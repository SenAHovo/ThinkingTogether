"""
验证码管理模块
处理验证码的生成、存储、验证和过期管理
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
import pymysql


class VerificationCodeManager:
    """验证码管理器"""

    def __init__(self, db_config: Dict):
        """
        初始化验证码管理器

        Args:
            db_config: 数据库配置字典
        """
        self.db_config = db_config

    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config)

    @staticmethod
    def generate_code(length: int = 6) -> str:
        """
        生成数字验证码

        Args:
            length: 验证码长度，默认6位

        Returns:
            str: 生成的验证码
        """
        return ''.join(random.choices(string.digits, k=length))

    def create_verification_code(
        self,
        email: str,
        purpose: str,
        expiry_minutes: int = 10
    ) -> Optional[str]:
        """
        创建验证码并存储到数据库

        Args:
            email: 用户邮箱
            purpose: 用途 (register, reset_password, change_password, bind_email)
            expiry_minutes: 过期时间（分钟），默认10分钟

        Returns:
            str: 生成的验证码，失败返回None
        """
        code = self.generate_code(6)
        expires_at = datetime.now() + timedelta(minutes=expiry_minutes)

        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 插入验证码记录
            sql = """
                INSERT INTO email_verification_codes (email, code, purpose, expires_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (email, code, purpose, expires_at))
            conn.commit()

            print(f"✅ 验证码已创建: {email} - {purpose} - {code}")
            return code

        except pymysql.Error as e:
            print(f"❌ 创建验证码失败: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    def verify_code(
        self,
        email: str,
        code: str,
        purpose: str
    ) -> bool:
        """
        验证验证码是否有效

        Args:
            email: 用户邮箱
            code: 验证码
            purpose: 用途

        Returns:
            bool: 验证是否成功
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 查询验证码
            sql = """
                SELECT id, expires_at, used
                FROM email_verification_codes
                WHERE email = %s AND code = %s AND purpose = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(sql, (email, code, purpose))
            result = cursor.fetchone()

            if not result:
                print(f"❌ 验证码无效: {email} - {code} - {purpose}")
                return False

            record_id, expires_at, used = result

            # 检查是否已使用
            if used:
                print(f"❌ 验证码已被使用: {email} - {code}")
                return False

            # 检查是否过期
            if datetime.now() > expires_at:
                print(f"❌ 验证码已过期: {email} - {code}")
                return False

            # 标记为已使用
            update_sql = """
                UPDATE email_verification_codes
                SET used = 1
                WHERE id = %s
            """
            cursor.execute(update_sql, (record_id,))
            conn.commit()

            print(f"✅ 验证码验证成功: {email} - {purpose}")
            return True

        except pymysql.Error as e:
            print(f"❌ 验证码验证失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def check_rate_limit(self, email: str, purpose: str, interval_seconds: int = 60) -> bool:
        """
        检查发送频率限制

        Args:
            email: 用户邮箱
            purpose: 用途
            interval_seconds: 间隔时间（秒），默认60秒

        Returns:
            bool: True表示可以发送，False表示需要等待
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 查询最近一次发送时间
            sql = """
                SELECT created_at
                FROM email_verification_codes
                WHERE email = %s AND purpose = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(sql, (email, purpose))
            result = cursor.fetchone()

            if not result:
                return True  # 从未发送过，可以发送

            last_sent_at = result[0]
            time_since_last = (datetime.now() - last_sent_at).total_seconds()

            return time_since_last >= interval_seconds

        except pymysql.Error as e:
            print(f"❌ 检查频率限制失败: {e}")
            return True  # 出错时允许发送
        finally:
            if conn:
                conn.close()

    def cleanup_expired_codes(self):
        """清理过期的验证码记录"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = """
                DELETE FROM email_verification_codes
                WHERE expires_at < NOW() OR used = 1
            """
            cursor.execute(sql)
            deleted_count = cursor.rowcount
            conn.commit()

            print(f"✅ 清理了 {deleted_count} 条过期/已使用的验证码记录")
            return deleted_count

        except pymysql.Error as e:
            print(f"❌ 清理过期验证码失败: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
