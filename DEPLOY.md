# 工友权益明白人 - 部署指南

## 项目简介

"工友权益明白人"是专门为建筑工友（尤其是农民工）服务的权益保障法律顾问智能体，参赛第一届"海之子"杯AI智能体挑战计划。

## 快速部署（推荐）

### 方案1：Vercel部署（最简单，5分钟完成）

1. 访问 https://vercel.com
2. 点击「New Project」
3. 选择「Upload」
4. 拖拽 `frontend/index.html` 文件
5. 点击「Deploy」
6. 获得公网链接：`https://your-project.vercel.app`

### 方案2：Netlify部署（同样简单）

1. 访问 https://netlify.com
2. 点击「Add new site」→「Deploy manually」
3. 拖拽 `frontend/index.html` 文件
4. 获得公网链接：`https://random-name.netlify.app`

### 方案3：GitHub Pages部署

1. 创建GitHub仓库
2. 上传 `frontend/index.html`
3. 进入仓库 Settings → Pages
4. Source选择 `main` 分支，Folder选择 `/ (root)`
5. 点击 Save
6. 获得链接：`https://用户名.github.io/仓库名`

## 配置WebSDK

部署前需要配置WebSDK的token：

1. 在扣子编程平台点击「查看接入方式」
2. 复制WebSDK代码中的token
3. 在 `frontend/index.html` 中找到：
   ```javascript
   refreshToken: () => Promise.resolve('<YOUR_TOKEN>'),
   ```
4. 将 `<YOUR_TOKEN>` 替换为实际token

## 项目结构

```
.
├── frontend/
│   └── index.html          # 前端展示页面（已集成WebSDK）
├── src/
│   ├── agents/
│   │   └── agent.py        # Agent主逻辑（7个专业Agent）
│   ├── tools/              # 工具定义（14个工具）
│   ├── storage/            # 数据库和存储
│   └── main.py             # HTTP服务入口
── config/
│   └── agent_llm_config.json  # 模型配置
├── assets/                 # 知识库文档（32个）
└── DEPLOY.md              # 本文件
```

## 功能特性

### 七大核心功能
1. **法律顾问** - 欠薪、工伤、合同、辞退维权指引
2. **安全守护** - 工地安全隐患识别和报告
3. **心理陪伴** - 情绪疏导和危机干预
4. **薪资管家** - 工时记录、工资核算、欠条生成
5. **技能导师** - 技能提升路径和考证指导
6. **生活管家** - 社保医保、子女教育、租房指南
7. **工友社区** - 互助问答和经验分享

### 技术特点
- 多Agent协作架构（Router + 7个专业Agent）
- RAG增强检索（混合检索+重排序）
- 多模态能力（图片安全隐患识别）
- 短期记忆（滑动窗口保留最近20轮对话）
- 知识库支持（32个权威文档）

## 参赛提交材料

### 1. Bot访问链接
- WebSDK链接：`https://code.coze.cn/web-sdk/7668109916292284459`
- 前端展示页面：部署后的公网链接

### 2. 功能演示
- 权益问答：测试欠薪、工伤、辞退等问题
- 维权指引：生成5步维权路径和证据清单
- 安全守护：上传工地照片识别隐患
- 心理陪伴：测试情绪识别和危机干预

### 3. 技术文档
- 系统架构：多Agent协作图
- 知识库设计：4大类32个文档
- 工具列表：14个专业工具
- 评估体系：L6+能力评估

## 联系方式

如有问题，请联系项目开发者。

---

**为人民建好房 · 为工友谋幸福**

中国建筑国际集团 · 第一届"海之子"杯 AI 智能体挑战计划
