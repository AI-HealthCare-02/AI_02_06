'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import PropTypes from 'prop-types'
import api from '@/lib/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'

// 인증이 필요하지 않은 공개 경로들 (화이트리스트)
const PUBLIC_ROUTES = [
  '/',           // 랜딩 페이지
  '/login'       // 로그인 페이지
]

// 경로가 공개 경로인지 확인
function isPublicRoute(pathname) {
  // 정확한 매치
  if (PUBLIC_ROUTES.includes(pathname)) {
    return true
  }

  // /auth로 시작하는 모든 경로 (로그인 처리 중)
  if (pathname.startsWith('/auth/')) {
    return true
  }

  return false
}

/**
 * 전역 라우팅 가드
 * 인증이 필요한 모든 페이지를 자동으로 보호
 */
export default function GlobalAuthGuard({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const checkAuth = async () => {
      // 공개 경로는 인증 확인 생략
      if (isPublicRoute(pathname)) {
        setIsAuthenticated(true)
        setIsLoading(false)
        return
      }

      try {
        // 인증 확인 API 호출 (인터셉터 비활성화)
        await api.get('/api/v1/profiles', {
          skipAuthInterceptor: true  // 인터셉터 비활성화 플래그
        })
        setIsAuthenticated(true)
      } catch (error) {
        // 인증 실패 시 조용히 리다이렉트 (토스트 없음)
        console.log('Authentication failed, redirecting to login')
        router.replace('/login')
        return
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [router, pathname])

  // 로딩 중
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <LoadingSpinner size="lg" />
          <p className="text-gray-600 font-medium">인증 확인 중...</p>
        </div>
      </div>
    )
  }

  // 인증되지 않은 경우 아무것도 렌더링하지 않음 (리다이렉트 중)
  if (!isAuthenticated) {
    return null
  }

  // 인증된 경우 또는 공개 경로인 경우 자식 컴포넌트 렌더링
  return children
}

GlobalAuthGuard.propTypes = {
  children: PropTypes.node.isRequired
}
