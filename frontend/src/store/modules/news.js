import { defineStore } from 'pinia'
import axios from 'axios'
import { apiConfig } from '../../config/api.js'

export const useNewsStore = defineStore('news', {
  state: () => ({
    newsList: [], newsDetail: {}, categories: [], currentCategory: 1,
    loading: false, refreshing: false, finished: false, categoriesLoading: false,
    fetching: false, requestId: 0, detailRequestId: 0, detailError: '',
  }),
  actions: {
    async getCategories() {
      if (this.categoriesLoading) return
      this.categoriesLoading = true
      try {
        const response = await axios.get(`${apiConfig.baseURL}/api/news/categories`)
        this.categories = [...response.data.data, { id: 10, name: '更多' }]
      } catch {
        this.categories = []
      } finally { this.categoriesLoading = false }
    },
    changeCategory(categoryId) {
      if (this.currentCategory === categoryId) return
      this.currentCategory = categoryId
      return this.getNewsList(true)
    },
    async getNewsList(isRefresh = false) {
      if (this.finished && !isRefresh) { this.loading = false; return }
      // Vant 会先设置 loading，再触发加载事件，因此用独立 fetching 标记阻止重复请求。
      if (this.fetching && !isRefresh) return
      if (isRefresh) {
        this.refreshing = true
        this.newsList = []
        this.finished = false
      }
      const requestId = ++this.requestId
      const categoryId = this.currentCategory
      this.fetching = true
      this.loading = true
      const params = { categoryId, page: Math.floor(this.newsList.length / 10) + 1, pageSize: 10 }
      try {
        const response = await axios.get(`${apiConfig.baseURL}/api/news/list`, { params })
        // 已切换分类或刷新时，丢弃迟到的旧结果。
        if (requestId !== this.requestId || categoryId !== this.currentCategory) return
        if (response.data.code === 200) {
          this.newsList = [...this.newsList, ...response.data.data.list]
          this.finished = !response.data.data.hasMore
        }
      } catch {
        if (requestId === this.requestId) this.finished = true
      } finally {
        if (requestId === this.requestId) {
          this.fetching = false
          this.loading = false
          this.refreshing = false
        }
      }
    },
    async getNewsDetail(id) {
      const requestId = ++this.detailRequestId
      this.newsDetail = {}
      this.detailError = ''
      try {
        const response = await axios.get(`${apiConfig.baseURL}/api/news/detail`, { params: { id } })
        if (requestId === this.detailRequestId && response.data.code === 200) this.newsDetail = response.data.data
      } catch {
        if (requestId === this.detailRequestId) this.detailError = '新闻不存在或加载失败，请稍后重试'
      }
    },
    getCategoryName(categoryId) {
      return this.categories.find(item => item.id === categoryId)?.name || '未知'
    },
  },
})
