'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { CheckCircle } from 'lucide-react'
import api from '@/lib/api'

const STEPS = [
  '처방전 이미지를 읽고 있어요...',
  'AI가 약품 정보를 분석하고 있어요...',
  '복용 방법을 정리하고 있어요...',
  '거의 다 됐어요!',
]

function MedCardSkeleton({ delay = 0 }) {
  return (
    <div
      className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 animate-pulse"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex justify-between items-center mb-5">
        <div className="h-5 w-40 bg-gray-200 rounded-lg" />
        <div className="w-5 h-5 bg-gray-100 rounded" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[0, 1, 2, 3].map((j) => (
          <div key={j} className="bg-gray-50 p-2 rounded-xl border border-gray-100">
            <div className="h-2.5 w-12 bg-gray-200 rounded mb-2" />
            <div className="h-3.5 w-10 bg-gray-200 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

function SuccessOverlay() {
  return (
    <div className="fixed inset-0 bg-white flex flex-col items-center justify-center z-50 animate-in fade-in duration-300">
      <div className="w-20 h-20 bg-gray-900 rounded-full flex items-center justify-center mb-6">
        <CheckCircle size={36} className="text-white" strokeWidth={1.5} />
      </div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">분석 완료!</h2>
      <p className="text-sm text-gray-400">처방전 내용을 확인해주세요</p>
    </div>
  )
}

function PrescriptionSkeleton({ step }) {
  const progress = ((step + 1) / STEPS.length) * 100

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-100 px-10 py-4 flex items-center gap-4 animate-pulse">
        <div className="w-6 h-6 bg-gray-200 rounded-full" />
        <div className="flex-1">
          <div className="h-4 w-36 bg-gray-200 rounded-lg mb-2" />
          <div className="h-3 w-48 bg-gray-100 rounded-lg" />
        </div>
      </div>

      {/* 진행 상태 안내 */}
      <div className="bg-white border-b border-gray-100 px-10 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex justify-between items-center mb-2">
            <p className="text-xs font-medium text-gray-500">{STEPS[step]}</p>
            <p className="text-xs text-gray-300">{step + 1} / {STEPS.length}</p>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1 overflow-hidden">
            <div
              className="h-1 rounded-full bg-gray-400 transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-10 py-8 space-y-4">
        {/* 안내 배너 */}
        <div className="bg-blue-50 rounded-2xl p-4 flex items-center gap-3 animate-pulse">
          <div className="w-8 h-8 bg-blue-100 rounded-full shrink-0" />
          <div className="flex-1">
            <div className="h-3.5 w-24 bg-blue-100 rounded mb-2" />
            <div className="h-3 w-52 bg-blue-100 rounded" />
          </div>
        </div>

        {/* 약품 카드 3개 */}
        <MedCardSkeleton delay={0} />
        <MedCardSkeleton delay={150} />
        <MedCardSkeleton delay={300} />

        {/* 하단 버튼 */}
        <div className="flex gap-3 pt-2 animate-pulse">
          <div className="flex-1 h-14 bg-white border border-gray-200 rounded-xl" />
          <div className="flex-1 h-14 bg-gray-200 rounded-xl" />
        </div>
      </div>
    </div>
  )
}

export default function OcrLoadingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    const ticker = setInterval(() => {
      setStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev))
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

        sessionStorage.removeItem('ocrFileData')
        sessionStorage.removeItem('ocrFileName')
        sessionStorage.removeItem('ocrFileType')

        clearInterval(ticker)
        setDone(true)

        const draftId = response.data.draft_id
        setTimeout(() => router.push(`/ocr/result?draft_id=${draftId}`), 1200)
      } catch (err) {
        const msg = err.parsed?.message || err.response?.data?.detail || '분석 중 오류가 발생했습니다.'
        router.push(`/ocr?error=${encodeURIComponent(typeof msg === 'string' ? msg : JSON.stringify(msg))}`)
      }
    }

    run()
    return () => clearInterval(ticker)
  }, [router])

  if (done) return <SuccessOverlay />
  return <PrescriptionSkeleton step={step} />
}
