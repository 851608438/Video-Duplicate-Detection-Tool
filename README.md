# 视频重复检测工具

一个基于Python的智能视频去重软件，支持GPU加速，能够检测经过压缩或格式转换的重复视频。

## 功能特性

- 🚀 **GPU加速**：支持NVIDIA CUDA加速，大幅提升检测速度
- 🎯 **智能检测**：先用元数据快速分组，再用CLIP深度学习精确验证
- 💾 **智能缓存**：自动缓存计算结果，避免重复处理
- 🎨 **现代化界面**：基于CustomTkinter的美观GUI
- 📊 **灵活控制**：可调节相似度阈值，适应不同需求
- 📁 **批量处理**：递归扫描子文件夹，支持数千个视频
- 🛡️ **内存优化**：批处理策略，避免内存和显存溢出

## 系统要求

- Windows 10/11
- Python 3.8+
- （可选）NVIDIA GPU + CUDA 11.0+

## 安装

1. 克隆或下载本项目
2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

运行主程序：
```bash
python main.py
```

1. 点击"选择文件夹"选择要扫描的视频目录
2. 调整相似度阈值（可选）
3. 点击"开始检测"
4. 查看检测结果，选择要删除的重复视频
5. 导出报告或执行删除操作

## 支持的视频格式

mp4, avi, mkv, mov, flv, wmv, webm, m4v, mpg, mpeg

## 技术栈

- **GUI**: CustomTkinter
- **视频处理**: OpenCV
- **深度学习**: PyTorch + CLIP
- **缓存**: SQLite

## 许可证

MIT License
