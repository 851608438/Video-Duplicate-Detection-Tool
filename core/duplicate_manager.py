"""重复视频管理器 - 协调两阶段检测流程"""
import os
import json
import csv
from typing import List, Dict, Callable, Optional
from collections import defaultdict
from core.video_scanner import VideoScanner
from core.fingerprint_detector import FingerprintDetector
from core.ratio_frame_detector import RatioFrameDetector
from core.clip_detector import CLIPDetector
from utils.cache_manager import CacheManager
from utils.video_utils import format_file_size


class DuplicateGroup:
    """重复视频组"""
    
    def __init__(self):
        self.videos = []  # 视频信息列表
        self.similarity_scores = {}  # 相似度分数
    
    def add_video(self, video_info: dict, similarity: float = 1.0):
        """添加视频到组"""
        self.videos.append(video_info)
        self.similarity_scores[video_info['path']] = similarity
    
    def get_recommended_keep(self) -> dict:
        """获取推荐保留的视频（最高分辨率或最大文件）"""
        if not self.videos:
            return None
        
        # 按分辨率排序，然后按文件大小
        sorted_videos = sorted(
            self.videos,
            key=lambda v: (v['width'] * v['height'], v['file_size']),
            reverse=True
        )
        
        return sorted_videos[0]
    
    def get_total_size(self) -> int:
        """获取组内所有视频的总大小"""
        return sum(v['file_size'] for v in self.videos)
    
    def get_removable_size(self) -> int:
        """获取可删除的文件大小（保留推荐的一个）"""
        if len(self.videos) <= 1:
            return 0
        
        keep = self.get_recommended_keep()
        return self.get_total_size() - keep['file_size']


