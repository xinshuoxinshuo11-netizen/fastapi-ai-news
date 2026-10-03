"""用真实内存数据库验证写入唯一性及 MySQL 锁定语句。"""
import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from crud import history, users
from models.history import History
from models.news import Category, News
from models.users import User, UserToken


class SessionAdapter:
    def __init__(self, session):
        self.session = session
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return self.session.execute(statement)

    async def commit(self):
        self.session.commit()

    async def refresh(self, instance):
        self.session.refresh(instance)

    def add(self, instance):
        self.session.add(instance)


class WriteConstraintTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        for model in (User, News, History):
            model.metadata.create_all(self.engine)
        self.session = Session(self.engine, expire_on_commit=False)
        self.db = SessionAdapter(self.session)
        self.session.add_all([
            User(id=1, username='测试用户', password='测试哈希'),
            Category(id=1, name='测试分类'),
            News(id=1, title='测试新闻', content='测试正文', category_id=1),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def assert_locking_reads(self):
        # SQLite 不支持行锁，另核对实际生成的 MySQL 语句。
        for statement in self.db.statements[:2]:
            self.assertIn('FOR UPDATE', str(statement.compile(dialect=mysql.dialect())))

    async def test_token_rotation_keeps_one_record_with_locking_reads(self):
        first = await users.create_token(self.db, 1)
        self.assert_locking_reads()
        second = await users.create_token(self.db, 1)
        self.assertNotEqual(first, second)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(UserToken)), 1)
        self.assertIsNone(await users.get_user_by_token(self.db, first))
        self.assertEqual((await users.get_user_by_token(self.db, second)).id, 1)

    async def test_repeated_history_keeps_one_record_with_locking_reads(self):
        first = await history.add_history(self.db, 1, 1)
        self.assert_locking_reads()
        second = await history.add_history(self.db, 1, 1)
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(History)), 1)

    async def test_database_rejects_two_tokens_for_one_user(self):
        await users.create_token(self.db, 1)
        token = self.session.scalar(select(UserToken))
        self.session.add(UserToken(user_id=1, token='另一枚测试令牌', expires_at=token.expires_at))
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()

    async def test_database_rejects_duplicate_user_news_history(self):
        await history.add_history(self.db, 1, 1)
        self.session.add(History(user_id=1, news_id=1))
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()
