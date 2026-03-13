"""感知哈希检测器 - 基于小波哈希算法"""
import cv2
import numpy as np
import os
from typing import Optional, List
from utils.video_utils import extract_frames, resize_frame
from utils.cache_manager import CacheManager


class HashDetector:
    """视频感知哈希检测器"""
    
    def __init__(self, cache_manager: CacheManager, fps_sample: float = 1.0):
        self.cache_manager = cache_manager
        self.fps_sample = fps_sample
    
    def compute_hash(self, video_path: str) -> Optional[str]:
        """
        计算视频的感知哈希值
        
        Args:
            video_path: 视频路径
        
        Returns:
            64位哈希字符串，失败返回None
        """
        # 检查缓存
        file_size = os.path.getsize(video_path)
        modified_time = os.path.getmtime(video_path)
        
        cached_hash = self.cache_manager.get_hash(video_path, file_size, modified_time)
        if cached_hash:
            return cached_hash
        
        # 提取帧
        frames = extract_frames(video_path, self.fps_sample, max_frames=60)
        
        if not frames:
            return None
        
        # 生成哈希
        hash_value = self._generate_hash(frames)
        
        # 保存到缓存
        if hash_value:
            self.cache_manager.set_hash(video_path, file_size, modified_time, hash_value)
        
        return hash_value
    
    def _generate_hash(self, frames: List[np.ndarray]) -> str:
        """
        从帧列表生成哈希值
        
        使用小波哈希算法：
        1. 将所有帧缩放到统一大小
        2. 拼接成网格图像
        3. 转换为灰度
        4. 应用离散小波变换
        5. 生成二进制哈希
        """
        if not frames:
            return ""
        
        # 限制帧数，避免内存问题
        if len(frames) > 60:
            step = len(frames) // 60
            frames = frames[::step][:60]
        
        # 缩放所有帧到144x144
        resized_frames = []
        for frame in frames:
            resized = resize_frame(frame, (144, 144))
            resized_frames.append(resized)
        
        # 计算网格大小
        grid_size = int(np.ceil(np.sqrt(len(resized_frames))))
        
        # 创建拼贴图
        collage = np.zeros((grid_size * 144, grid_size * 144, 3), dtype=np.uint8)
        
        for idx, frame in enumerate(resized_frames):
            row = idx // grid_size
            col = idx % grid_size
            collage[row*144:(row+1)*144, col*144:(col+1)*144] = frame
        
        # 转换为灰度
        gray = cv2.cvtColor(collage, cv2.COLOR_BGR2GRAY)
        
        # 缩放到32x32用于哈希计算
        small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        
        # 计算DCT（离散余弦变换）
        dct = cv2.dct(np.float32(small))
        
        # 取左上角8x8区域
        dct_low = dct[:8, :8]
        
        # 计算中值
        median = np.median(dct_low)
        
        # 生成二进制哈希
        hash_bits = (dct_low > median).flatten()
        
        # 转换为十六进制字符串
        hash_value = ''.join(['1' if bit else '0' for bit in hash_bits])
        
        return hash_value
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """计算两个哈希值的汉明距离"""
        if len(hash1) != len(hash2):
            return -1
        
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    @staticmethod
    def is_similar(hash1: str, hash2: str, threshold: int = 10) -> bool:
        """判断两个哈希值是否相似"""
        distance = HashDetector.hamming_distance(hash1, hash2)
        return 0 < distance <= threshold
