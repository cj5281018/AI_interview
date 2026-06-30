const API_BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || '请求失败')
  }
  return res.json()
}

export function healthCheck() {
  return request('/health')
}

export function listModels() {
  return request('/models')
}

export function listStyles() {
  return request('/styles')
}

export function uploadResume(file) {
  const form = new FormData()
  form.append('file', file)
  return fetch(`${API_BASE}/resume/upload`, { method: 'POST', body: form }).then(r => r.json())
}

export function setupInterview(config) {
  return request('/setup', { method: 'POST', body: JSON.stringify(config) })
}

export function endInterview(sessionId) {
  return request('/end', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) })
}

export function getReport(sessionId) {
  return request(`/report/${sessionId}`)
}

export function listSessions() {
  return request('/sessions')
}

/**
 * 流式聊天 — 返回一个可取消的 fetch + ReadableStream reader
 * 用法:
 *   const stream = chatStream(sessionId, message)
 *   for await (const chunk of stream) { ... }
 *   stream.cancel() // 停止
 */
export function chatStream(sessionId, message) {
  const controller = new AbortController()

  const stream = (async function* () {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal: controller.signal,
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            yield JSON.parse(line.slice(6))
          } catch {
            // skip malformed
          }
        }
      }
    }
  })()

  stream.cancel = () => {
    controller.abort()
    fetch(`${API_BASE}/chat-stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {})
  }

  return stream
}
