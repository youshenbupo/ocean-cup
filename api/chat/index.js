/**
 * Vercel Serverless Function - 扣子平台 API 代理
 * 
 * 正确解析 run 接口返回的 LangGraph 状态，提取实际回复文本
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
      project_id: "7668109916292284459"
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
              const chunk = extractAnswer(parsed);
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

    // 提取实际回复文本
    const answer = extractAnswer(data);

    if (answer) {
      return res.status(200).json({
        success: true,
        answer: answer
      });
    }

    // 无法提取时，打印完整结构供调试
    console.log('Could not extract answer. Full response:', JSON.stringify(data).substring(0, 1000));
    return res.status(200).json({
      success: true,
      answer: '⚠️ 收到响应但无法解析内容，请查看 Vercel 函数日志',
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

/**
 * 从扣子平台各种响应格式中提取实际回复文本
 * 
 * 支持的格式：
 * 1. { messages: [{content: "...", type: "ai"}, ...] }  — LangGraph 状态
 * 2. { content: { answer: "..." } }
 * 3. { answer: "..." }
 * 4. { output: "..." }
 * 5. { choices: [{message: {content: "..."}}] }  — OpenAI 格式
 */
function extractAnswer(data) {
  if (!data || typeof data !== 'object') return '';

  // 格式1: LangGraph 状态 — messages 数组
  if (data.messages && Array.isArray(data.messages)) {
    // 找最后一条 AI 消息
    for (let i = data.messages.length - 1; i >= 0; i--) {
      const msg = data.messages[i];
      const msgType = msg.type || msg.role || '';
      // AI 消息: type="ai" 或 role="assistant"
      if (msgType === 'ai' || msgType === 'assistant' || msgType === 'AIMessageChunk') {
        const content = msg.content;
        if (content && typeof content === 'string' && content.trim()) {
          return content.trim();
        }
        // content 可能是数组 [{type: "text", text: "..."}]
        if (Array.isArray(content)) {
          const texts = content
            .filter(c => c.type === 'text' && c.text)
            .map(c => c.text);
          if (texts.length > 0) return texts.join('');
        }
      }
    }
  }

  // 格式2: { content: { answer: "..." } }
  if (data.content) {
    if (data.content.answer && typeof data.content.answer === 'string') {
      return data.content.answer.trim();
    }
    if (typeof data.content === 'string' && data.content.trim()) {
      return data.content.trim();
    }
  }

  // 格式3: { answer: "..." }
  if (data.answer && typeof data.answer === 'string') {
    return data.answer.trim();
  }

  // 格式4: { output: "..." }
  if (data.output) {
    if (typeof data.output === 'string' && data.output.trim()) {
      return data.output.trim();
    }
  }

  // 格式5: OpenAI 兼容 { choices: [...] }
  if (data.choices && data.choices[0]) {
    const choice = data.choices[0];
    if (choice.message && choice.message.content) {
      return choice.message.content.trim();
    }
    if (choice.text) {
      return choice.text.trim();
    }
  }

  return '';
}
