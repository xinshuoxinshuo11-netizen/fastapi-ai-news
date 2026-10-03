// 用内存存储验证服务端历史 ID 与游客新闻 ID 两条删除路径。
import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
const saved = new Map()
globalThis.localStorage = {
  getItem: key => saved.get(key) ?? null,
  setItem: (key, value) => saved.set(key, value),
  removeItem: key => saved.delete(key),
}
const { useHistoryStore } = await import('../src/store/modules/history.js')

test('服务端删除按历史 ID，不误删同 ID 的新闻', () => {
  setActivePinia(createPinia())
  const store = useHistoryStore()
  store.history = [{ id: 17, historyId: 3 }, { id: 3, historyId: 8 }]
  store.removeHistory(3, true)
  assert.deepEqual(store.history.map(item => item.id), [3])
  assert.deepEqual(JSON.parse(saved.get('news_history')), [{ id: 3, historyId: 8 }])
})

test('游客本地删除继续按新闻 ID', async () => {
  setActivePinia(createPinia())
  const store = useHistoryStore()
  store.history = [{ id: 17 }, { id: 3 }]
  const result = await store.removeHistoryApi(17)
  assert.equal(result.isLocal, true)
  assert.deepEqual(store.history.map(item => item.id), [3])
})
