#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智炬五维协同学习系统 - 后端启动脚本
可在PyCharm中直接运行此文件启动后端服务
"""

import subprocess
import sys
import socket
import time
import psutil
import os


def check_port(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_process_on_port(port: int):
    """终止占用指定端口的进程"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            try:
                os.kill(conn.pid, 9)  # Windows下使用SIGKILL
                print(f"已终止占用端口 {port} 的进程 (PID: {conn.pid})")
            except:
                pass


def main():
    print("=" * 50)
    print("智炬五维协同学习系统 - 后端启动")
    print("=" * 50)
    print()

    # 检查并释放端口
    port = 8000
    if check_port(port):
        print(f"警告: 端口 {port} 已被占用，正在尝试释放...")
        kill_process_on_port(port)
        time.sleep(1)

    print(f"启动后端服务...")
    print(f"端口: {port}")
    print()

    try:
        # 使用 Popen 以便实时捕获输出
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "dev.api.server:app",
             "--host", "0.0.0.0", "--port", str(port), "--log-level", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )

        # 监听输出，等待服务启动完成
        startup_complete = False
        try:
            for line in process.stdout:
                print(line, end='')  # 实时输出日志
                if not startup_complete and "Application startup complete" in line:
                    startup_complete = True
                    print()
                    print("=" * 50)
                    print("后端服务启动成功！")
                    print(f"API文档: http://localhost:{port}/docs")
                    print(f"健康检查: http://localhost:{port}/api/health")
                    print("=" * 50)
                    print()
        except KeyboardInterrupt:
            print("\n正在停止服务...")
            process.terminate()
            process.wait()
            print("服务已停止")

    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    main()
