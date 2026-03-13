"""设置对话框"""
import customtkinter as ctk
from tkinter import messagebox
from utils.gpu_utils import get_gpu_info, get_gpu_memory_info, check_cuda_available
from utils.video_utils import format_file_size


class SettingsDialog(ctk.CTkToplevel):
    """设置对话框"""
    
    def __init__(self, parent, config: dict, on_save: callable):
        super().__init__(parent)
        
        self.config = config.copy()
        self.on_save = on_save
        
        self.title("高级设置")
        self.geometry("500x600")
        self.resizable(False, False)
        
        # 居中显示
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_config()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # GPU设置
        gpu_label = ctk.CTkLabel(main_frame, text="GPU设置", 
                                font=ctk.CTkFont(size=16, weight="bold"))
        gpu_label.pack(anchor="w", pady=(0, 10))
        
        # GPU信息
        gpu_info = get_gpu_info()
        if gpu_info:
            info_text = f"GPU: {gpu_info['name']}"
            mem_info = get_gpu_memory_info()
            if mem_info:
                info_text += f"\n显存: {format_file_size(int(mem_info['total'] * 1024 * 1024))}"
        else:
            info_text = "未检测到CUDA GPU"
        
        gpu_info_label = ctk.CTkLabel(main_frame, text=info_text,
                                     font=ctk.CTkFont(size=12),
                                     text_color="gray")
        gpu_info_label.pack(anchor="w", pady=(0, 10))
        
        # GPU开关
        self.gpu_var = ctk.BooleanVar(value=True)
        gpu_switch = ctk.CTkSwitch(main_frame, text="启用GPU加速",
                                   variable=self.gpu_var)
        gpu_switch.pack(anchor="w", pady=5)
        
        if not check_cuda_available():
            gpu_switch.configure(state="disabled")
        
        # 分隔线
        ctk.CTkLabel(main_frame, text="").pack(pady=5)
        
        # 检测模式
        mode_label = ctk.CTkLabel(main_frame, text="检测模式",
                                 font=ctk.CTkFont(size=16, weight="bold"))
        mode_label.pack(anchor="w", pady=(10, 10))
        
        self.detection_mode_var = ctk.StringVar(value="fingerprint")
        
        mode_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        mode_frame.pack(fill="x", pady=5)
        
        fingerprint_radio = ctk.CTkRadioButton(
            mode_frame, 
            text="指纹模式（快速）",
            variable=self.detection_mode_var,
            value="fingerprint"
        )
        fingerprint_radio.pack(anchor="w", pady=2)
        
        ctk.CTkLabel(main_frame, text="使用元数据指纹+CLIP验证，速度快",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", padx=20)
        
        ratio_radio = ctk.CTkRadioButton(
            mode_frame,
            text="比例关键帧模式（精确）",
            variable=self.detection_mode_var,
            value="ratio_frame"
        )
        ratio_radio.pack(anchor="w", pady=2)
        
        ctk.CTkLabel(main_frame, text="按时长比例抽取关键帧比对，更精确但稍慢",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w", padx=20)
        
        # 比例关键帧阈值（仅在该模式下显示）
        self.ratio_threshold_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.ratio_threshold_frame.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(self.ratio_threshold_frame, text="关键帧相似度阈值:").pack(side="left")
        self.ratio_threshold_label = ctk.CTkLabel(self.ratio_threshold_frame, text="0.85")
        self.ratio_threshold_label.pack(side="right")
        
        self.ratio_threshold_var = ctk.DoubleVar(value=0.85)
        self.ratio_slider = ctk.CTkSlider(main_frame, from_=0.70, to=0.95,
                                         variable=self.ratio_threshold_var,
                                         command=self._update_ratio_label)
        self.ratio_slider.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main_frame, text="关键帧哈希相似度阈值（0.70-0.95）",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
        
        # 分隔线
        ctk.CTkLabel(main_frame, text="").pack(pady=5)
        
        # 检测参数
        param_label = ctk.CTkLabel(main_frame, text="检测参数",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        param_label.pack(anchor="w", pady=(10, 10))
        
        # CLIP阈值
        clip_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        clip_frame.pack(fill="x", pady=(5, 5))
        
        ctk.CTkLabel(clip_frame, text="相似度阈值:").pack(side="left")
        self.clip_threshold_label = ctk.CTkLabel(clip_frame, text="0.85")
        self.clip_threshold_label.pack(side="right")
        
        self.clip_threshold_var = ctk.DoubleVar(value=0.85)
        self.clip_slider = ctk.CTkSlider(main_frame, from_=0.70, to=0.95,
                                        variable=self.clip_threshold_var,
                                        command=self._update_clip_label)
        self.clip_slider.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(main_frame, text="值越大越严格，推荐0.85（0.70-0.95）",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
        
        # CLIP采样率
        clip_sample_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        clip_sample_frame.pack(fill="x", pady=(15, 5))
        
        ctk.CTkLabel(clip_sample_frame, text="CLIP采样率 (帧/秒):").pack(side="left")
        self.clip_fps_sample_var = ctk.DoubleVar(value=2.0)
        clip_fps_entry = ctk.CTkEntry(clip_sample_frame, textvariable=self.clip_fps_sample_var, width=80)
        clip_fps_entry.pack(side="right")
        
        ctk.CTkLabel(main_frame, text="每秒提取多少帧用于分析，值越大越精确但越慢",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
        
        # Batch Size
        batch_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        batch_frame.pack(fill="x", pady=(15, 5))
        
        ctk.CTkLabel(batch_frame, text="批处理大小:").pack(side="left")
        self.batch_size_var = ctk.IntVar(value=32)
        batch_entry = ctk.CTkEntry(batch_frame, textvariable=self.batch_size_var, width=80)
        batch_entry.pack(side="right")
        
        ctk.CTkLabel(main_frame, text="GPU批处理大小，显存不足时可降低",
                    font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
        
        # 预设按钮
        ctk.CTkLabel(main_frame, text="").pack(pady=10)
        preset_label = ctk.CTkLabel(main_frame, text="快速预设",
                                   font=ctk.CTkFont(size=16, weight="bold"))
        preset_label.pack(anchor="w", pady=(10, 10))
        
        preset_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        preset_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(preset_frame, text="快速模式", width=140,
                     command=self._preset_fast).pack(side="left", padx=5)
        ctk.CTkButton(preset_frame, text="平衡模式", width=140,
                     command=self._preset_balanced).pack(side="left", padx=5)
        ctk.CTkButton(preset_frame, text="精确模式", width=140,
                     command=self._preset_accurate).pack(side="left", padx=5)
        
        # 底部按钮
        ctk.CTkLabel(main_frame, text="").pack(pady=10)
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(button_frame, text="保存", width=200,
                     command=self._save_settings).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="取消", width=200,
                     command=self.destroy).pack(side="right", padx=5)
    
    def _update_clip_label(self, value):
        """更新CLIP阈值标签"""
        self.clip_threshold_label.configure(text=f"{float(value):.2f}")
    
    def _update_ratio_label(self, value):
        """更新比例关键帧阈值标签"""
        self.ratio_threshold_label.configure(text=f"{float(value):.2f}")
    
    def _preset_fast(self):
        """快速模式预设"""
        self.clip_threshold_var.set(0.80)
        self.clip_fps_sample_var.set(1.5)
        self._update_clip_label(0.80)
    
    def _preset_balanced(self):
        """平衡模式预设"""
        self.clip_threshold_var.set(0.85)
        self.clip_fps_sample_var.set(2.0)
        self._update_clip_label(0.85)
    
    def _preset_accurate(self):
        """精确模式预设"""
        self.clip_threshold_var.set(0.90)
        self.clip_fps_sample_var.set(3.0)
        self._update_clip_label(0.90)
    
    def _load_config(self):
        """加载配置"""
        self.gpu_var.set(self.config.get('enable_gpu', True))
        self.clip_threshold_var.set(self.config.get('clip_threshold', 0.85))
        self.clip_fps_sample_var.set(self.config.get('clip_fps_sample', 2.0))
        self.batch_size_var.set(self.config.get('batch_size', 32))
        self.detection_mode_var.set(self.config.get('detection_mode', 'fingerprint'))
        self.ratio_threshold_var.set(self.config.get('ratio_frame_threshold', 0.85))
        
        self._update_clip_label(self.clip_threshold_var.get())
        self._update_ratio_label(self.ratio_threshold_var.get())
    
    def _save_settings(self):
        """保存设置"""
        try:
            self.config['enable_gpu'] = self.gpu_var.get()
            self.config['clip_threshold'] = float(self.clip_threshold_var.get())
            self.config['clip_fps_sample'] = float(self.clip_fps_sample_var.get())
            self.config['batch_size'] = int(self.batch_size_var.get())
            self.config['detection_mode'] = self.detection_mode_var.get()
            self.config['ratio_frame_threshold'] = float(self.ratio_threshold_var.get())
            
            self.on_save(self.config)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("错误", f"参数格式错误: {e}")
