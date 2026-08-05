// pages/post-detail/post-detail.js
const app = getApp()

Page({
  data: {
    postId: '',
    post: {},
    comments: [],
    commentInput: ''
  },

  onLoad: function(options) {
    const id = options.id
    this.setData({ postId: id })
    this.loadPostDetail(id)
    this.loadComments(id)
  },

  loadPostDetail: function(id) {
    const that = this
    wx.request({
      url: `${app.globalData.apiBaseUrl}/api/community/posts/${id}`,
      method: 'GET',
      success: function(res) {
        if (res.data && res.data.data) {
          that.setData({ post: res.data.data })
        }
      },
      fail: function() {
        // 使用缓存数据
        const cacheKey = `post_${id}`
        const cached = wx.getStorageSync(cacheKey)
        if (cached) {
          that.setData({ post: cached })
        }
      }
    })
  },

  loadComments: function(postId) {
    const that = this
    wx.request({
      url: `${app.globalData.apiBaseUrl}/api/community/posts/${postId}/comments`,
      method: 'GET',
      success: function(res) {
        if (res.data && res.data.data) {
          that.setData({ comments: res.data.data })
        }
      }
    })
  },

  onCommentInput: function(e) {
    this.setData({ commentInput: e.detail.value })
  },

  submitComment: function() {
    const content = this.data.commentInput.trim()
    if (!content) {
      wx.showToast({ title: '请输入评论内容', icon: 'none' })
      return
    }

    const that = this
    wx.request({
      url: `${app.globalData.apiBaseUrl}/api/community/posts/${this.data.postId}/comments`,
      method: 'POST',
      data: {
        content: content,
        author_name: app.globalData.userInfo ? app.globalData.userInfo.nickName : '匿名用户'
      },
      success: function(res) {
        wx.showToast({ title: '评论成功', icon: 'success' })
        that.setData({ commentInput: '' })
        that.loadComments(that.data.postId)
      },
      fail: function() {
        wx.showToast({ title: '评论失败，请重试', icon: 'none' })
      }
    })
  }
})
