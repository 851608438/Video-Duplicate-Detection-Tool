"""视频处理工具模块"""
import cv2
import os
from typing import Tuple, List, Optional
import numpy as np


SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}


def is_video_file(filepath: str) -> bool:
    """判断是否为支持的视频文件"""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in SUPPORTED_FORMATS


def get_video_info(video_path: str) -> Optional[dict]:
    """获取视频元信息"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        info = {
            'path': video_path,
            'filename': os.path.basename(video_path),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'duration': 0,
            'file_size': os.path.getsize(video_path)
        }
        
        if info['fps'] > 0:
            info['duration'] = info['frame_count'] / info['fps']
        
        cap.release()
        return info
    except Exception as e:
        print(f"获取视频信息失败 {video_path}: {e}")
        return None


def extract_frames(video_path: str, fps_sample: float = 1.0, max_frames: int = None) -> List[np.ndarray]:
    """
    提取视频关键帧
    
    Args:
        video_path: 视频路径
        fps_sample: 每秒采样帧数
        max_frames: 最大帧数限制
    
    Returns:
        帧列表（numpy数组）
    """
    frames = []
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return frames
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = 25  # 默认值
        
        # 计算采样间隔
        frame_interval = int(video_fps / fps_sample)
        if frame_interval < 1:
            frame_interval = 1
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                frames.append(frame)
                
                if max_frames and len(frames) >= max_frames:
                    break
            
            frame_idx += 1
        
        cap.release()
    except Exception as e:
        print(f"提取帧失败 {video_path}: {e}")
    
    return frames


def resize_frame(frame: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """调整帧大小"""
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


def format_duration(seconds: float) -> str:
    """格式化时长显示"""
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}小时{minutes}分"


def format_file_size(bytes_size: int) -> str:
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def create_thumbnail(video_path: str, output_size: Tuple[int, int] = (160, 90)) -> Optional[np.ndarray]:
    """创建视频缩略图（提取第一帧）"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return resize_frame(frame, output_size)
        return None
    except Exception as e:
        print(f"创建缩略图失败 {video_path}: {e}")
        return None
