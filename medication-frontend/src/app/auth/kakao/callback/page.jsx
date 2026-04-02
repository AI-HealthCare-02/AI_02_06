'use client'
import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api, { parseApiError } from '../../../../lib/api'

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
  const [error, setError] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    const handleCallback = async () => {
      // 1. URL에서 code, state, error 추출
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')

      // 카카오에서 에러 응답이 온 경우
      if (errorParam) {
        setError(errorDescription || '카카오 로그인 중 오류가 발생했습니다.')
        return
      }

      // code가 없는 경우
      if (!code) {
        setError('인가 코드가 없습니다.')
        return
      }

      // 2. state 검증 (CSRF 방지)
      const savedState = sessionStorage.getItem('oauth_state')
      if (!savedState || savedState !== state) {
        setError('유효하지 않은 요청입니다. (state 불일치)')
        sessionStorage.removeItem('oauth_state')
        return
      }

      // state 사용 완료 후 삭제
      sessionStorage.removeItem('oauth_state')

      // state 검증 완료 - 스켈레톤 UI 표시 시작
      setIsProcessing(true)

      try {
        // 3. BE에 인가 코드 전달하여 로그인 처리
        const { data } = await api.get('/api/v1/auth/kakao/callback', {
          params: { code, state },
        })

        // 4. access_token 저장
        localStorage.setItem('access_token', data.access_token)

        // 5. 신규 사용자 여부에 따른 분기 (필요 시)
        if (data.is_new_user) {
          console.log('신규 사용자 가입 완료')
        }

        // 6. 메인 페이지로 리다이렉트
        router.replace('/main')
      } catch (err) {
        console.error('로그인 처리 실패:', err)
        const parsed = err.parsed || parseApiError(err)
        setError(parsed.message)
        setIsProcessing(false)
      }
    }

    handleCallback()
  }, [searchParams, router])

  // 에러 발생 시
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-red-500">{error}</p>
        <button
          onClick={() => router.replace('/login')}
          className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
        >
          로그인 페이지로 돌아가기
        </button>
      </div>
    )
  }

  // BE 요청 중 - 메인 페이지 스켈레톤 표시
  if (isProcessing) {
    return <MainSkeleton />
  }

  // state 검증 중
  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-gray-500">로그인 처리 중...</p>
    </div>
  )
}
