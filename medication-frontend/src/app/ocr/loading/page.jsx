'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OcrLoadingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)

  const steps = [
    '이미지를 업로드하고 있어요...',
    '처방전을 분석하고 있어요...',
    '약품 정보를 인식하고 있어요...',
    '거의 다 됐어요!',
  ]

  useEffect(() => {
    // 단계별로 메시지 변경
    const timer = setInterval(() => {
      setStep(prev => {
        if (prev < steps.length - 1) return prev + 1
        return prev
      })
    }, 1500)

    // 나중에 실제 API 완료되면 result 페이지로 이동
    // 지금은 6초 후 자동 이동
    const redirect = setTimeout(() => {
      router.push('/ocr/result')
    }, 6000)

    return () => {
      clearInterval(timer)
      clearTimeout(redirect)
    }
  }, [])

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">

      {/* 로딩 애니메이션 */}
      <div className="bg-white rounded-2xl shadow-sm p-16 text-center max-w-md w-full mx-4">

        {/* 회전 원 */}
        <div className="relative w-24 h-24 mx-auto mb-8">
          <div className="absolute inset-0 rounded-full border-4 border-gray-100" />
          <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center text-3xl">
            💊
          </div>
        </div>

        <h2 className="text-xl font-bold mb-3">처방전 분석 중</h2>
        <p className="text-gray-400 text-sm mb-8">{steps[step]}</p>

        {/* 진행 바 */}
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
            style={{width: `${((step + 1) / steps.length) * 100}%`}}
          />
        </div>
        <p className="text-xs text-gray-300 mt-3">잠시만 기다려주세요</p>

      </div>

    </main>
  )
}