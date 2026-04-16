'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import api, { parseApiError, showError } from '@/lib/api'
import { Pill } from 'lucide-react'

// 환경 변수: local, dev, prod
// - local: 개발자 로그인 버튼 표시 (빠른 개발용)
// - dev: 개발자 로그인 버튼 숨김 (카카오 로그인 테스트용)
// - prod: 개발자 로그인 버튼 숨김
const ENV = process.env.NEXT_PUBLIC_ENV || 'local'
const SHOW_DEV_LOGIN = ENV === 'local'

// API Base URL (브라우저에서 직접 호출용)
// - local: http://localhost:8000
// - dev/prod (Docker): '' (Nginx 프록시)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ''

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleKakaoLogin = async () => {
    setIsLoading(true)

    try {
      // 1. BE에서 OAuth 설정 정보 조회 (HMAC signed state 포함)
      const { data } = await api.get('/api/v1/auth/kakao/config')
      const { client_id, redirect_uri, authorize_url, state } = data

      // 2. BE에서 받은 state 저장 (CSRF 방지)
      localStorage.setItem('oauth_state', state)

      // 3. 카카오(Mock) 인증 페이지로 리다이렉트
      // - local/dev: Mock 서버 (authorize_url이 API_BASE_URL/api/v1/mock/kakao/authorize)
      // - prod: 실제 카카오 서버 (https://kauth.kakao.com/oauth/authorize)
      const params = new URLSearchParams({
        client_id,
        redirect_uri,
        response_type: 'code',
        state,
      })

      window.location.href = `${authorize_url}?${params.toString()}`
    } catch (err) {
      console.error('카카오 로그인 설정 조회 실패:', err)
      const parsed = err.parsed || parseApiError(err)
      showError(parsed.message)
      setIsLoading(false)
    }
  }

const handleTestLogin = async () => {
    setIsLoading(true)

    try {
      // 1. 브라우저 이동 없이 백그라운드(Axios)에서 백엔드 API 호출
      // api 객체를 사용하므로 프록시(localhost:3000 -> localhost:8000)를 안전하게 탑니다.
      const response = await api.get('/api/v1/auth/kakao/callback', {
        params: {
          code: 'dev_test_login',
          state: 'dev_mode'
        }
      })

      // 2. 백엔드가 정상적으로 토큰(쿠키)과 JSON(200 OK)을 응답했다면?
      if (response.status === 200) {
        const { show_survey } = response.data

        // 프론트엔드가 주도적으로 화면 전환
        if (show_survey) {
          router.push('/main?showSurvey=true')
        } else {
          router.push('/main')
        }
      }
    } catch (err) {
      console.error('개발용 로그인 실패:', err)
      const parsed = err.parsed || parseApiError(err)
      showError(parsed.message || '로그인 처리 중 오류가 발생했습니다.')
      setIsLoading(false)
    }
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gray-50">

      <div className="bg-white p-10 rounded-2xl shadow-sm w-96 text-center">

        {/* 로고 */}
        <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Pill size={32} className="text-blue-500" />
        </div>
        <h1 className="text-2xl font-bold mb-1">복약 안내</h1>
        <p className="text-gray-400 text-sm mb-8">내 약을 안전하게 관리하세요</p>

        {/* 카카오 버튼 */}
        <button
          onClick={() => handleKakaoLogin()}
          disabled={isLoading}
          className="w-full bg-yellow-400 py-3 rounded-xl font-semibold text-sm mb-3 cursor-pointer hover:bg-yellow-500 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? '연결 중...' : '카카오로 로그인'}
        </button>

        {/* 개발자 로그인 버튼 (local 환경에서만 표시) */}
        {SHOW_DEV_LOGIN && (
          <button
            onClick={handleTestLogin}
            disabled={isLoading}
            className="w-full bg-slate-800 text-white py-3 rounded-xl font-semibold text-sm mb-3 cursor-pointer hover:bg-black transition-all disabled:opacity-50"
          >
            개발자로 로그인 ({ENV})
          </button>
        )}

        {/* 구분선 */}
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-gray-400 text-xs">또는</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* 네이버 버튼 */}
        <button className="w-full bg-green-500 text-white py-3 rounded-xl font-semibold text-sm cursor-pointer hover:bg-green-600 active:scale-[0.98] transition-transform duration-150">
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
