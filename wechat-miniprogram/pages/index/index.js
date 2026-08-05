// pages/index/index.js
const app = getApp()

Page({
  data: {
    userInfo: null,
    hasUserInfo: false
  },

  onLoad: function() {
    if (app.globalData.userInfo) {
      this.setData({
        userInfo: app.globalData.userInfo,
        hasUserInfo: true
      })
    }
  },

  onShow: function() {
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

  // 跳转到知识库
  goToKnowledge: function() {
    wx.navigateTo({
      url: '/pages/knowledge/knowledge'
    })
  },

  // 跳转到服务流程
  goToServiceFlow: function() {
    wx.navigateTo({
      url: '/pages/service-flow/service-flow'
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
        type = 'salary'
        break
      case 'contract':
        message = '没签劳动合同怎么办？'
        type = 'legal'
        break
      case 'contract-review':
        message = '帮我审查一下劳动合同，看看有没有问题'
        type = 'legal'
        break
      case 'injury':
        message = '工伤认定流程是什么？'
        type = 'legal'
        break
      case 'social':
        message = '我想了解社保怎么交'
        type = 'life'
        break
      case 'iou':
        message = '我要写一份欠条'
        type = 'legal'
        break
      case 'wage-slip':
        message = '帮我生成一份工资条'
        type = 'salary'
        break
      case 'cert':
        message = '我要记录我的证书信息'
        type = 'skill'
        break
      case 'expense':
        message = '我要记一笔开支'
        type = 'salary'
        break
    }
    
    app.globalData.chatType = type
    app.globalData.chatMessage = message
    wx.switchTab({
      url: '/pages/chat/chat'
    })
  },

  // 拨打热线
  callHotline: function(e) {
    const phone = e.currentTarget.dataset.phone
    wx.makePhoneCall({
      phoneNumber: phone,
      fail: function() {
        wx.showToast({ title: '取消拨号', icon: 'none' })
      }
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
