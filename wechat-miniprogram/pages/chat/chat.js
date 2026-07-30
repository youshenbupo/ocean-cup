// pages/chat/chat.js
const app = getApp()

Page({
  data: {
    messages: [],
    inputValue: '',
    isLoading: false,
    scrollToView: '',
    agentType: 'general'  // general, legal, safety, salary, skill, life
  },

  onLoad: function(options) {
    const type = options.type || 'general'
    const message = options.message ? decodeURIComponent(options.message) : ''
    
    this.setData({ agentType: type })
    
    // 初始化欢迎消息
    const welcomeMsg = this.getWelcomeMessage(type)
    this.setData({
      messages: [{ role: 'assistant', content: welcomeMsg }]
    })
    
    // 如果有预设消息，自动发送
    if (message) {
      this.setData({ inputValue: message })
      setTimeout(() => this.sendMessage(), 500)
    }
  },

  getWelcomeMessage: function(type) {
    const messages = {
      general: '你好，我是「明白人」，专门帮咱建筑工友搞清楚自己该得啥、怎么要。\n\n工资被拖欠了？干活受伤了？没签合同？被辞退了不知道该不该给钱？\n\n别急，把你的情况跟我说说，我帮你理一理。',
      legal: '我是你的法律顾问，专门帮你解决工资、合同、工伤等权益问题。说说你遇到了什么情况？',
      safety: '我是安全卫士，帮你识别工地安全隐患。你可以描述一下工地情况，或者拍照发给我看看。',
      salary: '我是薪资管家，帮你记录工时、核算工资、生成欠条。需要我帮你做什么？',
      skill: '我是技能导师，帮你规划技能提升路径、考证指导。你想学什么技能？',
      life: '我是生活管家，帮你解决社保、子女教育、租房等生活问题。有什么需要帮忙的？'
    }
    return messages[type] || messages.general
  },

  onInput: function(e) {
    this.setData({ inputValue: e.detail.value })
  },

  sendMessage: function() {
    const content = this.data.inputValue.trim()
    if (!content) return
    
    // 添加用户消息
    const messages = [...this.data.messages, { role: 'user', content }]
    this.setData({ 
      messages, 
      inputValue: '',
      isLoading: true 
    })
    this.scrollToBottom()
    
    // 调用后端API
    this.callAgent(content)
  },

  callAgent: function(userMessage) {
    // 实际项目中，这里应该调用后端API
    // 后端API再调用扣子平台的Agent
    wx.request({
      url: app.globalData.apiBaseUrl + '/chat',
      method: 'POST',
      data: {
        message: userMessage,
        agent_type: this.data.agentType,
        session_id: app.globalData.sessionId
      },
      success: (res) => {
        const reply = res.data.reply || '抱歉，我暂时无法回答这个问题。'
        const messages = [...this.data.messages, { role: 'assistant', content: reply }]
        this.setData({ messages, isLoading: false })
        this.scrollToBottom()
      },
      fail: (err) => {
        console.error('API调用失败:', err)
        const messages = [...this.data.messages, { 
          role: 'assistant', 
          content: '网络好像有点问题，请稍后再试。' 
        }]
        this.setData({ messages, isLoading: false })
        this.scrollToBottom()
      }
    })
  },

  askQuick: function(e) {
    const question = e.currentTarget.dataset.q
    this.setData({ inputValue: question })
    this.sendMessage()
  },

  scrollToBottom: function() {
    const index = this.data.messages.length - 1
    this.setData({ scrollToView: `msg-${index}` })
  }
})
