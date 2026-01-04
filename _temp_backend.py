
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
        print("\n服务器已停止")
