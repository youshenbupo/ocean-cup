// pages/post-detail/post-detail.js
const app = getApp()

Page({
  data: {
    postId: '',
    post: null,
    comments: [],
    commentText: '',
    commenterName: '',
    isLoading: true,
    submittingComment: false
  },

  onLoad: function(options) {
    if (options.id) {
      this.setData({ postId: options.id })
      this.loadPostDetail(options.id)
    }
  },

  // 加载帖子详情
  loadPostDetail: function(postId) {
    const that = this
    this.setData({ isLoading: true })
    
    app.request('/api/community/posts/' + postId).then(function(res) {
      that.setData({
        post: res.data,
        comments: res.data.comments || [],
        isLoading: false
      })
    }).catch(function(err) {
      console.error('加载帖子详情失败:', err)
      that.setData({ isLoading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    })
  },

  // 输入评论
  onCommentInput: function(e) {
    this.setData({ commentText: e.detail.value })
  },

  // 输入评论者姓名
  onCommenterInput: function(e) {
    this.setData({ commenterName: e.detail.value })
  },

  // 提交评论
  submitComment: function() {
    const { commentText, commenterName, postId } = this.data
    
    if (!commentText.trim()) {
      wx.showToast({ title: '请输入评论内容', icon: 'none' })
      return
    }
    if (!commenterName.trim()) {
      wx.showToast({ title: '请输入你的称呼', icon: 'none' })
      return
    }

    this.setData({ submittingComment: true })
    const that = this

    app.request('/api/community/posts/' + postId + '/comments', {
      content: commentText.trim(),
      commenter_name: commenterName.trim()
    }, 'POST').then(function(res) {
      wx.showToast({ title: '评论成功', icon: 'success' })
      that.setData({ commentText: '' })
      that.loadPostDetail(postId)
    }).catch(function() {
      wx.showToast({ title: '评论失败', icon: 'none' })
    }).finally(function() {
      that.setData({ submittingComment: false })
    })
  },

  // 分享帖子
  onShareAppMessage: function() {
    return {
      title: this.data.post ? this.data.post.title : '工友社区',
      path: '/pages/post-detail/post-detail?id=' + this.data.postId
    }
  }
})
