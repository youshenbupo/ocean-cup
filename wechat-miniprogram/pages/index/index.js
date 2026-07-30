// pages/index/index.js
const app = getApp()

Page({
  data: {
    userInfo: null,
    hasUserInfo: false
  },

  onLoad: function() {
    // 检查登录状态
    if (app.globalData.userInfo) {
      this.setData({
        userInfo: app.globalData.userInfo,
        hasUserInfo: true
      })
    }
  },

  // 跳转到聊天页面
  goToChat: function(e) {
    const type = e.currentTarget.dataset.type
    wx.navigateTo({
      url: `/pages/chat/chat?type=${type}`
    })
  },

  // 跳转到社区页面
  goToCommunity: function() {
    wx.switchTab({
      url: '/pages/community/community'
    })
  },

  // 快捷功能
  quickAction: function(e) {
    const action = e.currentTarget.dataset.action
    let message = ''
    
    switch(action) {
      case 'weather':
        message = '今天天气怎么样？工地干活要注意什么？'
        break
      case 'record':
        message = '帮我记录今天的工时'
        break
      case 'hotline':
        message = '维权热线是多少？'
        break
    }
    
    wx.navigateTo({
      url: `/pages/chat/chat?message=${encodeURIComponent(message)}`
    })
  },

  // 获取用户信息
  getUserProfile: function() {
    wx.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        this.setData({
          userInfo: res.userInfo,
          hasUserInfo: true
        })
        app.globalData.userInfo = res.userInfo
      }
    })
  }
})
