"""比例关键帧检测器 - 按时长比例抽取关键帧进行比对"""
import cv2
import numpy as np
import os
from typing import Optional, List, Tuple
from PIL import Image
from utils.cache_manager import CacheManager


class RatioFrameDetector:
    """比例关键帧检测器 - 按视频时长比例抽取固定位置的帧"""
    
    def __init__(self, cache_manager: CacheManager, 
                 ratios: List[float] = None):
        self.cache_manager = cache_manager
        # 默认抽取10%, 20%, ..., 90%位置的帧
        self.ratios = ratios or [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    def extract_ratio_frames(self, video_path: str) -> Optional[List[np.ndarray]]:
        """
        按比例抽取关键帧
        
        Args:
            video_path: 视频路径
        
        Returns:
            关键帧列表
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                cap.release()
                return None
            
            frames = []
            for ratio in self.ratios:
                frame_idx = int(total_frames * ratio)
                # 确保不超出范围
                frame_idx = min(frame_idx, total_frames - 1)
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret and frame is not None:
                    frames.append(frame)
            
            cap.release()
            return frames if frames else None
        
        except Exception as e:
            print(f"抽取比例关键帧失败 {video_path}: {e}")
            return None
    
    def compute_frame_hashes(self, frames: List[np.ndarray]) -> Optional[List[str]]:
        """
        计算帧的感知哈希
        
        使用差值哈希(dHash)，速度快且准确
        
        Args:
            frames: 帧列表
        
        Returns:
            哈希值列表
        """
        if not frames:
            return None
        
        hashes = []
        for frame in frames:
            try:
                # 转换为灰度
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 缩放到9x8（dHash需要）
                resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
                
                # 计算差值哈希
                diff = resized[:, 1:] > resized[:, :-1]
                
                # 转换为二进制字符串
                hash_str = ''.join(['1' if bit else '0' for bit in diff.flatten()])
                hashes.append(hash_str)
            
            except Exception as e:
                print(f"计算帧哈希失败: {e}")
                continue
        
        return hashes if hashes else None
    
    def compute_video_signature(self, video_path: str) -> Optional[List[str]]:
        """
        计算视频签名（所有比例关键帧的哈希）
        
        Args:
            video_path: 视频路径
        
        Returns:
            哈希列表（视频签名）
        """
        # 检查缓存
        file_size = os.path.getsize(video_path)
        modified_time = os.path.getmtime(video_path)
        
        cached_signature = self.cache_manager.get_hash(video_path, file_size, modified_time)
        if cached_signature:
            # 缓存的是用|分隔的哈希字符串
            return cached_signature.split('|')
        
        # 抽取帧
        frames = self.extract_ratio_frames(video_path)
        if not frames:
            return None
        
        # 计算哈希
        hashes = self.compute_frame_hashes(frames)
        
        # 保存到缓存
        if hashes:
            signature_str = '|'.join(hashes)
            self.cache_manager.set_hash(video_path, file_size, modified_time, signature_str)
        
        return hashes
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """计算两个哈希的汉明距离"""
        if len(hash1) != len(hash2):
            return -1
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    @staticmethod
    def compare_signatures(signature1: List[str], signature2: List[str], 
                          threshold: float = 0.85) -> Tuple[bool, float]:
        """
        比较两个视频签名
        
        Args:
            signature1, signature2: 视频签名（哈希列表）
            threshold: 相似度阈值
        
        Returns:
            (是否相似, 相似度分数)
        """
        if not signature1 or not signature2:
            return False, 0.0
        
        # 确保长度相同
        min_len = min(len(signature1), len(signature2))
        signature1 = signature1[:min_len]
        signature2 = signature2[:min_len]
        
        similarities = []
        for hash1, hash2 in zip(signature1, signature2):
            distance = RatioFrameDetector.hamming_distance(hash1, hash2)
            if distance >= 0:
                # 转换为相似度（0-1）
                max_distance = len(hash1)
                similarity = 1 - (distance / max_distance)
                similarities.append(similarity)
        
        if not similarities:
            return False, 0.0
        
        # 平均相似度
        avg_similarity = np.mean(similarities)
        
        return avg_similarity >= threshold, avg_similarity
    
    def find_duplicates_in_group(self, video_list: List[dict], 
                                 threshold: float = 0.85) -> List[List[dict]]:
        """
        在视频组中查找重复
        
        Args:
            video_list: 视频信息列表
            threshold: 相似度阈值
        
        Returns:
            重复组列表
        """
        # 计算所有视频的签名
        signatures = {}
        for video in video_list:
            sig = self.compute_video_signature(video['path'])
            if sig:
                signatures[video['path']] = sig
                video['ratio_signature'] = sig
        
        # 两两比较
        duplicate_groups = []
        processed = set()
        
        video_paths = list(signatures.keys())
        
        for i, path1 in enumerate(video_paths):
            if path1 in processed:
                continue
            
            group = [v for v in video_list if v['path'] == path1]
            processed.add(path1)
            
            for j in range(i + 1, len(video_paths)):
                path2 = video_paths[j]
                
                if path2 in processed:
                    continue
                
                is_similar, similarity = self.compare_signatures(
                    signatures[path1], 
                    signatures[path2], 
                    threshold
                )
                
                if is_similar:
                    video2 = [v for v in video_list if v['path'] == path2][0]
                    video2['ratio_similarity'] = similarity
                    group.append(video2)
                    processed.add(path2)
            
            # 只保留有重复的组
            if len(group) >= 2:
                duplicate_groups.append(group)
        
        return duplicate_groups
