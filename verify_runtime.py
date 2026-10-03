"""在独立课程库中验证真实 HTTP 流程；只清理本次创建的测试账号。"""
import concurrent.futures
import json
import time
import urllib.error
import urllib.request
import uuid

import pymysql
from sqlalchemy.engine import make_url
from config.db_conf import ASYNC_DATABASE_URL


def main():
    url = make_url(ASYNC_DATABASE_URL)
    if url.database != 'news_app_day06_00':
        raise SystemExit('运行验收只允许操作本项目独立库。')
    connection = pymysql.connect(host=url.host, port=url.port or 3306,
                                 user=url.username, password=url.password,
                                 database=url.database, charset='utf8mb4', autocommit=True)
    base = 'http://127.0.0.1:19000'
    checked = 0
    created_ids = []
    username = '验收_' + uuid.uuid4().hex[:12]

    def check(condition, message):
        nonlocal checked
        if not condition:
            raise AssertionError(message)
        checked += 1
        print(f'通过 {checked:02d}：{message}')

    def request(method, path, data=None, token=None, expected=200, extra_headers=None, return_full=False):
        headers = {'Content-Type': 'application/json', **(extra_headers or {})}
        if token:
            headers['Authorization'] = token
        body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
        req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        status = response.code
        content = json.load(response)
        check(status == expected, f'{method} {path} 状态码 {expected}')
        return content if return_full else content.get('data')

    def concurrent_posts(path, data, token=None):
        """用独立连接并发提交，只返回状态码，不输出令牌或密码。"""
        def submit(_):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = token
            req = urllib.request.Request(base + path, method='POST', headers=headers,
                                         data=json.dumps(data).encode())
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            return list(executor.map(submit, range(6)))

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT DATABASE()')
            check(cursor.fetchone()[0] == 'news_app_day06_00', '连接独立数据库')
        categories = request('GET', '/api/news/categories')
        check(len(categories) == 8, '真实分类共 8 条')
        first = request('GET', '/api/news/categories?skip=0&limit=1')
        second = request('GET', '/api/news/categories?skip=1&limit=1')
        check(first[0]['id'] != second[0]['id'], '分类分页缓存隔离')
        cold = request('GET', '/api/news/list?categoryId=1&page=1&pageSize=10')
        warm = request('GET', '/api/news/list?categoryId=1&page=1&pageSize=10')
        check(cold == warm and cold['list'][0]['content'] and cold['list'][0]['publishTime'], '冷暖列表字段、正文与时间一致')
        page2 = request('GET', '/api/news/list?categoryId=1&page=2&pageSize=10')
        check(set(x['id'] for x in cold['list']).isdisjoint(x['id'] for x in page2['list']), '相邻页新闻不重复')
        request('GET', '/api/news/list?categoryId=1&pageSize=0', expected=422)
        request('GET', '/api/news/detail?id=999999', expected=404)
        detail1 = request('GET', '/api/news/detail?id=403')
        detail2 = request('GET', '/api/news/detail?id=403')
        check(detail2['views'] == detail1['views'] + 1 and detail2['content'], '缓存命中详情保留正文，浏览量递增')
        def read_detail(_):
            response = urllib.request.urlopen(base + '/api/news/detail?id=403', timeout=20)
            return json.load(response)['code']
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            codes = list(executor.map(read_detail, range(6)))
        with connection.cursor() as cursor:
            cursor.execute('SELECT views FROM news WHERE id=403')
            check(all(code == 200 for code in codes) and cursor.fetchone()[0] == detail2['views'] + 6, '并发 6 次访问无浏览量丢失')
        auth = request('POST', '/api/user/register', {'username': username, 'password': 'Course123!'})
        created_ids.append(auth['userInfo']['id'])
        token = auth['token']
        request('POST', '/api/user/register', {'username': username, 'password': 'Course123!'}, expected=400)
        request('POST', '/api/user/login', {'username': username, 'password': '错误密码'}, expected=401)
        login = request('POST', '/api/user/login', {'username': username, 'password': 'Course123!'})
        request('GET', '/api/user/info', token=token, expected=401)
        # 删除的只是本次临时账号的令牌，验证并发首次登录也只创建一行。
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM user_token WHERE user_id=%s', (created_ids[0],))
        codes = concurrent_posts('/api/user/login', {'username': username, 'password': 'Course123!'})
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM user_token WHERE user_id=%s', (created_ids[0],))
            check(codes == [200] * 6 and cursor.fetchone()[0] == 1, '并发首次登录只产生一条令牌记录')
        login = request('POST', '/api/user/login', {'username': username, 'password': 'Course123!'})
        token = login['token']
        request('GET', '/api/user/info', token='invalid', expected=401)
        info = request('GET', '/api/user/info', token=token)
        check(info['username'] == username, '登录身份准确')
        request('PUT', '/api/user/update', {'bio': '真实接口验收简介'}, token)
        check(request('GET', '/api/user/info', token=token)['bio'] == '真实接口验收简介', '简介更新持久化')
        request('POST', '/api/favorite/add', {'newsId': 3}, token)
        duplicate = request('POST', '/api/favorite/add', {'newsId': 3}, token, expected=400, return_full=True)
        check(duplicate['message'] == '该新闻已收藏', '重复收藏提示准确')
        check(request('GET', '/api/favorite/check?newsId=3', token=token)['isFavorite'], '收藏状态正确')
        favorites = request('GET', '/api/favorite/list', token=token)
        check(favorites['total'] == 1 and favorites['list'][0]['publishTime'], '收藏联表与时间字段正确')
        request('DELETE', '/api/favorite/remove?newsId=3', token=token)
        check(not request('GET', '/api/favorite/check?newsId=3', token=token)['isFavorite'], '取消收藏生效')
        request('POST', '/api/favorite/add', {'newsId': 4}, token)
        request('DELETE', '/api/favorite/clear', token=token)
        check(request('GET', '/api/favorite/list', token=token)['total'] == 0, '清空收藏生效')
        codes = concurrent_posts('/api/history/add', {'newsId': 17}, token)
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM history WHERE user_id=%s AND news_id=17', (created_ids[0],))
            check(codes == [200] * 6 and cursor.fetchone()[0] == 1, '并发首次浏览只产生一条历史记录')
        history = request('POST', '/api/history/add', {'newsId': 17}, token)
        # 课程 SQL 的 DATETIME 精度为秒，等待跨秒后才能验证时间真实更新。
        time.sleep(1.05)
        again = request('POST', '/api/history/add', {'newsId': 17}, token)
        check(history['id'] == again['id'] and again['view_time'] > history['view_time'], '重复浏览更新原记录时间')
        history_list = request('GET', '/api/history/list', token=token)
        history_id = history_list['list'][0]['historyId']
        check(history_id != 17 and history_list['list'][0]['publishTime'], '历史 ID 与新闻 ID 不同，字段正确')
        other = request('POST', '/api/user/register', {'username': username + '_2', 'password': 'Course123!'})
        created_ids.append(other['userInfo']['id'])
        request('DELETE', f'/api/history/delete/{history_id}', token=other['token'], expected=404)
        request('DELETE', f'/api/history/delete/{history_id}', token=token)
        check(request('GET', '/api/history/list', token=token)['total'] == 0, '按历史 ID 删除，只影响本人')
        request('POST', '/api/history/add', {'newsId': 17}, token)
        request('DELETE', '/api/history/clear', token=token)
        check(request('GET', '/api/history/list', token=token)['total'] == 0, '历史清空生效')
        request('PUT', '/api/user/password', {'oldPassword': '错误密码', 'newPassword': 'Course456!'}, token, expected=400)
        request('PUT', '/api/user/password', {'oldPassword': 'Course123!', 'newPassword': 'Course456!'}, token)
        request('POST', '/api/user/login', {'username': username, 'password': 'Course123!'}, expected=401)
        request('POST', '/api/user/login', {'username': username, 'password': 'Course456!'})
        print(f'运行验收完成：{checked} 项断言通过；覆盖全部 17 个业务接口。')
    finally:
        # 仅删除本次随机创建的两名测试用户；外键按顺序清理，不影响素材 admin。
        with connection.cursor() as cursor:
            for user_id in created_ids:
                for table in ['favorite', 'history', 'user_token', 'ai_chat']:
                    cursor.execute(f'DELETE FROM `{table}` WHERE user_id=%s', (user_id,))
                cursor.execute('DELETE FROM user WHERE id=%s AND username LIKE %s', (user_id, username + '%'))
        connection.close()


if __name__ == '__main__':
    main()
