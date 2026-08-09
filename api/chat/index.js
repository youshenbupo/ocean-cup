/**
 * Vercel Serverless Function - 扣子平台 API 代理
 * 
 * 将前端请求转发到扣子平台的 stream_run 接口
 * 解决跨域问题和 API 密钥暴露问题
 */

export default async function handler(req, res) {
  // 只允许 POST 请求
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, session_id } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Missing message parameter' });
    }

    const apiUrl = process.env.COZE_API_URL;
    const apiKey = process.env.COZE_API_KEY;

    if (!apiUrl || !apiKey) {
      console.error('Missing environment variables:', { 
        hasApiUrl: !!apiUrl, 
        hasApiKey: !!apiKey 
      });
      return res.status(500).json({ 
        error: 'Server configuration error: Missing COZE_API_URL or COZE_API_KEY' 
      });
    }

    // 构造扣子平台 API 请求体
    const requestBody = {
      content: {
        query: {
          prompt: [
            {
              type: "text",
              content: {
                text: message
              }
            }
          ]
        }
      },
      type: "query",
      session_id: session_id || `session_${Date.now()}`,
      project_id: 7668109916292284459
    };

    console.log('Proxying request to Coze API:', {
      url: apiUrl,
      sessionId: requestBody.session_id,
      messageLength: message.length
    });

    // 转发请求到扣子平台
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Coze API error:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      });
      return res.status(response.status).json({ 
        error: `Coze API error: ${response.status}`,
        details: errorText
      });
    }

    // 解析响应
    const data = await response.json();
    
    console.log('Coze API response received:', {
      hasContent: !!data.content,
      contentType: typeof data.content
    });

    // 返回给前端
    res.status(200).json({
      success: true,
      data: data
    });

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message 
    });
  }
}
