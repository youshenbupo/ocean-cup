/**
 * Vercel Serverless Function - 扣子平台 API 代理
 * 
 * 优先使用 run（非流式）接口，兼容 stream_run（流式）接口
 */

export const config = {
  maxDuration: 60
};

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { message, session_id } = req.body;

    if (!message) {
      return res.status(400).json({ error: 'Missing message parameter' });
    }

    let apiUrl = process.env.COZE_API_URL || '';
    const apiKey = process.env.COZE_API_KEY;

    if (!apiUrl || !apiKey) {
      console.error('Missing env vars:', { hasApiUrl: !!apiUrl, hasApiKey: !!apiKey });
      return res.status(500).json({
        error: '服务未配置，请在 Vercel 环境变量中设置 COZE_API_URL 和 COZE_API_KEY'
      });
    }

    // 自动将 stream_run 替换为 run（非流式更稳定）
    if (apiUrl.includes('stream_run')) {
      apiUrl = apiUrl.replace('stream_run', 'run');
      console.log('Auto-switched to non-streaming endpoint:', apiUrl);
    }

    // 构造扣子平台请求体
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

    console.log('Proxying to:', apiUrl, '| message:', message.substring(0, 50));

    // 请求扣子平台
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
      console.error('Coze API error:', response.status, errorText.substring(0, 300));
      return res.status(response.status).json({
        error: `API 返回错误 ${response.status}`,
        details: errorText.substring(0, 300)
      });
    }

    const contentType = response.headers.get('content-type') || '';

    // ===== 流式响应（兜底） =====
    if (contentType.includes('text/event-stream')) {
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      let fullAnswer = '';
      let buffer = '';

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed.startsWith('data:')) continue;
            const dataStr = trimmed.slice(5).trim();
            if (dataStr === '[DONE]') continue;

            try {
              const parsed = JSON.parse(dataStr);
              let chunk = '';
              if (parsed.content && parsed.content.answer) chunk = parsed.content.answer;
              else if (parsed.answer) chunk = parsed.answer;
              else if (parsed.type === 'answer' && parsed.content) {
                chunk = typeof parsed.content === 'string' ? parsed.content : (parsed.content.text || '');
              }
              if (chunk) {
                fullAnswer += chunk;
                res.write(`data: ${JSON.stringify({ type: 'chunk', content: chunk })}\n\n`);
              }
              if (parsed.type === 'done' || parsed.last === true) {
                res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer })}\n\n`);
              }
            } catch {}
          }
        }
        res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer: fullAnswer || '暂无回复' })}\n\n`);
        res.end();
      } catch (err) {
        console.error('Stream error:', err);
        if (!res.writableEnded) {
          res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer: fullAnswer || '响应中断' })}\n\n`);
          res.end();
        }
      }
      return;
    }

    // ===== 非流式 JSON 响应（主路径） =====
    const data = await response.json();
    console.log('Response keys:', Object.keys(data));

    // 解析扣子平台响应 - 支持多种格式
    let answer = '';

    // 格式1: { content: { answer: "..." } }
    if (data.content && data.content.answer) {
      answer = data.content.answer;
    }
    // 格式2: { answer: "..." }
    else if (data.answer) {
      answer = data.answer;
    }
    // 格式3: { output: "..." }
    else if (data.output) {
      answer = typeof data.output === 'string' ? data.output : JSON.stringify(data.output);
    }
    // 格式4: { messages: [...] }  取最后一条 assistant 消息
    else if (data.messages && Array.isArray(data.messages)) {
      const assistantMsgs = data.messages.filter(m => m.role === 'assistant' || m.type === 'answer');
      if (assistantMsgs.length > 0) {
        const last = assistantMsgs[assistantMsgs.length - 1];
        answer = last.content || last.text || last.answer || '';
      }
    }
    // 格式5: OpenAI 兼容 { choices: [...] }
    else if (data.choices && data.choices[0]) {
      answer = data.choices[0].message?.content || data.choices[0].text || '';
    }

    if (answer) {
      return res.status(200).json({
        success: true,
        answer: answer
      });
    }

    // 无法解析时返回原始数据
    console.log('Unparsed response, returning raw data');
    return res.status(200).json({
      success: true,
      answer: JSON.stringify(data),
      raw: true
    });

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({
      error: '服务器内部错误',
      message: error.message
    });
  }
}
