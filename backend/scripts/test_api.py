#!/usr/bin/env python3
"""
API 测试脚本
用于测试后端 API 是否正常工作
"""
import httpx
import asyncio
import sys


BASE_URL = "http://localhost:8000/api"


async def test_api():
    print("=" * 50)
    print("API 测试")
    print("=" * 50)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # 测试健康检查
        print("\n[1] 测试健康检查...")
        try:
            resp = await client.get("/../health")  # 注意：需要去掉 /api 前缀
            print(f"状态码: {resp.status_code}")
            print(f"响应: {resp.json()}")
        except Exception as e:
            print(f"请求失败: {e}")

        # 测试根路径
        print("\n[2] 测试根路径...")
        try:
            resp = await client.get("/")
            print(f"状态码: {resp.status_code}")
            print(f"响应: {resp.json()}")
        except Exception as e:
            print(f"请求失败: {e}")

        # 测试登录
        print("\n[3] 测试登录...")
        try:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"}
            )
            print(f"状态码: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token")
                print(f"登录成功! Token: {token[:20]}...")
            else:
                print(f"登录失败: {resp.json()}")
        except Exception as e:
            print(f"请求失败: {e}")

        # 使用 token 测试受保护的端点
        print("\n[4] 测试获取当前用户信息...")
        try:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"}
            )
            token = resp.json().get("token")

            resp = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"状态码: {resp.status_code}")
            print(f"用户信息: {resp.json()}")
        except Exception as e:
            print(f"请求失败: {e}")

        # 测试主机列表
        print("\n[5] 测试主机列表...")
        try:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"}
            )
            token = resp.json().get("token")

            resp = await client.get(
                "/hosts",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"状态码: {resp.status_code}")
            print(f"主机数量: {resp.json().get('total', 0)}")
        except Exception as e:
            print(f"请求失败: {e}")

        # 测试流程列表
        print("\n[6] 测试流程列表...")
        try:
            resp = await client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"}
            )
            token = resp.json().get("token")

            resp = await client.get(
                "/flows",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"状态码: {resp.status_code}")
            print(f"流程数量: {resp.json().get('total', 0)}")
        except Exception as e:
            print(f"请求失败: {e}")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_api())