class DuplicateManager:
    """重复视频检测管理器"""
    
    def __init__(self, config: dict):
        self.config = config
        self.cache_manager = CacheManager(config.get('cache_path', 'cache/video_cache.db'))
        
        # 初始化检测器
        self.fingerprint_detector = FingerprintDetector(self.cache_manager)
        self.ratio_frame_detector = RatioFrameDetector(self.cache_manager)
        
        self.clip_detector = None  # 延迟初始化
        
        self.duplicate_groups = []
        self.all_videos = []
    
    def detect_duplicates(self, folder_path: str, 
                         progress_callback: Optional[Callable] = None,
                         stage_callback: Optional[Callable] = None) -> List[DuplicateGroup]:
        """
        检测重复视频（两阶段）
        
        Args:
            folder_path: 要扫描的文件夹路径
            progress_callback: 进度回调 callback(current, total, message)
            stage_callback: 阶段回调 callback(stage_name)
        
        Returns:
            重复视频组列表
        """
        self.duplicate_groups = []
        self.all_videos = []
        
        # 阶段1: 扫描视频文件
        if stage_callback:
            stage_callback("扫描视频文件...")
        
        scanner = VideoScanner(folder_path)
        for video_info in scanner.scan(progress_callback):
            self.all_videos.append(video_info)
        
        if not self.all_videos:
            return []
        
        # 阶段2: 使用元数据指纹快速分组
        if stage_callback:
            stage_callback("使用元数据快速分组...")
        
        # 按指纹分组（时长、分辨率、帧数相近的分为一组）
        fingerprint_groups = self.fingerprint_detector.group_by_fingerprint(self.all_videos)
        
        if not fingerprint_groups:
            return []
        
        # 阶段3: 查找完全相同的文件（可选，快速识别副本）
        if stage_callback:
            stage_callback("查找完全相同的文件...")
        
        exact_duplicates = []
        candidate_groups = []
        
        detection_mode = self.config.get('detection_mode', 'fingerprint')
        
        for fingerprint, videos in fingerprint_groups.items():
            if progress_callback:
                progress_callback(len(candidate_groups) + 1, len(fingerprint_groups),
                                f"分析指纹组: {len(videos)} 个视频")
            
            # 先用文件哈希找完全相同的
            exact_groups = self.fingerprint_detector.find_exact_duplicates(videos)
            exact_duplicates.extend(exact_groups)
            
            # 剩余的需要进一步验证
            exact_paths = set()
            for group in exact_groups:
                for video in group:
                    exact_paths.add(video['path'])
            
            # 未被精确匹配的视频需要进一步验证
            remaining = [v for v in videos if v['path'] not in exact_paths]
            if len(remaining) >= 2:
                # 如果启用比例关键帧模式，先用它过滤
                if detection_mode == 'ratio_frame':
                    if stage_callback:
                        stage_callback("比例关键帧检测...")
                    
                    ratio_threshold = self.config.get('ratio_frame_threshold', 0.85)
                    ratio_groups = self.ratio_frame_detector.find_duplicates_in_group(
                        remaining, ratio_threshold
                    )
                    
                    # 比例关键帧检测到的重复组直接加入结果
                    exact_duplicates.extend(ratio_groups)
                else:
                    # 指纹模式：需要CLIP验证
                    candidate_groups.append(remaining)
        
        # 阶段4: 使用CLIP验证候选组
        if stage_callback:
            stage_callback("CLIP深度验证...")
        
        # 初始化CLIP检测器
        if self.clip_detector is None:
            self.clip_detector = CLIPDetector(
                self.cache_manager,
                fps_sample=self.config.get('clip_fps_sample', 2.0),
                batch_size=self.config.get('batch_size', 32),
                enable_gpu=self.config.get('enable_gpu', True)
            )
        
        verified_groups = self._verify_with_clip(
            candidate_groups,
            self.config.get('clip_threshold', 0.85),
            progress_callback
        )
        
        # 合并完全相同的文件组和CLIP验证的组
        all_groups = []
        
        # 完全相同的文件直接转为DuplicateGroup
        for exact_group in exact_duplicates:
            dup_group = DuplicateGroup()
            for video in exact_group:
                dup_group.add_video(video, 1.0)  # 完全相同，相似度1.0
            all_groups.append(dup_group)
        
        # 添加CLIP验证的组
        all_groups.extend(verified_groups)
        
        self.duplicate_groups = all_groups
        
        return self.duplicate_groups
    
    def _verify_with_clip(self, candidate_groups: List[List[dict]], 
                         threshold: float,
                         progress_callback: Optional[Callable]) -> List[DuplicateGroup]:
        """使用CLIP验证候选组"""
        verified_groups = []
        
        total_videos = sum(len(group) for group in candidate_groups)
        processed_videos = 0
        
        for group in candidate_groups:
            # 提取所有视频的CLIP特征
            features_map = {}
            
            for video_info in group:
                if progress_callback:
                    processed_videos += 1
                    progress_callback(processed_videos, total_videos,
                                    f"CLIP验证: {video_info['filename']}")
                
                features = self.clip_detector.extract_features(video_info['path'])
                if features is not None:
                    features_map[video_info['path']] = features
                    video_info['clip_features'] = features
            
            # 在组内进行两两比较，构建真正的重复子组
            sub_groups = self._cluster_by_similarity(
                group, features_map, threshold
            )
            
            verified_groups.extend(sub_groups)
        
        return verified_groups
    
    def _cluster_by_similarity(self, videos: List[dict], 
                               features_map: Dict[str, any],
                               threshold: float) -> List[DuplicateGroup]:
        """根据相似度聚类视频"""
        groups = []
        assigned = set()
        
        for i, video1 in enumerate(videos):
            path1 = video1['path']
            
            if path1 in assigned or path1 not in features_map:
                continue
            
            # 创建新组
            dup_group = DuplicateGroup()
            dup_group.add_video(video1, 1.0)
            assigned.add(path1)
            
            features1 = features_map[path1]
            
            # 找出所有相似的视频
            for j in range(i + 1, len(videos)):
                video2 = videos[j]
                path2 = video2['path']
                
                if path2 in assigned or path2 not in features_map:
                    continue
                
                features2 = features_map[path2]
                similarity = CLIPDetector.cosine_similarity(features1, features2)
                
                if similarity >= threshold:
                    dup_group.add_video(video2, similarity)
                    assigned.add(path2)
            
            # 只保留有重复的组
            if len(dup_group.videos) >= 2:
                groups.append(dup_group)
        
        return groups
    
    def export_report(self, output_path: str, format: str = 'csv'):
        """
        导出重复视频报告
        
        Args:
            output_path: 输出文件路径
            format: 格式 ('csv' 或 'json')
        """
        if format == 'csv':
            self._export_csv(output_path)
        elif format == 'json':
            self._export_json(output_path)
    
    def _export_csv(self, output_path: str):
        """导出CSV报告"""
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['组ID', '文件路径', '文件名', '大小', '分辨率', 
                           '时长(秒)', '相似度', '推荐保留'])
            
            for group_id, group in enumerate(self.duplicate_groups, 1):
                recommended = group.get_recommended_keep()
                
                for video in group.videos:
                    is_recommended = '是' if video['path'] == recommended['path'] else '否'
                    similarity = group.similarity_scores.get(video['path'], 1.0)
                    
                    writer.writerow([
                        group_id,
                        video['path'],
                        video['filename'],
                        format_file_size(video['file_size']),
                        f"{video['width']}x{video['height']}",
                        f"{video['duration']:.1f}",
                        f"{similarity:.3f}",
                        is_recommended
                    ])
    
    def _export_json(self, output_path: str):
        """导出JSON报告"""
        report = {
            'total_groups': len(self.duplicate_groups),
            'total_videos': len(self.all_videos),
            'duplicate_count': sum(len(g.videos) for g in self.duplicate_groups),
            'removable_size': sum(g.get_removable_size() for g in self.duplicate_groups),
            'groups': []
        }
        
        for group_id, group in enumerate(self.duplicate_groups, 1):
            recommended = group.get_recommended_keep()
            
            group_data = {
                'group_id': group_id,
                'video_count': len(group.videos),
                'total_size': group.get_total_size(),
                'removable_size': group.get_removable_size(),
                'videos': []
            }
            
            for video in group.videos:
                video_data = {
                    'path': video['path'],
                    'filename': video['filename'],
                    'size': video['file_size'],
                    'resolution': f"{video['width']}x{video['height']}",
                    'duration': video['duration'],
                    'similarity': group.similarity_scores.get(video['path'], 1.0),
                    'recommended_keep': video['path'] == recommended['path']
                }
                group_data['videos'].append(video_data)
            
            report['groups'].append(group_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def delete_videos(self, video_paths: List[str]) -> tuple:
        """
        删除指定的视频文件
        
        Returns:
            (成功数量, 失败数量)
        """
        success = 0
        failed = 0
        
        for path in video_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    success += 1
            except Exception as e:
                print(f"删除失败 {path}: {e}")
                failed += 1
        
        return success, failed
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        total_duplicates = sum(len(g.videos) for g in self.duplicate_groups)
        removable_size = sum(g.get_removable_size() for g in self.duplicate_groups)
        
        return {
            'total_videos': len(self.all_videos),
            'duplicate_groups': len(self.duplicate_groups),
            'total_duplicates': total_duplicates,
            'removable_size': removable_size,
            'removable_size_formatted': format_file_size(removable_size)
        }
    
    def cleanup(self):
        """清理资源"""
        if self.clip_detector:
            self.clip_detector.cleanup()
        self.cache_manager.close()
