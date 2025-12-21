"""
数据库配置文件
用于管理数据库连接参数
"""

import os
from typing import Dict, Any


# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'thinking_together',
    'port': 3306,
    'charset': 'utf8mb4'
}


def get_db_config() -> Dict[str, Any]:
    """
    获取数据库配置

    Returns:
        Dict: 数据库配置字典
    """
    # 优先从环境变量读取，如果没有则使用默认配置
    config = {
        'host': os.getenv('DB_HOST', DB_CONFIG['host']),
        'user': os.getenv('DB_USER', DB_CONFIG['user']),
        'password': os.getenv('DB_PASSWORD', DB_CONFIG['password']),
        'database': os.getenv('DB_NAME', DB_CONFIG['database']),
        'port': int(os.getenv('DB_PORT', DB_CONFIG['port'])),
        'charset': os.getenv('DB_CHARSET', DB_CONFIG['charset'])
    }
    return config


def test_connection() -> bool:
    """
    测试数据库连接

    Returns:
        bool: 连接是否成功
    """
    try:
        from dev.mysql.db_utils import DatabaseManager
        config = get_db_config()
        db = DatabaseManager(**config)
        if db.connect():
            db.disconnect()
            return True
        return False
    except Exception as e:
        print(f"数据库连接测试失败: {e}")
        return False


if __name__ == "__main__":
    # 测试配置
    print("数据库配置:")
    for key, value in get_db_config().items():
        if key == 'password':
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")

    # 测试连接
    print(f"\n数据库连接测试: {'成功' if test_connection() else '失败'}")