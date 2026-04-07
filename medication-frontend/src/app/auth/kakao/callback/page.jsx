'use client'
import { useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api, { parseApiError, showError } from '../../../../lib/api'

// 메인 페이지 스켈레톤 UI
function MainSkeleton() {
  return (
    <main className="min-h-screen bg-gray-50 animate-pulse">
      {/* 상단 헤더 스켈레톤 */}
      <div className="bg-white px-10 py-4 shadow-sm">
        <div className="h-4 w-24 bg-gray-200 rounded mb-2" />
        <div className="h-6 w-32 bg-gray-200 rounded" />
      </div>

      <div className="p-10 grid grid-cols-2 gap-4">
        {/* 오늘 복약 현황 스켈레톤 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 col-span-2">
          <div className="h-5 w-32 bg-gray-200 rounded mb-4" />
          <div className="h-4 w-48 bg-gray-200 rounded" />
        </div>

        {/* 챗봇 버튼 스켈레톤 */}
        <div className="bg-gray-200 rounded-2xl p-6">
          <div className="h-4 w-32 bg-gray-300 rounded mb-2" />
          <div className="h-6 w-40 bg-gray-300 rounded" />
        </div>

        {/* 처방전 업로드 스켈레톤 */}
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <div className="h-5 w-24 bg-gray-200 rounded mb-2" />
          <div className="h-4 w-36 bg-gray-200 rounded mb-4" />
          <div className="w-full border-2 border-dashed border-gray-200 py-4 rounded-xl">
            <div className="h-4 w-16 bg-gray-200 rounded mx-auto" />
          </div>
        </div>
      </div>

      {/* 하단 네비게이션 스켈레톤 */}
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
        <div className="flex-1 py-4 flex justify-center">
          <div className="h-4 w-8 bg-gray-200 rounded" />
        </div>
        <div className="flex-1 py-4 flex justify-center">
          <div className="h-4 w-16 bg-gray-200 rounded" />
        </div>
      </div>
    </main>
  )
}

export default function KakaoCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isProcessing = useRef(false)

  useEffect(() => {
    const handleCallback = async () => {
      // 1. URL에서 code, state, error 추출
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')

      // searchParams가 아직 로드되지 않은 경우 대기 (Next.js hydration)
      if (!code && !errorParam) {
        return
      }

      // 중복 실행 방지 (React 18 Strict Mode, 브라우저 캐시 등)
      if (isProcessing.current) return
      isProcessing.current = true

      // 에러 발생 시 Toast + 로그인 페이지로 리다이렉트
      const handleError = (message) => {
        showError(message)
        setTimeout(() => router.replace('/login'), 1500)
      }

      // 카카오에서 에러 응답이 온 경우
      if (errorParam) {
        handleError(errorDescription || '카카오 로그인 중 오류가 발생했습니다.')
        return
      }

      // 2. state 검증 (CSRF 방지) - localStorage 사용 (모든 탭에서 공유)
      const savedState = localStorage.getItem('oauth_state')
      if (!savedState || savedState !== state) {
        localStorage.removeItem('oauth_state')
        handleError('유효하지 않은 요청입니다.')
        return
      }

      // state 사용 완료 후 삭제 (재사용 방지)
      localStorage.removeItem('oauth_state')

      try {
        // 3. BE에 인가 코드 전달하여 로그인 처리
        // access_token은 HttpOnly 쿠키로 자동 저장됨
        await api.get('/api/v1/auth/kakao/callback', {
          params: { code, state },
        })

        // 4. 메인 페이지로 리다이렉트
        router.replace('/main')
      } catch (err) {
        console.error('로그인 처리 실패:', err)
        const parsed = err.parsed || parseApiError(err)
        handleError(parsed.message)
      }
    }

    handleCallback()
  }, [searchParams, router])

  // 로딩 중 - 메인 페이지 스켈레톤 표시
  return <MainSkeleton />
}
