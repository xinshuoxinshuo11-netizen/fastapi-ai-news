// 使用真实 Pinia 状态，模拟外部 HTTP 边界，验证请求竞争不会污染新闻页面。
import test from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import { useNewsStore } from '../src/store/modules/news.js'

test('重复加载不会将同一页新闻追加两次', async () => {
  setActivePinia(createPinia())
  const store = useNewsStore()
  const original = axios.get
  let finish
  let requests = 0
  axios.get = () => { requests++; return new Promise(resolve => { finish = resolve }) }
  try {
    const first = store.getNewsList()
    const second = store.getNewsList()
    assert.equal(requests, 1)
    finish({ data: { code: 200, data: { list: [{ id: 1 }], hasMore: false } } })
    await Promise.all([first, second])
    assert.deepEqual(store.newsList.map(item => item.id), [1])
    assert.equal(store.finished, true)
  } finally { axios.get = original }
})

test('切换分类后丢弃较晚到达的旧分类结果', async () => {
  setActivePinia(createPinia())
  const store = useNewsStore()
  const original = axios.get
  const callbacks = []
  axios.get = () => new Promise(resolve => callbacks.push(resolve))
  try {
    const first = store.getNewsList()
    store.changeCategory(2)
    assert.equal(callbacks.length, 2)
    callbacks[1]({ data: { code: 200, data: { list: [{ id: 20 }], hasMore: false } } })
    await new Promise(resolve => setImmediate(resolve))
    callbacks[0]({ data: { code: 200, data: { list: [{ id: 1 }], hasMore: true } } })
    await first
    assert.deepEqual(store.newsList.map(item => item.id), [20])
    assert.equal(store.currentCategory, 2)
  } finally { axios.get = original }
})

test('新闻不存在时清除上一条新闻的正文', async () => {
  setActivePinia(createPinia())
  const store = useNewsStore()
  store.newsDetail = { id: 1, title: '上条新闻' }
  const original = axios.get
  axios.get = async () => { throw new Error('新闻不存在') }
  try {
    await store.getNewsDetail(999999)
    assert.equal(store.newsDetail.id, undefined)
  } finally { axios.get = original }
})

test('末页加载完毕后再次进入首页不会重复请求末页', async () => {
  setActivePinia(createPinia())
  const store = useNewsStore()
  const original = axios.get
  let requests = 0
  axios.get = async () => {
    requests++
    return { data: { code: 200, data: { list: [{ id: 1 }, { id: 2 }], hasMore: false } } }
  }
  try {
    await store.getNewsList()
    await store.getNewsList()
    assert.equal(requests, 1)
    assert.deepEqual(store.newsList.map(item => item.id), [1, 2])
    await store.getNewsList(true)
    assert.equal(requests, 2)
    assert.deepEqual(store.newsList.map(item => item.id), [1, 2])
  } finally { axios.get = original }
})
