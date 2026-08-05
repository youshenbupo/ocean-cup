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

  onShow: function() {
    // 每次显示首页时刷新用户信息
    if (app.globalData.userInfo) {
      this.setData({
        userInfo: app.globalData.userInfo,
        hasUserInfo: true
      })
    }
  },

  // 跳转到聊天页面（通过globalData传递参数）
  goToChat: function(e) {
    const type = e.currentTarget.dataset.type
    // 通过globalData传递类型参数，因为switchTab不支持URL参数
    app.globalData.chatType = type
    app.globalData.chatMessage = ''
    wx.switchTab({
      url: '/pages/chat/chat'
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
    let type = ''
    
    switch(action) {
      case 'weather':
        message = '今天天气怎么样？工地干活要注意什么？'
        type = 'safety'
        break
      case 'record':
        message = '帮我记录今天的工时'
        type = 'salary'
        break
      case 'hotline':
        message = '维权热线是多少？'
        type = 'legal'
        break
      case 'overtime':
        message = '加班费怎么算？'
        type = 'legal'
        break
      case 'contract':
        message = '没签劳动合同怎么办？'
        type = 'legal'
        break
      case 'injury':
        message = '工伤认定流程是什么？'
        type = 'legal'
        break
    }
    
    // 通过globalData传递参数
    app.globalData.chatType = type
    app.globalData.chatMessage = message
    wx.switchTab({
      url: '/pages/chat/chat'
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
