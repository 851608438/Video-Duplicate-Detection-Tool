"""
PyInstaller打包脚本

使用方法:
    python build.py

生成的可执行文件位于 dist/ 目录
"""
import PyInstaller.__main__
import os
import sys


def build():
    """构建可执行文件"""
    
    # PyInstaller参数
    args = [
        'main.py',                          # 主程序
        '--name=视频重复检测工具',            # 程序名称
        '--windowed',                        # 无控制台窗口
        '--onedir',                          # 文件夹模式（推荐，启动快）
        '--icon=NONE',                       # 图标（如果有的话）
        '--add-data=config.json;.',          # 包含配置文件
        '--hidden-import=clip',              # 隐式导入
        '--hidden-import=torch',
        '--hidden-import=torchvision',
        '--hidden-import=cv2',
        '--hidden-import=customtkinter',
        '--hidden-import=PIL',
        '--hidden-import=numpy',
        '--collect-all=clip',                # 收集CLIP所有文件
        '--collect-all=customtkinter',       # 收集CustomTkinter主题文件
        '--noconfirm',                       # 覆盖输出目录
    ]
    
    print("开始打包...")
    print("=" * 60)
    
    PyInstaller.__main__.run(args)
    
    print("=" * 60)
    print("打包完成！")
    print(f"可执行文件位于: dist/视频重复检测工具/")
    print("\n注意事项:")
    print("1. 首次运行会下载CLIP模型（约400MB），需要网络连接")
    print("2. 如果用户没有NVIDIA GPU，程序会自动使用CPU模式")
    print("3. 建议将整个文件夹分发给用户，不要只分发exe文件")


if __name__ == "__main__":
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
    except ImportError:
        print("错误: 未安装PyInstaller")
        print("请运行: pip install pyinstaller")
        sys.exit(1)
    
    build()
