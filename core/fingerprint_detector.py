"""快速指纹检测器 - 基于视频元数据的快速筛选"""
import os
import hashlib
from typing import Optional, Dict, List
from utils.cache_manager import CacheManager


class FingerprintDetector:
    """视频指纹检测器 - 使用元数据快速分组"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def compute_fingerprint(self, video_info: dict) -> str:
        """
        计算视频指纹（基于元数据）
        
        使用时长和分辨率创建指纹，相同指纹的视频才需要深度比较
        这比传统哈希快100倍以上
        
        Args:
            video_info: 视频信息字典
        
        Returns:
            指纹字符串
        """
        # 时长分组（容忍2%误差）
        duration = video_info.get('duration', 0)
        if duration > 0:
            duration_bucket = int(duration / max(1, duration * 0.02))
        else:
            duration_bucket = 0
        
        # 分辨率分组
        width = video_info.get('width', 0)
        height = video_info.get('height', 0)
        
        # 帧数分组（容忍3%误差）
        frame_count = video_info.get('frame_count', 0)
        if frame_count > 0:
            frame_bucket = int(frame_count / max(1, frame_count * 0.03))
        else:
            frame_bucket = 0
        
        # 组合指纹
        fingerprint = f"{duration_bucket}_{width}x{height}_{frame_bucket}"
        
        return fingerprint
    
    def group_by_fingerprint(self, video_list: List[dict]) -> Dict[str, List[dict]]:
        """
        按指纹分组视频
        
        只有相同指纹的视频才可能是重复的
        
        Args:
            video_list: 视频信息列表
        
        Returns:
            指纹 -> 视频列表的字典
        """
        groups = {}
        
        for video_info in video_list:
            fingerprint = self.compute_fingerprint(video_info)
            
            if fingerprint not in groups:
                groups[fingerprint] = []
            
            groups[fingerprint].append(video_info)
        
        # 只返回有多个视频的组（可能重复）
        return {fp: videos for fp, videos in groups.items() if len(videos) >= 2}
    
    def compute_file_hash(self, video_path: str, sample_size: int = 1024 * 1024) -> Optional[str]:
        """
        计算文件部分哈希（用于精确去重）
        
        只读取文件开头和结尾各1MB，速度极快
        
        Args:
            video_path: 视频路径
            sample_size: 采样大小（字节）
        
        Returns:
            MD5哈希值
        """
        try:
            file_size = os.path.getsize(video_path)
            
            hasher = hashlib.md5()
            
            with open(video_path, 'rb') as f:
                # 读取开头
                hasher.update(f.read(min(sample_size, file_size)))
                
                # 如果文件足够大，读取结尾
                if file_size > sample_size * 2:
                    f.seek(-sample_size, 2)  # 从文件末尾往前
                    hasher.update(f.read(sample_size))
            
            return hasher.hexdigest()
        
        except Exception as e:
            print(f"计算文件哈希失败 {video_path}: {e}")
            return None
    
    def find_exact_duplicates(self, video_list: List[dict]) -> List[List[dict]]:
        """
        查找完全相同的文件（通过文件哈希）
        
        这可以快速识别完全相同的副本
        
        Args:
            video_list: 视频信息列表
        
        Returns:
            重复组列表
        """
        hash_groups = {}
        
        for video_info in video_list:
            file_hash = self.compute_file_hash(video_info['path'])
            
            if file_hash:
                video_info['file_hash'] = file_hash
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(video_info)
        
        # 返回有重复的组
        return [videos for videos in hash_groups.values() if len(videos) >= 2]
    
    @staticmethod
    def is_similar_metadata(video1: dict, video2: dict, 
                           duration_tolerance: float = 0.02,
                           resolution_tolerance: float = 0.5) -> bool:
        """
        判断两个视频的元数据是否相似
        
        Args:
            video1, video2: 视频信息
            duration_tolerance: 时长容差（百分比）
            resolution_tolerance: 分辨率容差（面积比）
        
        Returns:
            是否相似
        """
        # 时长检查
        dur1 = video1.get('duration', 0)
        dur2 = video2.get('duration', 0)
        
        if dur1 == 0 or dur2 == 0:
            return False
        
        duration_diff = abs(dur1 - dur2) / max(dur1, dur2)
        if duration_diff > duration_tolerance:
            return False
        
        # 分辨率检查（允许不同分辨率，如720p vs 1080p）
        area1 = video1.get('width', 0) * video1.get('height', 0)
        area2 = video2.get('width', 0) * video2.get('height', 0)
        
        if area1 == 0 or area2 == 0:
            return False
        
        # 面积比在容差范围内
        area_ratio = min(area1, area2) / max(area1, area2)
        if area_ratio < resolution_tolerance:
            return False
        
        return True
