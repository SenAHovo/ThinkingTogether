"""
结束占用8000端口的进程
"""

import subprocess
import sys

def kill_port_8000():
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
        print(f'已结束进程 PID: {pid}')
    else:
        print('未找到占用8000端口的进程')

if __name__ == '__main__':
    kill_port_8000()
