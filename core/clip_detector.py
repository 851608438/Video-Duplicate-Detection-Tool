"""CLIP深度特征检测器 - 使用CLIP模型提取视频特征"""
import torch
import clip
import cv2
import numpy as np
import os
from typing import Optional, List
from PIL import Image
from utils.video_utils import extract_frames
from utils.cache_manager import CacheManager
from utils.gpu_utils import check_cuda_available, clear_gpu_cache


class CLIPDetector:
    """CLIP视频特征检测器"""
    
    def __init__(self, cache_manager: CacheManager, fps_sample: float = 2.0, 
                 batch_size: int = 32, enable_gpu: bool = True):
        self.cache_manager = cache_manager
        self.fps_sample = fps_sample
        self.batch_size = batch_size
        
        # 设置设备
        self.device = "cuda" if enable_gpu and check_cuda_available() else "cpu"
        
        # 加载CLIP模型
        print(f"加载CLIP模型到 {self.device}...")
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
        self.model.eval()
        
        print(f"CLIP模型加载完成，使用设备: {self.device}")
    
    def extract_features(self, video_path: str) -> Optional[np.ndarray]:
        """
        提取视频的CLIP特征向量
        
        Args:
            video_path: 视频路径
        
        Returns:
            特征向量（512维），失败返回None
        """
        # 检查缓存
        file_size = os.path.getsize(video_path)
        modified_time = os.path.getmtime(video_path)
        
        cached_features = self.cache_manager.get_clip_features(video_path, file_size, modified_time)
        if cached_features is not None:
            return cached_features
        
        # 提取帧
        frames = extract_frames(video_path, self.fps_sample, max_frames=100)
        
        if not frames:
            return None
        
        # 生成特征
        features = self._compute_features(frames)
        
        # 保存到缓存
        if features is not None:
            self.cache_manager.set_clip_features(video_path, file_size, modified_time, features)
        
        return features
    
    def _compute_features(self, frames: List[np.ndarray]) -> Optional[np.ndarray]:
        """
        从帧列表计算CLIP特征
        
        使用批处理和平均池化策略
        """
        if not frames:
            return None
        
        all_features = []
        
        try:
            with torch.no_grad():
                # 批处理
                for i in range(0, len(frames), self.batch_size):
                    batch_frames = frames[i:i + self.batch_size]
                    
                    # 预处理帧
                    batch_images = []
                    for frame in batch_frames:
                        # OpenCV BGR转RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        preprocessed = self.preprocess(pil_image)
                        batch_images.append(preprocessed)
                    
                    # 堆叠为batch
                    batch_tensor = torch.stack(batch_images).to(self.device)
                    
                    # 提取特征
                    features = self.model.encode_image(batch_tensor)
                    
                    # 归一化
                    features = features / features.norm(dim=-1, keepdim=True)
                    
                    # 转换为numpy
                    features_np = features.cpu().numpy()
                    all_features.append(features_np)
            
            # 合并所有批次的特征
            all_features = np.vstack(all_features)
            
            # 平均池化：取所有帧特征的平均值作为视频特征
            video_feature = np.mean(all_features, axis=0)
            
            # 再次归一化
            video_feature = video_feature / np.linalg.norm(video_feature)
            
            # 清理GPU缓存
            if self.device == "cuda":
                clear_gpu_cache()
            
            return video_feature
        
        except Exception as e:
            print(f"计算CLIP特征失败: {e}")
            if self.device == "cuda":
                clear_gpu_cache()
            return None
    
    @staticmethod
    def cosine_similarity(features1: np.ndarray, features2: np.ndarray) -> float:
        """计算两个特征向量的余弦相似度"""
        return np.dot(features1, features2)
    
    @staticmethod
    def is_similar(features1: np.ndarray, features2: np.ndarray, threshold: float = 0.85) -> bool:
        """判断两个特征向量是否相似"""
        similarity = CLIPDetector.cosine_similarity(features1, features2)
        return similarity >= threshold
    
    def cleanup(self):
        """清理资源"""
        if self.device == "cuda":
            clear_gpu_cache()
