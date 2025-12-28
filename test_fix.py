#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复效果：
1. 历史对话能正确加载
2. 智能体对话结果能加载到前端
3. 调用智能体期间其他请求不阻塞
"""
import asyncio
import httpx
import time
import json
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:8000/api"

async def test_health_check():
    """测试健康检查"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"✓ 健康检查: {response.status_code} - {response.json()}")
        return response.status_code == 200

async def test_get_chats(token):
    """测试获取对话列表"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/chats",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"✓ 获取对话列表: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  对话数量: {data.get('total', 0)}")
            return True
        else:
            print(f"  错误: {response.text}")
            return False

async def test_send_message(chat_id, content, token):
    """测试发送消息（调用智能体）"""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.post(
            f"{BASE_URL}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"chat_id": chat_id, "content": content, "action": "send"}
        )
        print(f"✓ 发送消息: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  响应: {data.get('message', 'N/A')}")
            print(f"  状态: {data.get('status', 'N/A')}")
            return True
        else:
            print(f"  错误: {response.text}")
            return False

async def test_concurrent_requests(chat_id, token):
    """测试并发请求 - 验证其他请求在智能体调用时不阻塞"""
    print("\n=== 测试并发请求 ===")

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # 任务1: 发送消息（触发智能体调用，需要几秒到几十秒）
        async def send_agent_request():
            start = time.time()
            response = await client.post(
                f"{BASE_URL}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"chat_id": chat_id, "content": "请继续讨论", "action": "send"}
            )
            elapsed = time.time() - start
            print(f"  智能体请求响应时间: {elapsed:.2f}秒 - 状态: {response.status_code}")
            return response.status_code == 200, elapsed

        # 任务2: 同时获取对话列表（应该立即返回，不等待智能体）
        async def get_chats_concurrent():
            start = time.time()
            response = await client.get(
                f"{BASE_URL}/chats",
                headers={"Authorization": f"Bearer {token}"}
            )
            elapsed = time.time() - start
            print(f"  对话列表请求响应时间: {elapsed:.2f}秒 - 状态: {response.status_code}")
            return response.status_code == 200, elapsed

        # 任务3: 同时获取公开对话大厅（应该立即返回）
        async def get_public_hall():
            start = time.time()
            response = await client.get(f"{BASE_URL}/public/chats?limit=10")
            elapsed = time.time() - start
            print(f"  公开对话大厅请求响应时间: {elapsed:.2f}秒 - 状态: {response.status_code}")
            return response.status_code == 200, elapsed

        # 并发执行所有请求
        start_time = time.time()
        results = await asyncio.gather(
            send_agent_request(),
            get_chats_concurrent(),
            get_public_hall(),
            return_exceptions=True
        )
        total_time = time.time() - start_time

        # 验证结果
        agent_ok, agent_time = results[0]
        chats_ok, chats_time = results[1]
        public_ok, public_time = results[2]

        print(f"\n  总耗时: {total_time:.2f}秒")
        print(f"  智能体请求是否先返回: {agent_time < 1.0}")
        print(f"  对话列表请求是否立即返回(< 1秒): {chats_time < 1.0}")
        print(f"  公开对话大厅请求是否立即返回(< 1秒): {public_time < 1.0}")

        # 判断是否通过
        success = (
            agent_ok and chats_ok and public_ok and
            agent_time < 1.0 and  # 智能体请求应该立即返回（非阻塞）
            chats_time < 1.0 and  # 对话列表应该立即返回
            public_time < 1.0     # 公开对话大厅应该立即返回
        )

        return success

async def main():
    print("=== 测试修复效果 ===\n")

    # 1. 健康检查
    print("1. 健康检查")
    if not await test_health_check():
        print("✗ 服务器未运行，请先启动后端服务器")
        return

    # 登录获取token（需要根据实际情况修改）
    print("\n2. 登录测试")
    async with httpx.AsyncClient() as client:
        # 这里使用测试账号
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"username": "testuser", "password": "test123"}
        )
        if response.status_code != 200:
            print("✗ 登录失败，请检查账号密码")
            return

        token_data = response.json()
        token = token_data.get("access_token")
        print(f"✓ 登录成功")

    # 3. 创建测试对话
    print("\n3. 创建测试对话")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chats",
            headers={"Authorization": f"Bearer {token}"},
            json={"topic": "测试并发请求"}
        )
        if response.status_code == 200:
            chat_id = response.json().get("chat_id")
            print(f"✓ 创建对话成功: {chat_id}")
        else:
            print(f"✗ 创建对话失败: {response.text}")
            return

    # 4. 测试获取对话列表（验证历史对话加载）
    print("\n4. 测试历史对话加载")
    if not await test_get_chats(token):
        print("✗ 获取对话列表失败")
        return

    # 5. 测试发送消息（触发智能体）
    print("\n5. 测试发送消息（触发智能体）")
    if not await test_send_message(chat_id, "请继续", token):
        print("✗ 发送消息失败")
        return

    # 6. 测试并发请求（核心测试）
    print("\n6. 测试并发请求（验证非阻塞）")
    if await test_concurrent_requests(chat_id, token):
        print("\n✓ 并发请求测试通过 - 其他请求在智能体调用期间不阻塞")
    else:
        print("\n✗ 并发请求测试失败 - 存在阻塞问题")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(main())
