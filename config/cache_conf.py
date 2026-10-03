import json
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Any

import redis.asyncio as redis

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
CACHE_KEY_PREFIX = os.getenv('CACHE_KEY_PREFIX', 'day06_00:')


# 创建 Redis 的连接对象
redis_client = redis.Redis(
    host=REDIS_HOST,  # Redis 服务器的主机地址
    port=REDIS_PORT,  # Redis 端口号
    db=REDIS_DB,  # Redis 数据库编号，0~15
    decode_responses=True,  # 是否将字节数据解码为字符串
    socket_connect_timeout=1,
    socket_timeout=1,
)


# 设置 和 读取（字符串 和 列表或字典）"[{}]"
# 读取：字符串
async def get_cache(key: str):
    # return await redis_client.get(key)
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"获取缓存失败：{e}")
        return None


# 读取：列表或字典
async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)  # 序列化
        return None
    except Exception as e:
        print(f"获取 JSON 缓存失败：{e}")
        return None


# 设置缓存 setex(key, expire, value)
async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        if isinstance(value, (dict, list)):
            # 转字符串再存
            value = json.dumps(value, ensure_ascii=False)  # 中文正常保存
        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False


async def delete_cache(key: str) -> bool:
    """删除指定缓存键；实际删除返回 True，键不存在或操作失败返回 False。"""
    try:
        # Redis 返回删除的键数量，单个键转换为布尔值即可。
        return bool(await redis_client.delete(key))
    except Exception as e:
        print(f"删除缓存失败：{e}")
        return False


async def exists_cache(key: str) -> bool:
    """判断指定缓存键是否存在；键不存在或操作失败返回 False。"""
    try:
        # 调用方传入完整缓存键，与现有读写函数保持一致。
        return bool(await redis_client.exists(key))
    except Exception as e:
        print(f"检查缓存是否存在失败：{e}")
        return False
