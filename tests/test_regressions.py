"""使用内存数据库复现接口字段、历史 ID 和缓存问题，不连接用户数据库。"""
import asyncio
import json
import time
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crud import history, news_cache
from models.history import History
from models.favorite import Favorite
from models.news import News, Category
from models.users import User
from routers import news as news_router
from config.cache_conf import redis_client
from schemas.favorite import FavoriteNewsItemResponse
from schemas.history import HistoryNewsItemResponse


class AsyncSessionAdapter:
    """为真实 SQLite 会话提供业务函数使用的异步方法。"""
    def __init__(self, session):
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def commit(self):
        self.session.commit()

    async def refresh(self, instance):
        self.session.refresh(instance)

    def add(self, instance):
        self.session.add(instance)


class RegressionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        User.metadata.create_all(self.engine)
        News.metadata.create_all(self.engine)
        History.metadata.create_all(self.engine)
        Favorite.metadata.create_all(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.db = AsyncSessionAdapter(self.session)
        self.session.add_all([
            User(id=1, username='用户一', password='测试哈希'),
            User(id=2, username='用户二', password='测试哈希'),
            Category(id=1, name='科技', sort_order=1),
            Category(id=2, name='财经', sort_order=2),
            News(id=17, title='测试新闻', content='完整正文', description='测试摘要',
                 category_id=1, views=10, publish_time=datetime(2026, 10, 3)),
            News(id=23, title='另一条新闻', content='另一段正文', category_id=1, views=0),
            History(id=3, user_id=1, news_id=17),
            History(id=8, user_id=2, news_id=17),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    async def test_history_deletes_history_id_instead_of_news_id(self):
        result = await history.delete_history(self.db, 1, 3)
        self.assertTrue(result)
        self.assertIsNone(self.session.get(History, 3))
        self.assertIsNotNone(self.session.get(History, 8))

    async def test_history_cannot_delete_another_users_record(self):
        self.assertFalse(await history.delete_history(self.db, 1, 8))
        self.assertIsNotNone(self.session.get(History, 8))

    async def test_favorite_and_history_publish_time_contract(self):
        data = jsonable_encoder(self.session.get(News, 17))
        favorite = FavoriteNewsItemResponse.model_validate({
            **data, 'favorite_id': 4, 'favorite_time': datetime(2026, 10, 3)})
        entry = HistoryNewsItemResponse.model_validate({
            **data, 'history_id': 3, 'view_time': datetime(2026, 10, 3)})
        for model in [favorite, entry]:
            self.assertIn('publishTime', jsonable_encoder(model))

    async def test_cached_list_keeps_the_same_payload(self):
        stored = {}
        async def save(category_id, page, size, data):
            stored['value'] = data
        async def read(*args):
            return stored.get('value')
        with patch.object(news_cache, 'get_cache_news_list', side_effect=read), \
             patch.object(news_cache, 'set_cache_news_list', side_effect=save):
            first = await news_cache.get_news_list(self.db, 1, 0, 10)
            second = await news_cache.get_news_list(self.db, 1, 0, 10)
            self.assertEqual(jsonable_encoder(first), jsonable_encoder(second))
            self.assertEqual(second[0].content, '完整正文')

    async def test_categories_cache_respects_pagination(self):
        stored = {}
        async def read(*args):
            return stored.get(args)
        async def save(data, *args, **kwargs):
            stored[args] = data
        with patch.object(news_cache, 'get_cached_categories', side_effect=read), \
             patch.object(news_cache, 'set_cache_categories', side_effect=save):
            first = await news_cache.get_categories(self.db, 0, 1)
            second = await news_cache.get_categories(self.db, 1, 1)
            self.assertEqual(first[0]['id'], 1)
            self.assertEqual(second[0]['id'], 2)

    async def test_cached_detail_returns_updated_views(self):
        detached = News(id=17, title='测试新闻', content='完整正文',
                        category_id=1, views=10, publish_time=datetime(2026, 10, 3))
        with patch.object(news_cache, 'get_news_detail', AsyncMock(return_value=detached)), \
             patch.object(news_cache, 'get_related_news', AsyncMock(return_value=[])), \
             patch.object(news_router, 'cache_news_detail', AsyncMock()):
            response = await news_router.get_news_detail(17, self.db)
            self.assertEqual(response['data']['views'], 11)

    async def test_new_users_get_the_actual_creation_time(self):
        first = self.session.get(User, 1)
        time.sleep(0.02)
        second = User(username='稍后创建', password='测试哈希')
        self.session.add(second)
        self.session.commit()
        self.assertGreater(second.created_at, first.created_at)

    async def test_favorite_and_history_use_the_same_local_clock(self):
        favorite = Favorite(user_id=1, news_id=23)
        entry = History(user_id=1, news_id=23)
        self.session.add_all([favorite, entry])
        self.session.commit()
        self.assertLess(abs((favorite.created_at - entry.view_time).total_seconds()), 2)

    async def test_redis_failure_still_returns_database_news(self):
        with patch.object(redis_client, 'get', AsyncMock(side_effect=ConnectionError('测试缓存不可用'))), \
             patch.object(redis_client, 'setex', AsyncMock(side_effect=ConnectionError('测试缓存不可用'))):
            result = await news_cache.get_news_list(self.db, 1, 0, 10)
            self.assertEqual(result[0].content, '完整正文')


if __name__ == '__main__':
    unittest.main()
