/**
 * Vercel Serverless Function - Chat API Proxy
 * 
 * 这个函数作为代理，将前端请求转发到扣子平台的智能体API
 * 解决了跨域(CORS)问题和API地址配置问题
 * 
 * 环境变量配置（在Vercel项目设置中添加）：
 * - COZE_API_URL: 扣子平台API地址（例如：https://api.coze.cn/v1）
 * - COZE_API_KEY: 扣子平台API密钥
 */

export default async function handler(req, res) {
  // 只允许 POST 请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // 从环境变量获取API配置
  const API_URL = process.env.COZE_API_URL;
  const API_KEY = process.env.COZE_API_KEY;

  // 检查配置是否存在
  if (!API_URL || !API_KEY) {
    return res.status(500).json({
      error: 'API configuration missing',
      message: '请在Vercel项目设置中配置 COZE_API_URL 和 COZE_API_KEY 环境变量'
    });
  }

  try {
    // 转发请求到扣子平台API
    const response = await fetch(`${API_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`,
      },
      body: JSON.stringify(req.body),
    });

    // 获取响应数据
    const data = await response.json();

    // 返回响应
    res.status(response.status).json(data);

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
}
