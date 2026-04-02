'use client'
import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api from '../../../lib/api'

export default function CallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {

  }, [])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-gray-500">로그인 처리 중...</p>
    </div>
  )
}
