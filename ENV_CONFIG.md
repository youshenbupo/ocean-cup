# 环境变量配置说明

## 你的扣子平台 API 信息

根据你提供的截图，你的 API 配置如下：

### COZE_API_URL
```
https://yh2g4xtgyt.coze.site/stream_run
```

### COZE_API_KEY
点击扣子平台页面上的「API Token」按钮获取完整 Token。
截图中显示为 `yJh********`（需要点击才能看到完整值）

---

## 在 Vercel 中配置环境变量

### 步骤 1：进入 Vercel 项目设置
1. 打开 https://vercel.com
2. 选择你的项目（gongyou 或类似名称）
3. 点击顶部导航栏的「Settings」

### 步骤 2：添加环境变量
1. 左侧菜单点击「Environment Variables」
2. 点击「Add New」
3. 添加第一个变量：
   - Name: `COZE_API_URL`
   - Value: `https://yh2g4xtgyt.coze.site/stream_run`
   - Environment: 选择 Production, Preview, Development（全选）
   - 点击「Save」

4. 点击「Add New」添加第二个变量：
   - Name: `COZE_API_KEY`
   - Value: 粘贴你从扣子平台获取的完整 API Token
   - Environment: 选择 Production, Preview, Development（全选）
   - 点击「Save」

### 步骤 3：重新部署
1. 回到「Deployments」页面
2. 找到最新的部署，点击右侧的「...」菜单
3. 选择「Redeploy」
4. 等待部署完成

### 步骤 4：测试
1. 打开你的 Vercel 网址（如 https://gongyou.vercel.app）
2. 发送一条消息测试
3. 打开浏览器控制台（F12）查看日志，确认 API 调用成功

---

## 常见问题

### Q: 部署后还是不回复？
A: 检查以下几点：
1. 环境变量是否正确配置（拼写、大小写）
2. API Token 是否完整复制（不要漏掉字符）
3. 查看 Vercel 函数日志：
   - Vercel 项目 → Functions → 点击最新的调用记录
   - 查看是否有错误信息

### Q: 如何查看 Vercel 函数日志？
A: 
1. 打开 Vercel 项目页面
2. 点击顶部「Functions」标签
3. 选择 `/api/chat` 函数
4. 查看最近的调用记录和日志

### Q: API Token 过期了怎么办？
A: 
1. 回到扣子平台
2. 重新生成 API Token
3. 在 Vercel 中更新 COZE_API_KEY 环境变量
4. 重新部署

---

## 代码已修复

我已经修复了以下文件以匹配扣子平台的实际 API 格式：

1. **api/chat/index.js** - 代理函数改为使用扣子 API 格式
2. **src/static/index.html** - 前端改为发送正确的请求格式

### 请求格式（已修复）
```json
{
  "message": "用户输入的消息",
  "session_id": "session_123456"
}
```

### 响应格式（代理返回）
```json
{
  "success": true,
  "data": {
    "content": {
      "answer": "智能体的回复"
    }
  }
}
```

---

## 下一步

1. 将更新后的代码推送到 GitHub：
   ```bash
   git add .
   git commit -m "fix: 修复扣子平台 API 格式"
   git push
   ```

2. Vercel 会自动重新部署（或手动触发 Redeploy）

3. 配置环境变量（如上所述）

4. 测试对话功能
