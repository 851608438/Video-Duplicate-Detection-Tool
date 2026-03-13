"""视频扫描器 - 递归扫描文件夹中的视频文件"""
import os
from typing import Generator, Callable, Optional
from utils.video_utils import is_video_file, get_video_info


class VideoScanner:
    """视频文件扫描器"""
    
    def __init__(self, root_folder: str):
        self.root_folder = root_folder
        self.total_files = 0
        self.scanned_files = 0
    
    def scan(self, progress_callback: Optional[Callable] = None) -> Generator[dict, None, None]:
        """
        递归扫描文件夹，返回视频信息
        
        Args:
            progress_callback: 进度回调函数 callback(current, total, filename)
        
        Yields:
            视频信息字典
        """
        # 首先统计总文件数
        self.total_files = self._count_video_files(self.root_folder)
        self.scanned_files = 0
        
        # 递归扫描
        for video_info in self._scan_recursive(self.root_folder, progress_callback):
            yield video_info
    
    def _count_video_files(self, folder: str) -> int:
        """统计视频文件总数"""
        count = 0
        try:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if is_video_file(file):
                        count += 1
        except Exception as e:
            print(f"统计文件失败: {e}")
        return count
    
    def _scan_recursive(self, folder: str, progress_callback: Optional[Callable]) -> Generator[dict, None, None]:
        """递归扫描文件夹"""
        try:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if is_video_file(file):
                        file_path = os.path.join(root, file)
                        
                        # 获取视频信息
                        video_info = get_video_info(file_path)
                        
                        if video_info:
                            self.scanned_files += 1
                            
                            # 调用进度回调
                            if progress_callback:
                                progress_callback(self.scanned_files, self.total_files, file)
                            
                            yield video_info
        except Exception as e:
            print(f"扫描文件夹失败 {folder}: {e}")
    
    def get_progress(self) -> tuple:
        """获取当前进度"""
        return self.scanned_files, self.total_files
