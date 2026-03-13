"""缓存管理器 - 使用SQLite存储哈希值和特征向量"""
import sqlite3
import os
import pickle
from typing import Optional, Any
from datetime import datetime
import threading


class CacheManager:
    """视频处理结果缓存管理器"""
    
    def __init__(self, db_path: str = "cache/video_cache.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_db_exists()
    
    def _get_connection(self):
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._local.conn
    
    def _ensure_db_exists(self):
        """确保数据库和表存在"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建视频缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_cache (
                file_path TEXT PRIMARY KEY,
                file_size INTEGER,
                modified_time REAL,
                hash_value TEXT,
                clip_features BLOB,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    
    def get_hash(self, file_path: str, file_size: int, modified_time: float) -> Optional[str]:
        """获取缓存的哈希值"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT hash_value FROM video_cache 
            WHERE file_path = ? AND file_size = ? AND modified_time = ?
        ''', (file_path, file_size, modified_time))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def set_hash(self, file_path: str, file_size: int, modified_time: float, hash_value: str):
        """保存哈希值到缓存"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO video_cache (file_path, file_size, modified_time, hash_value)
            VALUES (?, ?, ?, ?)
        ''', (file_path, file_size, modified_time, hash_value))
        
        conn.commit()
    
    def get_clip_features(self, file_path: str, file_size: int, modified_time: float) -> Optional[Any]:
        """获取缓存的CLIP特征向量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT clip_features FROM video_cache 
            WHERE file_path = ? AND file_size = ? AND modified_time = ?
        ''', (file_path, file_size, modified_time))
        
        result = cursor.fetchone()
        if result and result[0]:
            return pickle.loads(result[0])
        return None
    
    def set_clip_features(self, file_path: str, file_size: int, modified_time: float, features: Any):
        """保存CLIP特征向量到缓存"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        features_blob = pickle.dumps(features)
        
        cursor.execute('''
            INSERT OR REPLACE INTO video_cache 
            (file_path, file_size, modified_time, clip_features)
            VALUES (?, ?, ?, ?)
        ''', (file_path, file_size, modified_time, features_blob))
        
        conn.commit()
    
    def clear_cache(self):
        """清空所有缓存"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM video_cache')
        conn.commit()
    
    def remove_missing_files(self, existing_paths: set):
        """删除不存在文件的缓存"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_path FROM video_cache')
        all_cached = [row[0] for row in cursor.fetchall()]
        
        to_remove = [path for path in all_cached if path not in existing_paths]
        
        if to_remove:
            cursor.executemany('DELETE FROM video_cache WHERE file_path = ?', 
                             [(path,) for path in to_remove])
            conn.commit()
        
        return len(to_remove)
    
    def get_cache_size(self) -> int:
        """获取缓存数据库大小（字节）"""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path)
        return 0
    
    def get_cache_count(self) -> int:
        """获取缓存条目数量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM video_cache')
        return cursor.fetchone()[0]
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')
