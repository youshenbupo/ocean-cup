# 前端开发任务说明

## 任务目标

为"工友权益明白人"建筑工友权益保障智能体开发一个**建筑行业风格的展示网站**，并将扣子平台的WebSDK聊天功能嵌入到网站中。

## 项目背景

"工友权益明白人"是专门为建筑工友（尤其是农民工）服务的权益保障法律顾问智能体，参赛第一届"海之子"杯AI智能体挑战计划。

核心主题：**为人民建好房 · 为工友谋幸福**

## WebSDK接入说明

### 1. WebSDK信息

- **项目ID**: `7668109916292284459`
- **CDN地址**: `https://lf-cdn.coze.cn/obj/unpkg/latest/coze/web-sdk/dist/js-umd/index.min.js`
- **Bot链接**: `https://code.coze.cn/web-sdk/7668109916292284459`

### 2. 初始化代码

```html
<!-- 引入 Coze Web SDK 官方 CDN -->
<script src="https://lf-cdn.coze.cn/obj/unpkg/latest/coze/web-sdk/dist/js-umd/index.min.js"></script>
<script>
    // 初始化 Web SDK
    cozeWebSDK.init({
        projectId: '7668109916292284459',
        // 支持同步和异步刷新 token
        refreshToken: () => Promise.resolve('<YOUR_TOKEN>'),
    });
</script>
```

### 3. 发送消息

```javascript
// 发送消息到扣子Bot
cozeWebSDK.chat.sendMessage({
    message: message,
    stream: false
}).then(response => {
    // response.content 包含Bot回复
    addMessage(response.content, 'bot');
}).catch(error => {
    addMessage('抱歉，服务暂时不可用，请稍后再试。', 'bot');
});
```

### 4. Token获取

在扣子编程平台：
1. 点击「查看接入方式」
2. 选择「Web SDK」标签
3. 复制代码中的token（类似 `pt-xxx` 的字符串）
4. 替换代码中的 `<YOUR_TOKEN>`

---

## 当前前端代码说明

### 文件位置
`frontend/index.html`

### 已实现的功能

#### 1. 页面结构
- **导航栏**: 固定顶部，包含Logo和导航链接
- **Hero区域**: 项目名称、副标题、口号、CTA按钮
- **统计区域**: 32文档、7Agent、14工具、24h服务
- **功能卡片**: 7个核心功能展示（可点击）
- **服务流程**: 4步解决问题流程图
- **聊天区域**: 完整的聊天界面（已集成WebSDK）
- **知识库展示**: 8个分类卡片
- **页脚**: 版权信息、赛事名称

#### 2. 设计风格
- **配色方案**: 建筑行业风格
  - 主色：橙色 `#FF6B35`（安全帽）
  - 辅色：黄色 `#FFB800`（警示）
  - 深色：深蓝 `#1A1A2E`（工装）
  - 背景：浅灰 `#F8F9FA`
- **视觉元素**: 渐变背景、卡片阴影、平滑动画
- **响应式**: 支持手机、平板、电脑

#### 3. 交互功能
- **快捷提问**: 6个预设问题，点击自动发送
- **平滑滚动**: 导航链接点击平滑滚动到对应区域
- **功能卡片**: 点击跳转到聊天区域并自动提问
- **聊天界面**: 输入框+发送按钮，支持回车键发送

#### 4. WebSDK集成状态
- ✅ 已引入CDN
- ✅ 已初始化（projectId已配置）
- ⚠️ Token需要替换（当前是 `<YOUR_TOKEN>` 占位符）
- ✅ sendMessage函数已实现
- ✅ askQuestion函数已实现

---

## 需要完成的任务

### 任务1：完善WebSDK集成

**目标**: 让聊天功能真正工作

**步骤**:
1. 获取扣子平台的WebSDK token
2. 替换 `index.html` 中的 `<YOUR_TOKEN>`
3. 测试聊天功能是否正常

