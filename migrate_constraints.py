"""为独立课程库补唯一约束；重复记录先备份，迁移可重复执行。"""
import json
from datetime import datetime
from pathlib import Path

import pymysql
from sqlalchemy.engine import make_url

from config.db_conf import ASYNC_DATABASE_URL


def migrate_constraints(connection):
    with connection.cursor() as cursor:
        cursor.execute('SELECT DATABASE()')
        if cursor.fetchone()[0] != 'news_app_day06_00':
            raise RuntimeError('迁移只允许操作 news_app_day06_00。')
        cursor.execute("SELECT GET_LOCK('day06_00:constraints', 10)")
        if cursor.fetchone()[0] != 1:
            raise RuntimeError('另一迁移正在执行，请稍后重试。')
        try:
            plans = (
                ('user_token', 'user_id', 'expires_at', 'uq_user_token_user'),
                ('history', 'user_id, news_id', 'view_time', 'uq_history_user_news'),
            )
            for table, columns, time_column, index_name in plans:
                keys = columns.split(', ')
                equality = ' AND '.join(f'a.`{key}`=b.`{key}`' for key in keys)
                # 同组保留时间最新、时间相同则 ID 最大的一行。
                older = (f'(a.`{time_column}`<b.`{time_column}` OR '
                         f'(a.`{time_column}`=b.`{time_column}` AND a.id<b.id))')
                cursor.execute(f'SELECT DISTINCT a.* FROM `{table}` a '
                               f'JOIN `{table}` b ON {equality} AND {older}')
                rows = cursor.fetchall()
                if rows:
                    backup_dir = Path(__file__).parent / 'logs'
                    backup_dir.mkdir(exist_ok=True)
                    backup = backup_dir / f'migration-{table}-{datetime.now():%Y%m%d-%H%M%S-%f}.json'
                    fields = [field[0] for field in cursor.description]
                    backup.write_text(json.dumps(
                        [dict(zip(fields, row)) for row in rows],
                        ensure_ascii=False, default=str, indent=2,
                    ), encoding='utf-8')
                    cursor.execute(f'DELETE a FROM `{table}` a '
                                   f'JOIN `{table}` b ON {equality} AND {older}')
                    connection.commit()
                    print(f'{table}：已备份并合并 {len(rows)} 条重复记录。')
                cursor.execute('SELECT COUNT(*) FROM information_schema.statistics '
                               'WHERE table_schema=DATABASE() AND table_name=%s '
                               'AND index_name=%s AND non_unique=0', (table, index_name))
                if not cursor.fetchone()[0]:
                    quoted_columns = ', '.join(f'`{key}`' for key in keys)
                    cursor.execute(f'ALTER TABLE `{table}` ADD UNIQUE INDEX '
                                   f'`{index_name}` ({quoted_columns})')
                print(f'{table}：唯一约束已就绪。')
        finally:
            cursor.execute("SELECT RELEASE_LOCK('day06_00:constraints')")


def main():
    url = make_url(ASYNC_DATABASE_URL)
    if url.database != 'news_app_day06_00':
        raise SystemExit('迁移只允许使用 news_app_day06_00。')
    connection = pymysql.connect(
        host=url.host or '127.0.0.1', port=url.port or 3306,
        user=url.username, password=url.password or '',
        database=url.database, charset='utf8mb4',
    )
    try:
        migrate_constraints(connection)
    finally:
        connection.close()


if __name__ == '__main__':
    main()
