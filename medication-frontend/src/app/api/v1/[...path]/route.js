/**
 * API Proxy Route
 *
 * Vercel(HTTPS)에서 EC2(HTTP)로 요청을 프록시합니다.
 * Mixed Content 문제를 서버 사이드에서 해결합니다.
 *
 * /api/v1/* 요청 -> http://52.78.62.12/api/v1/*
 */

const API_BASE_URL = process.env.API_BASE_URL || 'http://52.78.62.12'

export async function GET(request, { params }) {
  return proxyRequest(request, params, 'GET')
}

export async function POST(request, { params }) {
  return proxyRequest(request, params, 'POST')
}

export async function PATCH(request, { params }) {
  return proxyRequest(request, params, 'PATCH')
}

export async function PUT(request, { params }) {
  return proxyRequest(request, params, 'PUT')
}

export async function DELETE(request, { params }) {
  return proxyRequest(request, params, 'DELETE')
}

async function proxyRequest(request, { params }, method) {
  const { path } = await params
  const targetPath = Array.isArray(path) ? path.join('/') : path
  const targetUrl = `${API_BASE_URL}/api/v1/${targetPath}`

  // 쿼리 파라미터 전달
  const url = new URL(request.url)
  const queryString = url.search

  try {
    const headers = new Headers()

    // 필요한 헤더 전달
    const contentType = request.headers.get('content-type')
    if (contentType) {
      headers.set('content-type', contentType)
    }

    // 쿠키 전달 (인증용)
    const cookie = request.headers.get('cookie')
    if (cookie) {
      headers.set('cookie', cookie)
    }

    const fetchOptions = {
      method,
      headers,
    }

    // Body 전달 (GET, HEAD 제외)
    if (method !== 'GET' && method !== 'HEAD') {
      const body = await request.text()
      if (body) {
        fetchOptions.body = body
      }
    }

    const response = await fetch(`${targetUrl}${queryString}`, fetchOptions)

    // 응답 헤더 복사
    const responseHeaders = new Headers()
    response.headers.forEach((value, key) => {
      // hop-by-hop 헤더 제외
      if (!['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value)
      }
    })

    // Set-Cookie 헤더 전달 (인증 토큰)
    const setCookie = response.headers.get('set-cookie')
    if (setCookie) {
      responseHeaders.set('set-cookie', setCookie)
    }

    const responseBody = await response.text()

    return new Response(responseBody, {
      status: response.status,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('Proxy error:', error)
    return new Response(JSON.stringify({ error: 'Proxy request failed' }), {
      status: 502,
      headers: { 'content-type': 'application/json' },
    })
  }
}
