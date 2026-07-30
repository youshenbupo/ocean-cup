// pages/community/community.js
const app = getApp()

Page({
  data: {
    currentTab: 'all',
    posts: [],
    isLoading: false,
    noMore: false,
    page: 1,
    pageSize: 10
  },

  onLoad() {
    this.loadPosts()
  },

  onPullDownRefresh() {
    this.setData({ page: 1, noMore: false, posts: [] })
    this.loadPosts().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 切换标签
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      currentTab: tab,
      page: 1,
      noMore: false,
      posts: []
    })
    this.loadPosts()
  },

  // 加载帖子列表
  async loadPosts() {
    if (this.data.isLoading || this.data.noMore) return
    
    this.setData({ isLoading: true })
    
    try {
      // 调用后端API获取帖子列表
      const response = await app.request('/api/community/posts', {
        page: this.data.page,
        pageSize: this.data.pageSize,
        tag: this.data.currentTab === 'all' ? '' : this.data.currentTab
      })
      
      const newPosts = response.data || []
      
      this.setData({
        posts: [...this.data.posts, ...newPosts],
        page: this.data.page + 1,
        noMore: newPosts.length < this.data.pageSize
      })
    } catch (error) {
      console.error('加载帖子失败:', error)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      this.setData({ isLoading: false })
    }
  },

  // 加载更多
  loadMore() {
    if (!this.data.noMore) {
      this.loadPosts()
    }
  },

  // 查看帖子详情
  viewPost(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({
      url: `/pages/post-detail/post-detail?id=${id}`
    })
  },

  // 发帖
  createPost() {
    wx.navigateTo({
      url: '/pages/create-post/create-post'
    })
  }
})
