#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智炬五维协同学习系统 - 前端启动脚本
可在PyCharm中直接运行此文件启动前端服务
"""

import subprocess
import sys
import os


def main():
    print("=" * 50)
    print("智炬五维协同学习系统 - 前端启动")
    print("=" * 50)
    print()

    # 切换到前端目录
    frontend_dir = os.path.join(os.path.dirname(__file__), "FrontDev")
    os.chdir(frontend_dir)

    print(f"工作目录: {os.getcwd()}")
    print()

    # 检查依赖
    if not os.path.exists("node_modules"):
        print("首次运行，正在安装依赖...")
        subprocess.run(["npm", "install"], shell=True)
        print()

    print("启动前端开发服务器...")
    print("默认端口: 5173")
    print("注意: 如果端口被占用，Vite会自动选择下一个可用端口")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    print()

    try:
        subprocess.run(["npm", "run", "dev"], shell=True)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
