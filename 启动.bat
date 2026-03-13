@echo off
chcp 65001 >nul
title 视频重复检测工具

echo ========================================
echo    视频重复检测工具 - 快速启动
echo ========================================
echo.

REM 检查虚拟环境是否存在
if exist "venv\Scripts\activate.bat" (
    echo [信息] 检测到虚拟环境，正在激活...
    call venv\Scripts\activate.bat
    echo [成功] 虚拟环境已激活
    echo.
) else (
    echo [警告] 未检测到虚拟环境
    echo [提示] 首次使用请先运行: python -m venv venv
    echo [提示] 然后安装依赖: pip install -r requirements.txt
    echo.
    echo [信息] 将使用系统 Python 环境
    echo.
)

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

echo [启动] 正在运行视频重复检测工具...
echo.
python main.py

echo.
echo ========================================
echo    程序已退出
echo ========================================
pause
