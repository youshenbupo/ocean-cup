# 工友权益明白人 - Vercel 部署指南

## 快速部署（3 步搞定）

### 第 1 步：上传到 GitHub

```bash
cd /workspace/projects
git init
git add .
git commit -m "工友权益明白人"
git remote add origin https://github.com/你的用户名/gongyou.git
git push -u origin main
```

### 第 2 步：在 Vercel 部署

1. 打开 https://vercel.com
2. 点击「Add New...」→「Project」
3. 选择你的 GitHub 仓库 `gongyou`
4. 点击「Deploy」

### 第 3 步：配置环境变量（关键！）

部署后，在 Vercel 项目设置中添加环境变量：

1. 进入项目 → Settings → Environment Variables
2. 添加两个变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `COZE_API_URL` | `https://你的扣子API地址/v1/chat/completions` | 扣子平台的 API 地址 |
| `COZE_API_KEY` | `你的API密钥` | 扣子平台的 API Key |

3. 点击「Save」
4. 在 Deployments 页面点击「Redeploy」重新部署

### 获取扣子平台 API 地址和密钥

1. 登录扣子平台 → 进入「工友权益明白人」项目
2. 点击右上角「发布」
3. 选择「API」渠道
4. 复制 API Base URL 和 API Key

### 完成！

访问你的 Vercel 地址（如 `https://gongyou.vercel.app`），开始对话！

---

## 架构说明

```
用户浏览器 → Vercel 前端 (index.html)
                ↓
         Vercel Serverless (/api/chat)
                ↓
         扣子平台 API (智能体后端)
                ↓
         模型 + 数据库 + 知识库
```

前端通过 Vercel 的 serverless 函数代理请求到扣子平台，避免 CORS 问题。
