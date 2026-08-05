// pages/chat/chat.js
const app = getApp()

Page({
  data: {
    messages: [],
    inputValue: '',
    isLoading: false,
    scrollToView: '',
    agentType: 'general',  // general, legal, safety, salary, skill, life
    selectedImage: '',  // 选中的图片临时路径
    isRecording: false,  // 是否正在录音
    recorderManager: null,  // 录音管理器
    lastProcessedType: '',  // 上次处理的类型，避免重复触发
    showToolPanel: false  // 工具面板是否显示
  },

  onLoad: function(options) {
    // 初始化录音管理器
    this.recorderManager = wx.getRecorderManager()
    this.recorderManager.onStop((res) => {
      this.onRecordStop(res)
    })
    this.recorderManager.onError((err) => {
      console.error('录音错误:', err)
      this.setData({ isRecording: false })
      wx.showToast({ title: '录音失败，请重试', icon: 'none' })
    })
    
    // 从 globalData 或 URL 参数读取（兼容两种方式）
    this.processNavigationParams(options)
  },

  onShow: function() {
    // switchTab 不会触发 onLoad，但会触发 onShow
    // 检查是否有新的导航参数
    this.processNavigationParams()
  },

  // 处理导航参数（支持 globalData 和 URL 两种方式）
  processNavigationParams: function(options) {
    const type = (app.globalData.chatType) || (options && options.type) || 'general'
    const message = app.globalData.chatMessage || 
                    (options && options.message ? decodeURIComponent(options.message)) : ''
    
    // 避免重复处理相同的导航参数
    const paramKey = `${type}_${message}`
    if (this.data.lastProcessedType === paramKey && this.data.messages.length > 1) {
      return
    }
    
    // 如果类型变了，重置对话
    if (type !== this.data.agentType || this.data.messages.length === 0) {
      this.setData({ agentType: type })
      
      // 初始化欢迎消息
      const welcomeMsg = this.getWelcomeMessage(type)
      this.setData({
        messages: [{ role: 'assistant', content: welcomeMsg }],
        lastProcessedType: paramKey
      })
      
      // 如果有预设消息，自动发送
      if (message) {
        this.setData({ inputValue: message })
        setTimeout(() => this.sendMessage(), 500)
      }
    }
    
    // 清除 globalData 中的参数，避免下次 onShow 重复处理
    app.globalData.chatType = ''
    app.globalData.chatMessage = ''
  },

  getWelcomeMessage: function(type) {
    const messages = {
      general: '你好，我是「明白人」，专门帮咱建筑工友搞清楚自己该得啥、怎么要。\n\n工资被拖欠了？干活受伤了？没签合同？被辞退了不知道该不该给钱？\n\n别急，把你的情况跟我说说，我帮你理一理。\n\n💡 你可以点击左下角 📷 拍照或选择图片发给我，比如工伤照片、安全隐患照片等。',
      legal: '我是你的法律顾问，专门帮你解决工资、合同、工伤等权益问题。说说你遇到了什么情况？\n\n💡 如果有合同、工资条等证据照片，可以点击 📷 发给我。',
      safety: '我是安全卫士，帮你识别工地安全隐患。\n\n📷 强烈建议你拍照发给我，我可以识别照片中的安全隐患，比如：\n- 未戴安全帽、未系安全带\n- 脚手架搭设不规范\n- 临边洞口无防护\n- 用电不规范等',
      salary: '我是薪资管家，帮你记录工时、核算工资、生成欠条。需要我帮你做什么？',
      skill: '我是技能导师，帮你规划技能提升路径、考证指导。你想学什么技能？',
      life: '我是生活管家，帮你解决社保、子女教育、租房等生活问题。有什么需要帮忙的？'
    }
    return messages[type] || messages.general
  },

  onInput: function(e) {
    this.setData({ inputValue: e.detail.value })
  },

  // 选择图片
  chooseImage: function() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      sizeType: ['compressed'],
      success: (res) => {
        const tempFilePath = res.tempFiles[0].tempFilePath
        this.setData({ selectedImage: tempFilePath })
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        wx.showToast({ title: '选择图片失败', icon: 'none' })
      }
    })
  },

  // 移除已选图片
  removeImage: function() {
    this.setData({ selectedImage: '' })
  },

  // 预览图片
  previewImage: function(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      urls: [src],
      current: src
    })
  },

  sendMessage: function() {
    const content = this.data.inputValue.trim()
    const image = this.data.selectedImage
    
    if (!content && !image) return
    
    // 添加用户消息（包含图片）
    const userMsg = { role: 'user', content: content || '[图片]' }
    if (image) {
      userMsg.image = image
    }
    const messages = [...this.data.messages, userMsg]
    this.setData({ 
      messages, 
      inputValue: '',
      selectedImage: '',
      isLoading: true 
    })
    this.scrollToBottom()
    
    // 调用后端API（如果有图片，先上传图片）
    if (image) {
      this.uploadImageAndCallAgent(image, content)
    } else {
      this.callAgent(content, null)
    }
  },

  // 上传图片并调用Agent
  uploadImageAndCallAgent: function(imagePath, text) {
    wx.showLoading({ title: '上传图片中...' })
    
    wx.uploadFile({
      url: app.globalData.apiBaseUrl + '/upload',
      filePath: imagePath,
      name: 'file',
      formData: {
        session_id: app.globalData.sessionId,
        agent_type: this.data.agentType
      },
      success: (uploadRes) => {
        wx.hideLoading()
        try {
          const data = JSON.parse(uploadRes.data)
          const imageUrl = data.url || data.file_url
          this.callAgent(text, imageUrl)
        } catch (e) {
          console.error('解析上传结果失败:', e)
          this.callAgent(text, null)
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('图片上传失败:', err)
        // 上传失败仍然发送文字消息
        this.callAgent(text, null)
        wx.showToast({ title: '图片上传失败，仅发送文字', icon: 'none' })
      }
    })
  },

  callAgent: function(userMessage, imageUrl) {
    const requestData = {
      message: userMessage,
      agent_type: this.data.agentType,
      session_id: app.globalData.sessionId
    }
    if (imageUrl) {
      requestData.image_url = imageUrl
    }

    wx.request({
      url: app.globalData.apiBaseUrl + '/chat',
      method: 'POST',
      data: requestData,
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
  },

  // 新建对话
  newConversation: function() {
    wx.showModal({
      title: '新建对话',
      content: '确定要开始新对话吗？当前对话记录将不再保留。',
      confirmText: '确定',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 生成新的session
          const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
          app.globalData.sessionId = newSessionId
          
          // 重置消息列表
          const welcomeMsg = this.getWelcomeMessage(this.data.agentType)
          this.setData({
            messages: [{ role: 'assistant', content: welcomeMsg }],
            inputValue: '',
            selectedImage: '',
            isLoading: false,
            isRecording: false
          })
          
          wx.showToast({ title: '已开始新对话', icon: 'success' })
        }
      }
    })
  },

  // 切换语音输入
  toggleVoiceInput: function() {
    if (this.data.isRecording) {
      // 停止录音
      this.recorderManager.stop()
      this.setData({ isRecording: false })
    } else {
      // 开始录音
      wx.authorize({
        scope: 'scope.record',
        success: () => {
          this.recorderManager.start({
            duration: 60000,  // 最长60秒
            sampleRate: 16000,
            numberOfChannels: 1,
            encodeBitRate: 48000,
            format: 'mp3'
          })
          this.setData({ isRecording: true })
          wx.showToast({ title: '正在录音，再点一次停止', icon: 'none', duration: 2000 })
        },
        fail: () => {
          wx.showModal({
            title: '需要录音权限',
            content: '请在设置中允许使用麦克风，才能使用语音输入功能。',
            confirmText: '去设置',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting()
              }
            }
          })
        }
      })
    }
  },

  // 录音结束回调
  onRecordStop: function(res) {
    const tempFilePath = res.tempFilePath
    wx.showLoading({ title: '识别中...' })
    
    // 上传录音文件到后端进行语音识别
    wx.uploadFile({
      url: app.globalData.apiBaseUrl + '/voice/recognize',
      filePath: tempFilePath,
      name: 'file',
      success: (uploadRes) => {
        wx.hideLoading()
        try {
          const data = JSON.parse(uploadRes.data)
          const recognizedText = data.text || ''
          if (recognizedText) {
            this.setData({ inputValue: recognizedText })
            wx.showToast({ title: '识别完成', icon: 'success' })
          } else {
            wx.showToast({ title: '未识别到内容，请重试', icon: 'none' })
          }
        } catch (e) {
          wx.showToast({ title: '识别失败，请手动输入', icon: 'none' })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('语音上传失败:', err)
        wx.showToast({ title: '网络问题，请手动输入', icon: 'none' })
      }
    })
  },

  // 切换工具面板显示
  toggleToolPanel: function() {
    this.setData({
      showToolPanel: !this.data.showToolPanel
    })
  },

  // 使用工具
  useTool: function(e) {
    const tool = e.currentTarget.dataset.tool
    this.setData({ showToolPanel: false })
    
    // 根据工具类型发送对应的指令消息
    const toolMessages = {
      'iou': '我要写一份欠条',
      'wage-slip': '我要生成工资条',
      'contract': '帮我审查一下劳动合同',
      'arbitration': '我要申请劳动仲裁，帮我写申请书',
      'cert': '我要记录我的证书信息',
      'expense': '我要记一笔开支'
    }
    
    const message = toolMessages[tool] || ''
    if (message) {
      this.setData({ inputValue: message })
      this.sendMessage()
    }
  }
})