**代码位置**:
```javascript
// 第XXX行
refreshToken: () => Promise.resolve('<YOUR_TOKEN>'),
```

### 任务2：优化聊天界面（可选）

**目标**: 让聊天界面更美观、更易用

**建议**:
1. 添加加载动画（Bot回复时显示"正在思考..."）
2. 支持Markdown格式渲染（Bot回复可能包含格式）
3. 添加消息时间戳
4. 支持图片上传（多模态功能）
5. 优化移动端体验

### 任务3：添加更多页面（可选）

**目标**: 丰富网站内容

**建议页面**:
1. **工友社区页面**: 展示帖子列表、发帖功能
2. **安全知识页面**: 展示安全规范、隐患案例
3. **法律法规页面**: 展示法律条文、解读
4. **关于我们页面**: 项目介绍、团队信息

---

## 七大核心功能说明

在开发时，需要了解这7个功能，以便在界面中展示：

| 功能 | 图标 | 说明 | 触发词 |
|------|------|------|--------|
| 法律顾问 | ⚖️ | 权益问答、维权指引、证据清单 | 欠薪、工伤、合同、辞退 |
| 安全守护 | 🦺 | 安全隐患识别、安全报告 | 安全、隐患、防护 |
| 心理陪伴 | 💬 | 情绪疏导、危机干预 | 烦、累、想家 |
| 薪资管家 | 💰 | 工时记录、工资核算、欠条 | 工时、加班、算工资 |
| 技能导师 | 🎓 | 技能提升、考证指导 | 技能、考证、培训 |
| 生活管家 | 🏠 | 社保医保、子女教育 | 社保、医保、报销 |
| 工友社区 | 👥 | 互助问答、经验分享 | 发帖、分享、求助 |

---

## 测试用例

开发完成后，用以下问题测试：

1. "老板拖欠工资怎么办？" → 应触发法律顾问，返回维权指引
2. "工地上受伤了怎么取证？" → 应触发法律顾问，返回证据清单
3. "工地有安全隐患怎么办？" → 应触发安全守护
4. "心里烦，想找人聊聊" → 应触发心理陪伴
5. "帮我记工时算工资" → 应触发薪资管家

---

## 部署说明

### 部署到Vercel（推荐）

```bash
# 1. 安装Vercel CLI
npm install -g vercel

# 2. 在项目根目录运行
vercel

# 3. 按提示操作
# - Set up and deploy? → Yes
# - Which scope? → 选择你的账号
# - Link to existing project? → No
# - Project name → gongyou-bot
# - Directory → ./frontend
```

### 部署到Netlify

```bash
# 1. 安装Netlify CLI
npm install -g netlify-cli

# 2. 在项目根目录运行
netlify deploy --prod --dir=frontend
```

### 部署到GitHub Pages

1. 创建GitHub仓库
2. 将 `frontend/index.html` 推送到仓库
3. Settings → Pages → Source选择 `main` 分支
4. 等待1-2分钟，获得链接

---

## 注意事项

1. **Token安全**: 不要将token提交到公开仓库，使用环境变量
2. **跨域问题**: WebSDK已处理跨域，无需额外配置
3. **移动端适配**: 确保在手机上也能正常使用
4. **加载速度**: 优化图片、CSS，确保快速加载
5. **SEO优化**: 添加meta标签、描述，便于搜索引擎收录

---

## 参考资源

- **扣子WebSDK文档**: https://www.coze.cn/docs/developer_guides/web_sdk
- **项目WebSDK链接**: https://code.coze.cn/web-sdk/7668109916292284459
- **当前前端代码**: `frontend/index.html`

---

## 联系信息

如有问题，请参考：
- 项目README: `README.md`
- 部署指南: `DEPLOY.md`
- 扣子平台: https://www.coze.cn

---

**为人民建好房 · 为工友谋幸福**

中国建筑国际集团 · 第一届"海之子"杯 AI 智能体挑战计划
