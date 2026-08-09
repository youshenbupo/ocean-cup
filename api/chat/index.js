/**
 * Vercel Serverless Function - 扣子平台 API 代理
 * 
 * 支持 stream_run 流式响应，将 SSE 事件解析后返回给前端
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

    const apiUrl = process.env.COZE_API_URL;
    const apiKey = process.env.COZE_API_KEY;

    if (!apiUrl || !apiKey) {
      console.error('Missing env vars:', { hasApiUrl: !!apiUrl, hasApiKey: !!apiKey });
      return res.status(500).json({
        error: 'Server config error: Missing COZE_API_URL or COZE_API_KEY'
      });
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

    console.log('Proxying to:', apiUrl, '| sessionId:', requestBody.session_id);

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
      console.error('Coze API error:', response.status, errorText.substring(0, 500));
      return res.status(response.status).json({
        error: `Coze API error: ${response.status}`,
        details: errorText.substring(0, 500)
      });
    }

    const contentType = response.headers.get('content-type') || '';

    // ===== 流式响应（SSE） =====
    if (contentType.includes('text/event-stream') || apiUrl.includes('stream')) {
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

          // 解析 SSE 事件
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留最后一个不完整的行

          for (const line of lines) {
            const trimmed = line.trim();

            if (trimmed.startsWith('data:')) {
              const dataStr = trimmed.slice(5).trim();

              if (dataStr === '[DONE]') {
                continue;
              }

              try {
                const parsed = JSON.parse(dataStr);

                // 多种可能的响应结构
                let textChunk = '';
                if (parsed.content && parsed.content.answer) {
                  textChunk = parsed.content.answer;
                } else if (parsed.answer) {
                  textChunk = parsed.answer;
                } else if (parsed.type === 'answer' && parsed.content) {
                  if (typeof parsed.content === 'string') {
                    textChunk = parsed.content;
                  } else if (parsed.content.text) {
                    textChunk = parsed.content.text;
                  }
                } else if (parsed.type === 'message' && parsed.content) {
                  if (typeof parsed.content === 'string') {
                    textChunk = parsed.content;
                  } else if (parsed.content.text) {
                    textChunk = parsed.content.text;
                  }
                }

                if (textChunk) {
                  fullAnswer += textChunk;
                  // 向前端发送 SSE 事件
                  res.write(`data: ${JSON.stringify({ type: 'chunk', content: textChunk })}\n\n`);
                }

                // 检查是否完成
                if (parsed.type === 'done' || parsed.event === 'done' || parsed.last === true) {
                  res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer: fullAnswer })}\n\n`);
                }

              } catch (parseErr) {
                // 不是 JSON，可能是纯文本内容
                if (dataStr && dataStr !== '[DONE]') {
                  fullAnswer += dataStr;
                  res.write(`data: ${JSON.stringify({ type: 'chunk', content: dataStr })}\n\n`);
                }
              }
            }
          }
        }

        // 处理缓冲区剩余内容
        if (buffer.trim()) {
          const remaining = buffer.trim();
          if (remaining.startsWith('data:')) {
            const dataStr = remaining.slice(5).trim();
            if (dataStr && dataStr !== '[DONE]') {
              try {
                const parsed = JSON.parse(dataStr);
                let textChunk = parsed.content?.answer || parsed.answer || parsed.content?.text || '';
                if (textChunk) {
                  fullAnswer += textChunk;
                  res.write(`data: ${JSON.stringify({ type: 'chunk', content: textChunk })}\n\n`);
                }
              } catch {}
            }
          }
        }

        // 发送完成事件
        res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer: fullAnswer || '暂无回复' })}\n\n`);
        res.end();

      } catch (streamErr) {
        console.error('Stream read error:', streamErr);
        // 尝试发送已收集的内容
        if (fullAnswer) {
          res.write(`data: ${JSON.stringify({ type: 'done', fullAnswer: fullAnswer })}\n\n`);
        } else {
          res.write(`data: ${JSON.stringify({ type: 'error', message: 'Stream interrupted' })}\n\n`);
        }
        res.end();
      }

      return;
    }

    // ===== 非流式 JSON 响应 =====
    const data = await response.json();
    console.log('Non-stream response keys:', Object.keys(data));

    // 解析多种响应格式
    let answer = '';
    if (data.content && data.content.answer) {
      answer = data.content.answer;
    } else if (data.answer) {
      answer = data.answer;
    } else if (data.output) {
      answer = typeof data.output === 'string' ? data.output : JSON.stringify(data.output);
    } else if (data.choices && data.choices[0]) {
      answer = data.choices[0].message?.content || data.choices[0].text || '';
    } else {
      // 返回完整数据让前端处理
      return res.status(200).json({ success: true, data: data, format: 'raw' });
    }

    return res.status(200).json({
      success: true,
      answer: answer,
      format: 'json'
    });

  } catch (error) {
    console.error('Proxy error:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
}
