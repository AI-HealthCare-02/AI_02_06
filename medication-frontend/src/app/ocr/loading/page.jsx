'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Pill } from 'lucide-react'
import api from '@/lib/api'

export default function OcrLoadingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [error, setError] = useState(null)

  const steps = [
    '이미지를 업로드하고 있어요...',
    '처방전을 분석하고 있어요...',
    '약품 정보를 인식하고 있어요...',
    '거의 다 됐어요!',
  ]

  useEffect(() => {
    const ticker = setInterval(() => {
      setStep(prev => prev < steps.length - 1 ? prev + 1 : prev)
    }, 1500)

    const run = async () => {
      try {
        const fileData = sessionStorage.getItem('ocrFileData')
        const fileName = sessionStorage.getItem('ocrFileName')
        const fileType = sessionStorage.getItem('ocrFileType')

        if (!fileData) {
          router.push('/ocr')
          return
        }

        const res = await fetch(fileData)
        const blob = await res.blob()
        const file = new File([blob], fileName, { type: fileType })

        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('/api/v1/ocr/extract', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
        })

        // 원본 이미지는 브라우저에서 즉시 파기
        sessionStorage.removeItem('ocrFileData')
        sessionStorage.removeItem('ocrFileName')
        sessionStorage.removeItem('ocrFileType')

        // Redis에 임시 저장된 draft_id를 들고 결과 페이지로 이동
        const draftId = response.data.draft_id
        router.push(`/ocr/result?draft_id=${draftId}`)

      } catch (err) {
        const msg = err.parsed?.message || err.response?.data?.detail || '분석 중 오류가 발생했습니다.'
        setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
        clearInterval(ticker)
      }
    }

    run()
    return () => clearInterval(ticker)
  }, [router])

  if (error) {
    return (
      <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
        <div className="bg-white rounded-2xl shadow-sm p-16 text-center max-w-md w-full mx-4">
          <p className="text-4xl mb-4">❌</p>
          <h2 className="text-xl font-bold mb-3">분석 실패</h2>
          <p className="text-gray-400 text-sm mb-8">{error}</p>
          <button
            onClick={() => router.push('/ocr')}
            className="bg-blue-900 text-white px-8 py-3 rounded-xl font-semibold">
            다시 시도
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm p-16 text-center max-w-md w-full mx-4">
        <div className="relative w-24 h-24 mx-auto mb-8">
          <div className="absolute inset-0 rounded-full border-4 border-gray-100" />
          <div className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Pill size={28} className="text-blue-500" />
          </div>
        </div>
        <h2 className="text-xl font-bold mb-3">처방전 분석 중</h2>
        <p className="text-gray-400 text-sm mb-8">{steps[step]}</p>
        <div className="w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${((step + 1) / steps.length) * 100}%` }}
          />
        </div>
        <p className="text-xs text-gray-300 mt-3">잠시만 기다려주세요</p>
      </div>
    </main>
  )
}
