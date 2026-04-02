'use client'

import { useState } from 'react'
import api, { parseApiError, showError } from '../../lib/api'

function generateState(): string {
  const array = new Uint8Array(16)
  crypto.getRandomValues(array)
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)

  const handleKakaoLogin = async () => {
    setIsLoading(true)

    try {
      // 1. BE에서 OAuth 설정 정보 조회
      const { data } = await api.get('/api/v1/auth/kakao/config')
      const { client_id, redirect_uri, authorize_url } = data

      // 2. CSRF 방지용 state 생성 및 저장
      const state = generateState()
      sessionStorage.setItem('oauth_state', state)

      // 3. 카카오(Mock) 인증 페이지로 리다이렉트
      const params = new URLSearchParams({
        client_id,
        redirect_uri,
        response_type: 'code',
        state,
      })

      window.location.href = `${authorize_url}?${params.toString()}`
    } catch (err: any) {
      console.error('카카오 로그인 설정 조회 실패:', err)
      const parsed = err.parsed || parseApiError(err)
      showError(parsed.message)
      setIsLoading(false)
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gray-50">

      <div className="bg-white p-10 rounded-2xl shadow-sm w-96 text-center">

        {/* 로고 */}
        <div className="text-5xl mb-4">💊</div>
        <h1 className="text-2xl font-bold mb-1">복약 안내</h1>
        <p className="text-gray-400 text-sm mb-8">내 약을 안전하게 관리하세요</p>

        {/* 카카오 버튼 */}
        <button
          onClick={handleKakaoLogin}
          disabled={isLoading}
          className="w-full bg-yellow-400 py-3 rounded-xl font-semibold text-sm mb-3 cursor-pointer hover:bg-yellow-500 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? '연결 중...' : '카카오로 로그인'}
        </button>

        {/* 구분선 */}
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-gray-400 text-xs">또는</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* 네이버 버튼 */}
        <button className="w-full bg-green-500 text-white py-3 rounded-xl font-semibold text-sm cursor-pointer hover:bg-green-600">
          네이버로 로그인
        </button>

        {/* 하단 약관 */}
        <p className="text-gray-300 text-xs mt-8">
          로그인 시 서비스 이용약관에 동의하게 됩니다
        </p>

      </div>

    </main>
  )
}