"""主窗口界面"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import json
import os
from datetime import datetime
from core.duplicate_manager import DuplicateManager
from gui.result_panel import ResultPanel
from gui.settings_dialog import SettingsDialog
from utils.video_utils import format_file_size


class MainWindow(ctk.CTk):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.title("视频重复检测工具")
        self.geometry("1200x800")
        
        # 加载配置
        self.config = self._load_config()
        
        # 状态变量
        self.is_detecting = False
        self.detection_thread = None
        self.duplicate_manager = None
        
        # 创建界面
        self._create_widgets()
        
        # 设置关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        default_config = {
            "last_folder": "",
            "clip_threshold": 0.85,
            "clip_fps_sample": 2.0,
            "enable_gpu": True,
            "batch_size": 32,
            "cache_path": "cache/video_cache.db"
        }
        
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            print(f"加载配置失败: {e}")
        
        return default_config
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _create_widgets(self):
        """创建界面组件"""
        # 顶部控制面板
        top_frame = ctk.CTkFrame(self, height=150)
        top_frame.pack(fill="x", padx=10, pady=10)
        top_frame.pack_propagate(False)
        
        # 文件夹选择
        folder_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        folder_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(folder_frame, text="扫描文件夹:", 
                    font=ctk.CTkFont(size=14)).pack(side="left", padx=5)
        
        self.folder_entry = ctk.CTkEntry(folder_frame, width=600)
        self.folder_entry.pack(side="left", padx=5)
        self.folder_entry.insert(0, self.config.get('last_folder', ''))
        
        ctk.CTkButton(folder_frame, text="浏览", width=100,
                     command=self._select_folder).pack(side="left", padx=5)
        
        ctk.CTkButton(folder_frame, text="设置", width=100,
                     command=self._open_settings).pack(side="left", padx=5)
        
        # 控制按钮
        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=5)
        
        self.start_button = ctk.CTkButton(button_frame, text="开始检测", 
                                         width=150, height=40,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         command=self._start_detection)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ctk.CTkButton(button_frame, text="停止", 
                                        width=150, height=40,
                                        state="disabled",
                                        command=self._stop_detection)
        self.stop_button.pack(side="left", padx=5)
        
        # 进度信息
        progress_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(progress_frame, text="就绪",
                                        font=ctk.CTkFont(size=12))
        self.status_label.pack(anchor="w")
        
        # 中部结果面板
        result_frame = ctk.CTkFrame(self)
        result_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        result_label = ctk.CTkLabel(result_frame, text="检测结果",
                                   font=ctk.CTkFont(size=16, weight="bold"))
        result_label.pack(anchor="w", padx=10, pady=10)
        
        self.result_panel = ResultPanel(result_frame, height=400)
        self.result_panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # 底部操作面板
        bottom_frame = ctk.CTkFrame(self, height=100)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))
        bottom_frame.pack_propagate(False)
        
        # 统计信息
        self.stats_label = ctk.CTkLabel(bottom_frame, 
                                       text="扫描: 0  |  重复组: 0  |  可释放空间: 0 B",
                                       font=ctk.CTkFont(size=13))
        self.stats_label.pack(pady=10)
        
        # 操作按钮
        action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(action_frame, text="全选", width=120,
                     command=self.result_panel.select_all).pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="取消全选", width=120,
                     command=self.result_panel.deselect_all).pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="删除选中", width=120,
                     fg_color="red", hover_color="darkred",
                     command=self._delete_selected).pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="导出CSV报告", width=120,
                     command=lambda: self._export_report('csv')).pack(side="left", padx=5)
        
        ctk.CTkButton(action_frame, text="导出JSON报告", width=120,
                     command=lambda: self._export_report('json')).pack(side="left", padx=5)
        
        # 分页控制
        self.prev_button = ctk.CTkButton(action_frame, text="◀ 上一页", width=100,
                                        command=self._prev_page, state="disabled")
        self.prev_button.pack(side="left", padx=5)
        
        self.page_label = ctk.CTkLabel(action_frame, text="",
                                      font=ctk.CTkFont(size=12, weight="bold"))
        self.page_label.pack(side="left", padx=5)
        
        self.next_button = ctk.CTkButton(action_frame, text="下一页 ▶", width=100,
                                        command=self._next_page, state="disabled")
        self.next_button.pack(side="left", padx=5)
    
    def _select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择要扫描的文件夹")
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.config['last_folder'] = folder
            self._save_config()
    
    def _open_settings(self):
        """打开设置对话框"""
        SettingsDialog(self, self.config, self._on_settings_saved)
    
    def _prev_page(self):
        """上一页"""
        if hasattr(self.result_panel, 'current_page') and self.result_panel.current_page > 0:
            self.result_panel.load_page(self.result_panel.current_page - 1)
            self._update_pagination_ui()
    
    def _next_page(self):
        """下一页"""
        if hasattr(self.result_panel, 'current_page') and hasattr(self.result_panel, 'total_pages'):
            if self.result_panel.current_page < self.result_panel.total_pages - 1:
                self.result_panel.load_page(self.result_panel.current_page + 1)
                self._update_pagination_ui()
    
    def _update_pagination_ui(self):
        """更新分页UI状态"""
        if not hasattr(self.result_panel, 'total_pages') or self.result_panel.total_pages <= 1:
            self.prev_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            self.page_label.configure(text="")
            return
        
        current = self.result_panel.current_page + 1
        total = self.result_panel.total_pages
        self.page_label.configure(text=f"第 {current}/{total} 页")
        
        # 更新按钮状态
        if self.result_panel.current_page == 0:
            self.prev_button.configure(state="disabled")
        else:
            self.prev_button.configure(state="normal")
        
        if self.result_panel.current_page >= self.result_panel.total_pages - 1:
            self.next_button.configure(state="disabled")
        else:
            self.next_button.configure(state="normal")
    
    def _on_settings_saved(self, new_config: dict):
        """设置保存回调"""
        self.config.update(new_config)
        self._save_config()
        messagebox.showinfo("成功", "设置已保存")
    
    def _start_detection(self):
        """开始检测"""
        folder = self.folder_entry.get().strip()
        
        if not folder:
            messagebox.showwarning("警告", "请选择要扫描的文件夹")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror("错误", "文件夹不存在")
            return
        
        # 更新UI状态
        self.is_detecting = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        self.status_label.configure(text="正在初始化...")
        self.result_panel.clear()
        
        # 在后台线程中执行检测
        self.detection_thread = threading.Thread(target=self._detection_worker, args=(folder,))
        self.detection_thread.daemon = True
        self.detection_thread.start()
    
    def _detection_worker(self, folder: str):
        """检测工作线程"""
        try:
            # 创建管理器
            self.duplicate_manager = DuplicateManager(self.config)
            
            # 执行检测
            duplicate_groups = self.duplicate_manager.detect_duplicates(
                folder,
                progress_callback=self._on_progress,
                stage_callback=self._on_stage_change
            )
            
            # 检测完成
            if self.is_detecting:
                self.after(0, self._on_detection_complete, duplicate_groups)
        
        except Exception as e:
            if self.is_detecting:
                self.after(0, self._on_detection_error, str(e))
    
    def _on_progress(self, current: int, total: int, message: str):
        """进度更新回调"""
        if not self.is_detecting:
            return
        
        progress = current / total if total > 0 else 0
        status_text = f"[{current}/{total}] {message}"
        
        self.after(0, self._update_progress, progress, status_text)
    
    def _update_progress(self, progress: float, status: str):
        """更新进度条（在主线程中）"""
        self.progress_bar.set(progress)
        self.status_label.configure(text=status)
    
    def _on_stage_change(self, stage_name: str):
        """阶段变化回调"""
        if not self.is_detecting:
            return
        
        self.after(0, self.status_label.configure, {"text": stage_name})
    
    def _on_detection_complete(self, duplicate_groups):
        """检测完成"""
        self.is_detecting = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_bar.set(1.0)
        
        # 显示结果
        self.result_panel.display_results(duplicate_groups)
                # 更新分页UI
        self._update_pagination_ui()
                # 更新统计
        if self.duplicate_manager:
            stats = self.duplicate_manager.get_statistics()
            stats_text = (f"扫描: {stats['total_videos']}  |  "
                         f"重复组: {stats['duplicate_groups']}  |  "
                         f"可释放空间: {stats['removable_size_formatted']}")
            self.stats_label.configure(text=stats_text)
        
        self.status_label.configure(text=f"检测完成！发现 {len(duplicate_groups)} 组重复视频")
        
        if duplicate_groups:
            messagebox.showinfo("完成", f"检测完成！\n发现 {len(duplicate_groups)} 组重复视频")
        else:
            messagebox.showinfo("完成", "检测完成！未发现重复视频")
    
    def _on_detection_error(self, error_msg: str):
        """检测出错"""
        self.is_detecting = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text=f"错误: {error_msg}")
        messagebox.showerror("错误", f"检测过程中出错:\n{error_msg}")
    
    def _stop_detection(self):
        """停止检测"""
        if messagebox.askyesno("确认", "确定要停止检测吗？"):
            self.is_detecting = False
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.status_label.configure(text="已停止")
    
    def _delete_selected(self):
        """删除选中的视频"""
        selected = self.result_panel.get_selected_videos()
        
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的视频")
            return
        
        # 确认删除
        total_size = sum(os.path.getsize(p) for p in selected if os.path.exists(p))
        confirm_msg = (f"确定要删除 {len(selected)} 个视频吗？\n"
                      f"将释放 {format_file_size(total_size)} 空间\n\n"
                      f"此操作不可恢复！")
        
        if not messagebox.askyesno("确认删除", confirm_msg):
            return
        
        # 执行删除
        if self.duplicate_manager:
            success, failed = self.duplicate_manager.delete_videos(selected)
            
            messagebox.showinfo("完成", 
                              f"删除完成！\n成功: {success}\n失败: {failed}")
            
            # 重新加载结果以更新显示
            if success > 0:
                # 从重复组中移除已删除的视频
                updated_groups = []
                for group in self.duplicate_manager.duplicate_groups:
                    # 过滤掉已删除的视频
                    remaining_videos = [v for v in group.videos if v['path'] not in selected]
                    if len(remaining_videos) >= 2:
                        # 重新创建组
                        from core.duplicate_manager import DuplicateGroup
                        new_group = DuplicateGroup()
                        for video in remaining_videos:
                            similarity = group.similarity_scores.get(video['path'], 1.0)
                            new_group.add_video(video, similarity)
                        updated_groups.append(new_group)
                
                # 更新管理器中的重复组
                self.duplicate_manager.duplicate_groups = updated_groups
                
                # 重新显示结果
                self.result_panel.display_results(updated_groups)
                self._update_pagination_ui()
                
                # 更新统计信息
                total_videos = sum(len(g.videos) for g in updated_groups)
                total_removable = sum(g.get_removable_size() for g in updated_groups)
                self.stats_label.configure(
                    text=f"扫描: {total_videos}  |  重复组: {len(updated_groups)}  |  可释放空间: {format_file_size(total_removable)}"
                )
    
    def _export_report(self, format: str):
        """导出报告"""
        if not self.duplicate_manager or not self.duplicate_manager.duplicate_groups:
            messagebox.showwarning("警告", "没有可导出的结果")
            return
        
        # 选择保存位置
        ext = "csv" if format == "csv" else "json"
        default_name = f"重复视频报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        file_path = filedialog.asksaveasfilename(
            title="保存报告",
            defaultextension=f".{ext}",
            initialfile=default_name,
            filetypes=[(f"{ext.upper()} 文件", f"*.{ext}"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.duplicate_manager.export_report(file_path, format)
                messagebox.showinfo("成功", f"报告已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败:\n{e}")
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.is_detecting:
            if not messagebox.askyesno("确认", "检测正在进行中，确定要退出吗？"):
                return
            self.is_detecting = False
        
        # 清理资源
        if self.duplicate_manager:
            self.duplicate_manager.cleanup()
        
        self.destroy()


def run_app():
    """运行应用"""
    # 设置外观
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    
    # 创建并运行主窗口
    app = MainWindow()
    app.mainloop()
