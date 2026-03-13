"""结果展示面板 - 显示重复视频组"""
import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
from typing import List, Callable
from core.duplicate_manager import DuplicateGroup
from utils.video_utils import format_file_size


class ResultPanel(ctk.CTkScrollableFrame):
    """重复视频结果展示面板（支持分页加载）"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.duplicate_groups = []
        self.checkboxes = {}  # path -> BooleanVar（当前页）
        self.group_frames = []
        self.selection_state = {}  # path -> bool（所有页的勾选状态缓存）
        
        # 分页参数
        self.page_size = 20  # 每页显示20组
        self.current_page = 0
        self.total_pages = 0
        
    def display_results(self, duplicate_groups: List[DuplicateGroup]):
        """显示检测结果（分页模式）"""
        # 清空现有内容
        self.clear()
        
        self.duplicate_groups = duplicate_groups
        
        if not duplicate_groups:
            label = ctk.CTkLabel(self, text="未发现重复视频", 
                               font=ctk.CTkFont(size=16))
            label.pack(pady=20)
            return
        
        # 计算总页数
        self.total_pages = (len(duplicate_groups) + self.page_size - 1) // self.page_size
        self.current_page = 0
        
        # 显示统计信息
        self._create_summary()
        
        # 显示第一页
        self.load_page(0)
    
    def _create_summary(self):
        """创建统计摘要"""
        summary_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("lightblue", "darkblue"))
        summary_frame.pack(fill="x", padx=10, pady=10)
        
        total_groups = len(self.duplicate_groups)
        total_videos = sum(len(g.videos) for g in self.duplicate_groups)
        total_removable = sum(g.get_removable_size() for g in self.duplicate_groups)
        
        summary_text = f"📊 检测结果：共 {total_groups} 组重复  |  涉及 {total_videos} 个视频  |  可释放空间: {format_file_size(total_removable)}"
        
        summary_label = ctk.CTkLabel(summary_frame, text=summary_text,
                                    font=ctk.CTkFont(size=14, weight="bold"))
        summary_label.pack(padx=20, pady=10)
    
    def load_page(self, page_num: int):
        """加载指定页的重复组（公开方法）"""
        if page_num < 0 or page_num >= self.total_pages:
            return
        
        # 保存当前页勾选状态
        self._save_selection_state()
        
        # 清空当前显示的组（使用after延迟销毁，避免卡顿）
        for frame in self.group_frames:
            frame.pack_forget()  # 先隐藏
            self.after(1, frame.destroy)  # 延迟销毁
        self.group_frames.clear()
        self.checkboxes.clear()
        
        # 计算当前页的范围
        start_idx = page_num * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.duplicate_groups))
        
        # 显示当前页的重复组
        for idx in range(start_idx, end_idx):
            group = self.duplicate_groups[idx]
            self._create_group_frame(idx + 1, group)
        
        # 更新页码
        self.current_page = page_num
        
        # 滚动到顶部
        self._parent_canvas.yview_moveto(0)
    
    def _save_selection_state(self):
        """保存当前页所有复选框的勾选状态"""
        for path, var in self.checkboxes.items():
            self.selection_state[path] = var.get()
    
    def _create_group_frame(self, group_id: int, group: DuplicateGroup):
        """创建重复组框架"""
        # 组容器
        group_frame = ctk.CTkFrame(self, corner_radius=10)
        group_frame.pack(fill="x", padx=10, pady=10)
        self.group_frames.append(group_frame)
        
        # 组标题
        recommended = group.get_recommended_keep()
        removable_size = format_file_size(group.get_removable_size())
        
        title_text = f"重复组 #{group_id}  |  共 {len(group.videos)} 个视频  |  可释放空间: {removable_size}"
        title_label = ctk.CTkLabel(group_frame, text=title_text,
                                   font=ctk.CTkFont(size=14, weight="bold"))
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # 视频列表
        for video in group.videos:
            self._create_video_item(group_frame, video, group, recommended)
    
    def _create_video_item(self, parent, video: dict, group: DuplicateGroup, recommended: dict):
        """创建单个视频项"""
        is_recommended = video['path'] == recommended['path']
        
        # 视频项容器
        item_frame = ctk.CTkFrame(parent, corner_radius=5,
                                 fg_color=("gray85", "gray25") if not is_recommended else ("green", "darkgreen"))
        item_frame.pack(fill="x", padx=10, pady=5)
        
        # 复选框：优先使用缓存的勾选状态，否则默认推荐保留不勾选
        default_value = self.selection_state.get(video['path'], not is_recommended)
        checkbox_var = ctk.BooleanVar(value=default_value)
        checkbox = ctk.CTkCheckBox(item_frame, text="", variable=checkbox_var,
                                   width=20)
        checkbox.pack(side="left", padx=10)
        self.checkboxes[video['path']] = checkbox_var
        
        # 视频信息
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # 文件名（可点击复制）
        filename_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        filename_frame.pack(anchor="w", fill="x")
        
        filename_label = ctk.CTkLabel(filename_frame, text=video['filename'],
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     anchor="w", cursor="hand2")
        filename_label.pack(side="left")
        filename_label.bind("<Button-1>", lambda e, name=video['filename']: self._copy_filename(name))
        
        copy_hint = ctk.CTkLabel(filename_frame, text="📋",
                                font=ctk.CTkFont(size=10),
                                text_color="gray", cursor="hand2")
        copy_hint.pack(side="left", padx=5)
        copy_hint.bind("<Button-1>", lambda e, name=video['filename']: self._copy_filename(name))
        
        # 路径
        path_label = ctk.CTkLabel(info_frame, text=video['path'],
                                 font=ctk.CTkFont(size=10),
                                 text_color="gray", anchor="w")
        path_label.pack(anchor="w")
        
        # 详细信息
        size_str = format_file_size(video['file_size'])
        resolution_str = f"{video['width']}x{video['height']}"
        duration_str = f"{video['duration']:.1f}秒"
        similarity = group.similarity_scores.get(video['path'], 1.0)
        
        details = f"大小: {size_str}  |  分辨率: {resolution_str}  |  时长: {duration_str}  |  相似度: {similarity:.2%}"
        
        if is_recommended:
            details += "  |  ⭐ 推荐保留"
        
        details_label = ctk.CTkLabel(info_frame, text=details,
                                    font=ctk.CTkFont(size=10),
                                    anchor="w")
        details_label.pack(anchor="w")
        
        # 操作按钮
        btn_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        open_btn = ctk.CTkButton(btn_frame, text="定位文件", width=80,
                                command=lambda p=video['path']: self._open_location(p))
        open_btn.pack(pady=2)
    
    def _copy_filename(self, filename: str):
        """复制文件名到剪贴板"""
        try:
            self.clipboard_clear()
            self.clipboard_append(filename)
            # 显示提示（可选）
            # messagebox.showinfo("提示", f"已复制: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {e}")
    
    def _open_location(self, file_path: str):
        """打开文件所在位置并选中文件"""
        try:
            # Windows系统使用explorer /select定位到具体文件
            if os.name == 'nt':  # Windows
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            else:  # Linux/Mac等其他系统，打开文件夹
                folder = os.path.dirname(file_path)
                if os.path.exists(folder):
                    os.startfile(folder)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件位置: {e}")
    
    def get_selected_videos(self) -> List[str]:
        """获取所有页中选中要删除的视频路径"""
        # 先保存当前页状态
        self._save_selection_state()
        # 返回所有页中勾选的视频
        return [path for path, checked in self.selection_state.items() if checked]
    
    def select_all(self):
        """全选所有页（排除推荐保留的）"""
        for group in self.duplicate_groups:
            recommended = group.get_recommended_keep()
            for video in group.videos:
                path = video['path']
                if path != recommended['path']:
                    self.selection_state[path] = True
                    if path in self.checkboxes:
                        self.checkboxes[path].set(True)
    
    def select_all_current_page(self):
        """全选当前页（排除推荐保留的）"""
        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, len(self.duplicate_groups))
        
        for idx in range(start_idx, end_idx):
            group = self.duplicate_groups[idx]
            recommended = group.get_recommended_keep()
            for video in group.videos:
                if video['path'] != recommended['path']:
                    if video['path'] in self.checkboxes:
                        self.checkboxes[video['path']].set(True)
    
    def deselect_all(self):
        """取消所有页的全选"""
        self.selection_state.clear()
        for var in self.checkboxes.values():
            var.set(False)
    
    def clear(self):
        """清空面板"""
        for frame in self.group_frames:
            frame.destroy()
        self.group_frames.clear()
        self.checkboxes.clear()
        self.selection_state.clear()
        self.duplicate_groups.clear()
        
        self.current_page = 0
        self.total_pages = 0
