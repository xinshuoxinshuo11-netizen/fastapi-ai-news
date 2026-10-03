"""验证缓存删除和存在判断的返回约定，模拟 Redis 异常，不连接真实服务。"""
import unittest
from unittest.mock import AsyncMock, patch

from config.cache_conf import delete_cache, exists_cache, redis_client


class CacheHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_delete_returns_boolean_for_existing_and_missing_keys(self):
        for count, expected in ((1, True), (0, False)):
            with self.subTest(count=count), patch.object(
                redis_client, 'delete', AsyncMock(return_value=count)
            ) as delete:
                result = await delete_cache('day06_00:test:删除')
                self.assertIs(result, expected)
                delete.assert_awaited_once_with('day06_00:test:删除')

    async def test_exists_returns_boolean_for_existing_and_missing_keys(self):
        for count, expected in ((1, True), (0, False)):
            with self.subTest(count=count), patch.object(
                redis_client, 'exists', AsyncMock(return_value=count)
            ) as exists:
                result = await exists_cache('day06_00:test:存在')
                self.assertIs(result, expected)
                exists.assert_awaited_once_with('day06_00:test:存在')

    async def test_delete_failure_returns_false(self):
        with patch.object(redis_client, 'delete', AsyncMock(
            side_effect=ConnectionError('测试缓存不可用')
        )):
            self.assertIs(await delete_cache('day06_00:test:删除'), False)

    async def test_exists_failure_returns_false(self):
        with patch.object(redis_client, 'exists', AsyncMock(
            side_effect=ConnectionError('测试缓存不可用')
        )):
            self.assertIs(await exists_cache('day06_00:test:存在'), False)


if __name__ == '__main__':
    unittest.main()
