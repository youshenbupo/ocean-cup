// app.js
App({
  globalData: {
    // 后端API地址，部署后替换为实际域名
    apiBaseUrl: 'https://your-api-domain.com',
    sessionId: '',
    userInfo: null
  },

  onLaunch: function() {
    // 生成会话ID
    this.globalData.sessionId = this.generateSessionId()
    
    // 检查登录态
    this.checkLogin()
  },

  generateSessionId: function() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  },

  checkLogin: function() {
    const that = this
    wx.login({
      success: function(res) {
        if (res.code) {
          // 可将code发送到后端换取openId和session_key
          console.log('登录code:', res.code)
        }
      }
    })
  },

  // 获取用户信息
  getUserInfo: function(callback) {
    const that = this
    if (this.globalData.userInfo) {
      callback && callback(this.globalData.userInfo)
      return
    }
    wx.getUserInfo({
      success: function(res) {
        that.globalData.userInfo = res.userInfo
        callback && callback(res.userInfo)
      }
    })
  },

  // 统一请求方法
  request: function(url, data = {}, method = 'GET') {
    return new Promise((resolve, reject) => {
      wx.request({
        url: this.globalData.apiBaseUrl + url,
        method: method,
        data: {
          ...data,
          session_id: this.globalData.sessionId
        },
        header: {
          'content-type': 'application/json'
        },
        success: function(res) {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject(new Error(`请求失败: ${res.statusCode}`))
          }
        },
        fail: function(err) {
          reject(err)
        }
      })
    })
  }
})
