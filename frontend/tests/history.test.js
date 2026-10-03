// 用内存存储验证服务端历史 ID 与游客新闻 ID 两条删除路径。
import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
const saved = new Map()
globalThis.localStorage = {
  getItem: key => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: key => saved.delete(key),
}
const { useHistoryStore } = await import('../src/store/modules/history.js')
const { useUserStore } = await import('../src/store/user.js')

test('服务端删除按历史 ID，不误删同 ID 的新闻', () => {
  setActivePinia(createPinia())
  const store = useHistoryStore()
  store.history = [{ id: 17, historyId: 3 }, { id: 3, historyId: 8 }]
  store.removeHistory(3, true)
  assert.deepEqual(store.history.map(item => item.id), [3])
  assert.deepEqual(JSON.parse(saved.get('news_history:guest')), [{ id: 3, historyId: 8 }])
})

test('游客本地删除继续按新闻 ID', async () => {
  setActivePinia(createPinia())
  const store = useHistoryStore()
  store.history = [{ id: 17 }, { id: 3 }]
  const result = await store.removeHistoryApi(17)
  assert.equal(result.isLocal, true)
  assert.deepEqual(store.history.map(item => item.id), [3])
})

test('账号切换后请求失败也不会加载上一账号的历史', async () => {
  saved.clear()
  setActivePinia(createPinia())
  const user = useUserStore(), store = useHistoryStore()
  const original = axios.get
  try {
    user.$patch({ isLogin: true, token: '甲的测试令牌', userInfo: { id: 1 } })
    axios.get = async () => ({ data: { code: 200, data: { list: [{ id: 17, historyId: 3 }] } } })
    await store.getHistoryListApi()
    assert.equal(saved.has('news_history:user:1'), true)
    user.logout()
    assert.deepEqual(store.history, [])
    user.$patch({ isLogin: true, token: '乙的测试令牌', userInfo: { id: 2 } })
    axios.get = async () => { throw new Error('模拟网络错误') }
    await store.getHistoryListApi()
    store.loadHistory()
    assert.deepEqual(store.history, [])
  } finally { axios.get = original }
})

test('迟到的历史响应不能覆盖切换后的账号', async () => {
  saved.clear()
  setActivePinia(createPinia())
  const user = useUserStore(), store = useHistoryStore()
  const original = axios.get
  let finish
  try {
    user.$patch({ isLogin: true, token: '甲的测试令牌', userInfo: { id: 1 } })
    axios.get = () => new Promise(resolve => { finish = resolve })
    const pending = store.getHistoryListApi()
    user.logout()
    user.$patch({ isLogin: true, token: '乙的测试令牌', userInfo: { id: 2 } })
    finish({ data: { code: 200, data: { list: [{ id: 17, historyId: 3 }] } } })
    assert.equal((await pending).stale, true)
    assert.deepEqual(store.history, [])
    assert.equal(saved.has('news_history:user:2'), false)
  } finally { axios.get = original }
})

test('旧版无归属的共享历史不会迁移给当前用户', () => {
  saved.clear()
  saved.set('news_history', JSON.stringify([{ id: 17 }]))
  setActivePinia(createPinia())
  const store = useHistoryStore()
  store.loadHistory()
  assert.deepEqual(store.history, [])
  assert.equal(saved.has('news_history'), false)
})

test('迟到的用户资料不能把历史缓存归属改回旧账号', async () => {
  setActivePinia(createPinia())
  const user = useUserStore()
  const original = axios.get
  let finish
  try {
    user.$patch({ isLogin: true, token: '甲的测试令牌', userInfo: { id: 1 } })
    axios.get = () => new Promise(resolve => { finish = resolve })
    const pending = user.getUserInfoDetail()
    user.logout()
    user.$patch({ isLogin: true, token: '乙的测试令牌', userInfo: { id: 2 } })
    finish({ data: { code: 200, data: { id: 1 } } })
    assert.equal((await pending).stale, true)
    assert.equal(user.userInfo.id, 2)
  } finally { axios.get = original }
})
