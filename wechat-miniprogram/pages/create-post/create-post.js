// pages/create-post/create-post.js
const app = getApp()

Page({
  data: {
    categories: ['薪资相关', '安全问题', '技能交流', '生活互助', '综合'],
    categoryIndex: 0,
    title: '',
    content: '',
    authorName: '',
    submitting: false
  },

  onLoad: function() {
    // 预填用户信息
    if (app.globalData.userInfo) {
      this.setData({ authorName: app.globalData.userInfo.nickName })
    }
  },

  onCategoryChange: function(e) {
    this.setData({ categoryIndex: e.detail.value })
  },

  onTitleInput: function(e) {
    this.setData({ title: e.detail.value })
  },

  onContentInput: function(e) {
    this.setData({ content: e.detail.value })
  },

  onAuthorInput: function(e) {
    this.setData({ authorName: e.detail.value })
  },

  submitPost: function() {
    const { title, content, authorName, categories, categoryIndex } = this.data
    
    if (!title.trim()) {
      wx.showToast({ title: '请输入标题', icon: 'none' })
      return
    }
    if (!content.trim()) {
      wx.showToast({ title: '请输入内容', icon: 'none' })
      return
    }
    if (!authorName.trim()) {
      wx.showToast({ title: '请输入你的称呼', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    const that = this

    wx.request({
      url: `${app.globalData.apiBaseUrl}/api/community/posts`,
      method: 'POST',
      data: {
        title: title.trim(),
        content: content.trim(),
        author_name: authorName.trim(),
        category: categories[categoryIndex]
      },
      success: function(res) {
        wx.showToast({ title: '发布成功', icon: 'success' })
        setTimeout(() => {
          wx.navigateBack()
        }, 1500)
      },
      fail: function() {
        wx.showToast({ title: '发布失败，请重试', icon: 'none' })
      },
      complete: function() {
        that.setData({ submitting: false })
      }
    })
  }
})
