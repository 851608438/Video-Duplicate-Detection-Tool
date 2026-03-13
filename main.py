"""
视频重复检测工具 - 主程序入口

支持GPU加速的智能视频去重软件
"""
import sys
import os
import logging
from datetime import datetime

# 配置日志
log_filename = f"video_dedup_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖库是否正确安装"""
    missing_deps = []
    
    try:
        import customtkinter
        logger.info(f"✓ CustomTkinter {customtkinter.__version__}")
    except ImportError:
        missing_deps.append("customtkinter")
    
    try:
        import cv2
        logger.info(f"✓ OpenCV {cv2.__version__}")
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import torch
        logger.info(f"✓ PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            logger.info(f"  GPU: {torch.cuda.get_device_name(0)}")
        else:
            logger.warning("  CUDA不可用，将使用CPU模式（速度较慢）")
    except ImportError:
        missing_deps.append("torch")
    
    try:
        import clip
        logger.info("✓ CLIP")
    except ImportError:
        missing_deps.append("clip")
    
    try:
        import PIL
        logger.info(f"✓ Pillow {PIL.__version__}")
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import numpy
        logger.info(f"✓ NumPy {numpy.__version__}")
    except ImportError:
        missing_deps.append("numpy")
    
    if missing_deps:
        logger.error(f"缺少依赖库: {', '.join(missing_deps)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("视频重复检测工具启动")
    logger.info("=" * 60)
    
    # 检查依赖
    logger.info("检查依赖库...")
    if not check_dependencies():
        input("\n按回车键退出...")
        sys.exit(1)
    
    logger.info("\n所有依赖检查通过！")
    logger.info("正在启动GUI界面...\n")
    
    try:
        # 导入并运行GUI
        from gui.main_window import run_app
        run_app()
        
    except Exception as e:
        logger.exception("程序运行出错")
        import tkinter.messagebox as messagebox
        messagebox.showerror("错误", f"程序运行出错:\n{str(e)}\n\n详细信息请查看日志文件: {log_filename}")
        sys.exit(1)
    
    logger.info("程序正常退出")


if __name__ == "__main__":
    main()
