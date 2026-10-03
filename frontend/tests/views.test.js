// 执行实际组件的 setup 逻辑，模拟路由和延迟请求，不连接真实 API。
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { ref, reactive, computed, watch, nextTick } from 'vue'

function setupView(name, context) {
  const source = fs.readFileSync(new URL(`../src/views/${name}.vue`, import.meta.url), 'utf8')
    .match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/gm, '')
  return new Function(...Object.keys(context), source + '\nreturn typeof activeTab === "undefined" ? undefined : activeTab;')(...Object.values(context))
}

function detailFixture() {
  const route = reactive({ params: { id: '1' } })
  const user = { getLoginStatus: true, token: '测试令牌' }
  const news = { newsDetail: {}, detailRequestId: 0, async getNewsDetail(id) {
    this.detailRequestId++; this.newsDetail = { id, title: '测试新闻' }
  } }
  const favorites = [], requests = []
  let callback
  setupView('NewsDetail', {
    computed, watch: (_source, fn) => { callback = fn },
    useRoute: () => route, useRouter: () => ({}), useNewsStore: () => news,
    useUserStore: () => user, useHistoryStore: () => ({ addHistoryApi: async () => ({ success: true }) }),
    useFavoriteStore: () => ({
      loadFavorites() {}, isFavorite: id => favorites.some(item => item.id === id),
      addFavorite: item => favorites.push(item), removeFavorite: id => {
        const index = favorites.findIndex(item => item.id === id)
        if (index !== -1) favorites.splice(index, 1)
      },
      checkFavoriteStatusApi: id => new Promise(resolve => requests.push({ id, resolve })),
    }), showToast() {},
  })
  return { route, user, favorites, requests, callback }
}

const settle = () => new Promise(resolve => setImmediate(resolve))

test('旧新闻收藏响应不会改变新新闻的星标', async () => {
  const fixture = detailFixture()
  const first = fixture.callback(1); await settle()
  fixture.route.params.id = '2'
  const second = fixture.callback(2); await settle()
  fixture.requests[1].resolve({ success: true, isFavorite: false }); await second
  fixture.requests[0].resolve({ success: true, isFavorite: true }); await first
  assert.deepEqual(fixture.favorites, [])
})

test('详情查询期间切换账号会丢弃收藏响应', async () => {
  const fixture = detailFixture()
  const pending = fixture.callback(1); await settle()
  fixture.user.token = '新账号的测试令牌'
  fixture.requests[0].resolve({ success: true, isFavorite: true }); await pending
  assert.deepEqual(fixture.favorites, [])
})

test('切换分类会同步 URL，详情返回后保留新分类', async () => {
  const route = reactive({ path: '/home', query: { categoryId: '2' } })
  const news = reactive({ categories: [{ id: 1, name: '头条' }, { id: 2, name: '社会' }, { id: 3, name: '国内' }],
    currentCategory: 2, changeCategory(id) { this.currentCategory = id } })
  function mount() {
    const stops = []
    const active = setupView('Home', {
      ref, computed, watch: (...args) => { const stop = watch(...args); stops.push(stop); return stop },
      onMounted() {}, onBeforeUnmount() {}, useNewsStore: () => news,
      useRoute: () => route, useRouter: () => ({ replace: value => { route.query = value.query } }),
      useI18n: () => ({ t: key => key }),
    })
    return { active, stop: () => stops.forEach(stop => stop()) }
  }
  const first = mount()
  first.active.value = 2
  await nextTick()
  assert.equal(route.query.categoryId, '3')
  first.stop()
  const returned = mount()
  await nextTick()
  assert.equal(news.currentCategory, 3)
  assert.equal(returned.active.value, 2)
  returned.stop()
})
