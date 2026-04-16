'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import LoadingSpinner from './LoadingSpinner'

export default function PageLoader() {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  useEffect(() => {
    const handleStart = () => setLoading(true)
    const handleComplete = () => setLoading(false)

    // Next.js 라우터 이벤트 리스너 (App Router용)
    const originalPush = router.push
    router.push = (...args) => {
      handleStart()
      return originalPush.apply(router, args).finally(handleComplete)
    }

    return () => {
      router.push = originalPush
    }
  }, [router])

  if (!loading) return null

  return (
    <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-[9999] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="lg" />
        <p className="text-gray-600 font-medium">페이지를 불러오는 중...</p>
      </div>
    </div>
  )
}
