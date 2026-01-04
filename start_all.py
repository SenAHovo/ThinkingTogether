#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智炬五维协同学习系统 - 统一启动脚本
同时启动前端和后端服务
"""
import sys
import os
import subprocess
import time
import signal


# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def check_port_8000_listening():
    """检查8000端口是否处于监听状态"""
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True
    )

    for line in result.stdout.split('\n'):
        if ':8000' in line and 'LISTENING' in line:
            return True
    return False


def kill_port_8000():
    """结束占用8000端口的进程"""
    print("检查 8000 端口占用情况...")

    # 查找占用8000端口的进程
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True
    )

    # 解析输出找到PID
    pid = None
    for line in result.stdout.split('\n'):
        if ':8000' in line and 'LISTENING' in line:
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                break

    if pid:
        # 结束进程
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
        print(f'✓ 已结束占用 8000 端口的进程 PID: {pid}')
    else:
        print('✓ 8000 端口未被占用')


def start_backend():
    """启动后端服务"""
    print("\n" + "=" * 60)
    print("启动后端服务...")
    print("=" * 60)

    # 创建日志文件路径
    log_file = os.path.join(project_root, "backend_output.log")

    # 导入应用
    try:
        from dev.api.server import app
        import uvicorn
    except ImportError as e:
        print(f"✗ 导入后端应用失败: {e}")
        return None

    # 打开日志文件用于写入
    log_handle = open(log_file, 'w', encoding='utf-8')

    # 创建后端进程
    # 使用 subprocess 启动一个新的 Python 进程运行 uvicorn
    backend_code = """
import sys
import os
import uvicorn

# 确保项目根目录在Python路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入应用
from dev.api.server import app

if __name__ == "__main__":
    print("=== 智炬五维协同学习系统 API 服务器 ===")
    print("正在启动服务器...")
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\\n服务器已停止")
"""

    # 将后端代码写入临时文件
    temp_backend_script = os.path.join(project_root, "_temp_backend.py")
    with open(temp_backend_script, 'w', encoding='utf-8') as f:
        f.write(backend_code)

    # 启动后端进程，输出重定向到日志文件
    # 使用 CREATE_NEW_PROCESS_GROUP 以便能够单独终止进程
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    process = subprocess.Popen(
        ['python', temp_backend_script],
        stdout=log_handle,
        stderr=log_handle,
        creationflags=CREATE_NEW_PROCESS_GROUP
    )

    print(f"✓ 后端服务已启动")
    print(f"  - 日志文件: {log_file}")
    print("  - API地址: http://localhost:8000")
    print("  - API文档: http://localhost:8000/docs")

    return process


def start_frontend():
    """启动前端服务"""
    print("\n" + "=" * 60)
    print("启动前端服务...")
    print("=" * 60)

    # 切换到前端目录
    frontend_dir = os.path.join(project_root, "FrontDev")

    if not os.path.exists(frontend_dir):
        print(f"✗ 前端目录不存在: {frontend_dir}")
        return None

    os.chdir(frontend_dir)
    print(f"工作目录: {os.getcwd()}")

    # 检查依赖
    if not os.path.exists("node_modules"):
        print("\n首次运行，正在安装前端依赖...")
        result = subprocess.run(["npm", "install"], shell=True)
        if result.returncode != 0:
            print("✗ 依赖安装失败")
            return None
        print("✓ 依赖安装完成")

    print("\n启动前端开发服务器...")

    # 启动前端（在当前窗口）
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        shell=True
    )

    return process


def main():
    """主函数"""
    print("=" * 60)
    print("智炬五维协同学习系统 - 统一启动")
    print("=" * 60)

    # 1. 先检查并释放8000端口
    kill_port_8000()

    # 2. 启动后端服务（在后台）
    backend_process = start_backend()

    if not backend_process:
        print("\n✗ 后端启动失败")
        return

    log_file = os.path.join(project_root, "backend_output.log")
    temp_backend_script = os.path.join(project_root, "_temp_backend.py")

    # 等待后端启动完成（通过检查端口监听状态）
    print("\n等待后端服务启动...")
    max_wait_time = 60  # 最多等待60秒
    check_interval = 1  # 每1秒检查一次
    waited_time = 0

    while waited_time < max_wait_time:
        if check_port_8000_listening():
            print(f"✓ 后端服务已启动（耗时 {waited_time} 秒）")
            break
        time.sleep(check_interval)
        waited_time += check_interval
        # 每5秒显示一次进度
        if waited_time % 5 == 0:
            print(f"  正在等待后端启动... ({waited_time}/{max_wait_time}秒)")
    else:
        print("\n✗ 后端服务启动超时（超过60秒未响应）")
        print(f"\n后端日志文件：{log_file}")
        print("后端日志最后20行：")
        print("-" * 60)

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 显示最后20行
                for line in lines[-20:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"无法读取日志文件：{e}")

        print("-" * 60)
        print("\n建议：")
        print("1. 检查后端日志文件中的错误信息")
        print("2. 检查数据库连接是否正常")
        print("3. 检查必要的 Python 包是否已安装")

        if backend_process:
            backend_process.terminate()

        # 清理临时文件
        if os.path.exists(temp_backend_script):
            os.remove(temp_backend_script)

        return

    # 3. 启动前端服务（在当前窗口）
    frontend_process = start_frontend()

    if not frontend_process:
        print("\n✗ 前端启动失败")
        if backend_process:
            backend_process.terminate()
        # 清理临时文件
        if os.path.exists(temp_backend_script):
            os.remove(temp_backend_script)
        return

    print("\n" + "=" * 60)
    print("服务启动完成！")
    print("=" * 60)
    print("\n访问地址：")
    print("  - 前端界面: http://localhost:5173")
    print("  - 后端API:  http://localhost:8000")
    print("  - API文档:  http://localhost:8000/docs")
    print(f"\n提示：")
    print(f"  - 后端服务在后台运行，日志：{log_file}")
    print("  - 前端服务在当前窗口运行")
    print("  - 按 Ctrl+C 同时停止前后端服务")
    print("=" * 60 + "\n")

    try:
        # 等待前端进程
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")

        # 停止前端
        if frontend_process:
            frontend_process.terminate()
            print("✓ 前端服务已停止")

        # 停止后端
        if backend_process:
            backend_process.terminate()
            # 同时清理8000端口
            kill_port_8000()
            print("✓ 后端服务已停止")

        # 清理临时文件
        if os.path.exists(temp_backend_script):
            os.remove(temp_backend_script)
            print("✓ 临时文件已清理")

        print("\n所有服务已停止")


if __name__ == "__main__":
    main()
