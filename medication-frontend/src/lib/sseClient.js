/**
 * SSE (Server-Sent Events) async generator client.
 *
 * 백엔드의 ``text/event-stream`` 응답을 fetch + ReadableStream reader 로 읽고,
 * `event:` / `data:` 블록 단위로 파싱해 ``{event, data}`` 객체를 yield 한다.
 *
 * `EventSource` 기본 API 는 cookie 기반 인증을 지원하지 않으므로 fetch +
 * `credentials: 'include'` 패턴을 직접 구현한다.
 *
 * 사용:
 *   for await (const ev of streamSSE('/api/v1/ocr/draft/{id}/stream', {signal})) {
 *     if (ev.event === 'update') handleUpdate(ev.data)
 *     if (ev.event === 'timeout') break  // 또 호출
 *   }
 */

import { config } from '@/config/env'

const SSE_HEADERS = { Accept: 'text/event-stream' }

/**
 * 단일 SSE 연결을 async generator 로 변환한다.
 *
 * @param {string} path  '/api/v1/...' 형태의 백엔드 경로
 * @param {object} [options]
 * @param {AbortSignal} [options.signal]  외부 cancel 용
 * @yields {{event: string, data: any}}  SSE 이벤트
 */
export async function* streamSSE(path, { signal } = {}) {
  const url = `${config.API_BASE_URL}${path}`
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: SSE_HEADERS,
    signal,
  })
  if (!response.ok || !response.body) {
    throw new Error(`SSE connect failed: HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) return
      buffer += decoder.decode(value, { stream: true })
      // SSE event delimiter = blank line ("\n\n").
      let separatorIndex = buffer.indexOf('\n\n')
      while (separatorIndex !== -1) {
        const block = buffer.slice(0, separatorIndex)
        buffer = buffer.slice(separatorIndex + 2)
        const parsed = parseSSEBlock(block)
        if (parsed) yield parsed
        separatorIndex = buffer.indexOf('\n\n')
      }
    }
  } finally {
    reader.releaseLock()
  }
}

/**
 * SSE 한 블록 (event: ... \n data: ...) 을 파싱.
 * 빈 블록 또는 data 가 없으면 null.
 */
function parseSSEBlock(block) {
  let event = 'message'
  const dataLines = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }
  if (dataLines.length === 0) return null
  const raw = dataLines.join('\n')
  try {
    return { event, data: JSON.parse(raw) }
  } catch {
    return { event, data: raw }
  }
}
