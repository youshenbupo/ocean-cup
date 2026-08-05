// pages/service-flow/service-flow.js
const app = getApp()

Page({
  data: {
    flowSteps: [
      { title: '提出问题', desc: '用文字、语音或图片描述你的问题' },
      { title: '智能识别', desc: '系统自动分析你的问题类型（法律/安全/薪资/技能/生活）' },
      { title: '专业处理', desc: '将问题路由给对应的专业智能体，检索知识库获取准确信息' },
      { title: '结构化回复', desc: '以通俗易懂的语言给出分析、法律依据和行动建议' },
      { title: '持续跟进', desc: '支持多轮追问，记住你的情况，持续提供帮助' }
    ],
    agents: [
      { name: '法律顾问', icon: '⚖️', type: 'legal', desc: '精通劳动法律法规，帮你分析欠薪、工伤、合同等问题', tags: ['欠薪维权', '工伤认定', '合同纠纷', '仲裁诉讼'], welcomeMsg: '我遇到了劳动纠纷问题，需要法律咨询' },
      { name: '安全守护', icon: '🦺', type: 'safety', desc: '关注工地安全生产，提供天气预警和隐患识别', tags: ['安全隐患', '天气提醒', '防护装备', '应急处理'], welcomeMsg: '我想了解工地安全注意事项' },
      { name: '薪资管家', icon: '💰', type: 'salary', desc: '帮你记录工时、核算工资、计算加班费', tags: ['工时记录', '工资核算', '加班费', '薪资提醒'], welcomeMsg: '帮我记录今天的工时' },
      { name: '技能导师', icon: '📚', type: 'skill', desc: '提供职业技能培训信息和考证指导', tags: ['技能培训', '考证', '补贴申请', '职业规划'], welcomeMsg: '我想了解有哪些免费的技能培训' },
      { name: '生活管家', icon: '🏠', type: 'life', desc: '社保医保、子女教育、租房等生活问题咨询', tags: ['社保', '医保', '子女教育', '租房'], welcomeMsg: '我想了解社保怎么交' },
      { name: '工友社区', icon: '💬', type: 'community', desc: '发帖求助、经验分享、互助交流', tags: ['发帖', '求助', '经验分享', '互助'], welcomeMsg: '我想在社区发帖' }
    ]
  },

  tryAgent: function(e) {
    const type = e.currentTarget.dataset.type
    const msg = e.currentTarget.dataset.msg
    
    if (type === 'community') {
      wx.switchTab({ url: '/pages/community/community' })
    } else {
      app.globalData.chatType = type
      app.globalData.chatMessage = msg
      wx.switchTab({ url: '/pages/chat/chat' })
    }
  }
})
