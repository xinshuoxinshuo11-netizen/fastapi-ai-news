"""仅首次向本项目的空数据库导入课程数据，重复运行不覆盖已有数据。"""
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT
from sqlalchemy.engine import make_url

from config.db_conf import ASYNC_DATABASE_URL
from migrate_constraints import migrate_constraints


def main():
    url = make_url(ASYNC_DATABASE_URL)
    database = url.database
    if database != 'news_app_day06_00':
        raise SystemExit('为避免影响其他项目，初始化只允许使用 news_app_day06_00。')
    connection = pymysql.connect(
        host=url.host or '127.0.0.1', port=url.port or 3306,
        user=url.username, password=url.password or '', charset='utf8mb4',
        client_flag=CLIENT.MULTI_STATEMENTS,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s', (database,))
            count = cursor.fetchone()[0]
            if count:
                print('数据库已包含表，本次跳过导入，保留已有数据。')
            else:
                sql = (Path(__file__).parent / 'sql' / 'database.day06-00.sql').read_text(encoding='utf-8')
                cursor.execute(sql)
                while cursor.nextset():
                    pass
                connection.commit()
                print('课程 SQL 已导入独立数据库。')
            cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s', (database,))
            print(f'数据表：{cursor.fetchone()[0]} 张')
            for table in ['news_category', 'news', 'user']:
                cursor.execute(f'SELECT COUNT(*) FROM `{database}`.`{table}`')
                print(f'{table}：{cursor.fetchone()[0]} 条')
        connection.select_db(database)
        migrate_constraints(connection)
    finally:
        connection.close()


if __name__ == '__main__':
    main()
