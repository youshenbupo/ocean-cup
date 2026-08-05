// pages/knowledge/knowledge.js
const app = getApp()

Page({
  data: {
    searchKey: '',
    currentCategory: '',
    filteredDocs: [],
    allDocs: [
      // 法律法规
      { id: 1, category: 'law', categoryName: '法律法规', title: '《保障农民工工资支付条例》核心条款', summary: '农民工有按时足额获得工资的权利，任何单位和个人不得拖欠。施工总承包单位对分包单位欠薪负有先行清偿责任。', date: '2020-05-01' },
      { id: 2, category: 'law', categoryName: '法律法规', title: '《劳动合同法》要点解读', summary: '用人单位自用工之日起即与劳动者建立劳动关系。建立劳动关系应当订立书面劳动合同，否则需支付双倍工资。', date: '2008-01-01' },
      { id: 3, category: 'law', categoryName: '法律法规', title: '《安全生产法》工友必读', summary: '从业人员有权了解作业场所的危险因素和防范措施，有权拒绝违章指挥和强令冒险作业。', date: '2021-09-01' },
      { id: 4, category: 'law', categoryName: '法律法规', title: '《工伤保险条例》要点', summary: '职工在工作时间和工作场所内因工作原因受到事故伤害的，应当认定为工伤。用人单位未参保的，由用人单位支付工伤保险待遇。', date: '2011-01-01' },
      // 典型案例
      { id: 5, category: 'case', categoryName: '典型案例', title: '欠薪维权成功案例：3个月工资全追回', summary: '张工友在某建筑工地被拖欠3个月工资，通过劳动监察投诉+仲裁，最终成功追回全部欠薪并获得赔偿金。', date: '2024-03-15' },
      { id: 6, category: 'case', categoryName: '典型案例', title: '没签合同也能认定工伤', summary: '李工友未签劳动合同但在工地受伤，通过工资流水、工友证言等证据证明劳动关系，成功认定工伤并获得赔偿。', date: '2024-01-20' },
      { id: 7, category: 'case', categoryName: '典型案例', title: '加班费追讨案例', summary: '王工友长期加班但未获加班费，收集考勤记录和工资条后申请仲裁，成功追回2年加班费差额。', date: '2023-11-08' },
      // 安全生产
      { id: 8, category: 'safety', categoryName: '安全生产', title: '建筑工地安全操作十不准', summary: '不戴安全帽不准进工地、不系安全带不准高处作业、不懂操作规范不准使用机械设备...', date: '2024-06-01' },
      { id: 9, category: 'safety', categoryName: '安全生产', title: '高温天气作业防护指南', summary: '日最高气温达到37℃以上，用人单位应当采取换班轮休等方式缩短连续作业时间，不得安排室外露天作业劳动者加班。', date: '2024-05-15' },
      { id: 10, category: 'safety', categoryName: '安全生产', title: '常见安全隐患识别手册', summary: '脚手架搭设不规范、临边洞口无防护、用电线路私拉乱接、起重机械超负荷运行等常见隐患及正确做法。', date: '2024-04-20' },
      // 技能提升
      { id: 11, category: 'skill', categoryName: '技能提升', title: '建筑工人职业技能等级认定指南', summary: '建筑工人可参加职业技能培训，通过考核获得职业资格证书。电工、焊工、架子工等工种有明确的等级认定标准。', date: '2024-02-10' },
      { id: 12, category: 'skill', categoryName: '技能提升', title: '免费技能培训报名渠道', summary: '各地人社部门定期组织免费技能培训，包括电工、焊工、砌筑工等工种。培训期间还有生活补贴。', date: '2024-03-01' },
      // 社保医保
      { id: 13, category: 'social', categoryName: '社保医保', title: '农民工社保参保指南', summary: '用人单位应当为农民工缴纳工伤保险。鼓励农民工参加养老保险和医疗保险，可在户籍地或工作地参保。', date: '2024-01-15' },
      { id: 14, category: 'social', categoryName: '社保医保', title: '异地就医备案流程', summary: '农民工在外地工作生病需要就医的，可通过国家医保服务平台APP办理异地就医备案，实现直接结算。', date: '2024-04-01' }
    ]
  },

  onLoad: function() {
    this.setData({ filteredDocs: this.data.allDocs })
  },

  onSearch: function(e) {
    this.setData({ searchKey: e.detail.value })
  },

  doSearch: function() {
    this.filterDocs()
  },

  switchCategory: function(e) {
    const cat = e.currentTarget.dataset.cat
    this.setData({ currentCategory: cat })
    this.filterDocs()
  },

  filterDocs: function() {
    const { searchKey, currentCategory, allDocs } = this.data
    let filtered = allDocs
    
    if (currentCategory) {
      filtered = filtered.filter(d => d.category === currentCategory)
    }
    
    if (searchKey.trim()) {
      const key = searchKey.toLowerCase()
      filtered = filtered.filter(d => 
        d.title.toLowerCase().includes(key) || 
        d.summary.toLowerCase().includes(key)
      )
    }
    
    this.setData({ filteredDocs: filtered })
  },

  openDoc: function(e) {
    const id = e.currentTarget.dataset.id
    const doc = this.data.allDocs.find(d => d.id === id)
    if (doc) {
      wx.showModal({
        title: doc.title,
        content: doc.summary,
        showCancel: false,
        confirmText: '知道了'
      })
    }
  },

  callHotline: function(e) {
    const phone = e.currentTarget.dataset.phone
    wx.makePhoneCall({
      phoneNumber: phone,
      fail: function() {
        wx.showToast({ title: '取消拨号', icon: 'none' })
      }
    })
  }
})
