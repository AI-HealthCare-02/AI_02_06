'use client'

// TanStack Query v5 — server-state 통합 캐시.
//
// 도입 이유 (2025-2026 React 표준):
// - 같은 query 키에 대한 동시 호출 자동 dedupe (network 1회)
// - staleTime 동안 라우트 재방문 시 GET 0회 (cache hit)
// - mutation.onSuccess 안에서 invalidateQueries 호출만으로 cross-cascade 동기화
//   (예: 처방전 삭제 → 가이드/챌린지 캐시 자동 invalidate → 다음 read 에 refetch)
// - React 18+ Suspense / concurrent rendering 친화
//
// Provider 는 상위 layout 한 곳에 mount 하고, 도메인별 query/mutation hook 은
// `src/queries/*` 에서 정의해 페이지 컴포넌트가 직접 useQuery/useMutation 을 부르지
// 않도록 한다 — 도메인 결정을 한 곳에 모으는 게 유지보수성↑.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export default function QueryProvider({ children }) {
  // 인스턴스를 useState 의 초기값으로 — Strict Mode 더블 mount 에서도 단일 client 유지.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 60초 안에는 같은 키 재방문 시 cache hit (GET 0회). 그 후 refetch.
            // 너무 길면 stale 데이터 노출, 너무 짧으면 GET 폭증 — 균형값.
            staleTime: 60 * 1000,
            // 창 포커스 복귀에 따른 자동 refetch — 사용자 의도와 어긋나는 경우가 많아 off.
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // 4xx (인증/권한/리소스 없음) 는 재시도 무의미.
              const status = error?.response?.status
              if (status && status >= 400 && status < 500) return false
              return failureCount < 2
            },
          },
          mutations: {
            // 401 등 글로벌 인증 실패는 api interceptor 가 처리. 여기선 단순 재시도 X.
            retry: false,
          },
        },
      }),
  )

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
