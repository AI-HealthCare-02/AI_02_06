'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OcrResultPage() {
  const router = useRouter()
  const [guide, setGuide] = useState('')

  useEffect(() => {
    const saved = sessionStorage.getItem('ocrGuide')
    if (!saved) {
      router.push('/ocr')
      return
    }
    setGuide(saved)
  }, [])

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-10 py-4 flex items-center gap-4">
        <button onClick={() => router.push('/ocr')} className="text-gray-400 hover:text-black cursor-pointer text-xl">←</button>
        <div>
          <h1 className="font-bold">처방전 인식 결과</h1>
          <p className="text-xs text-gray-400">AI가 생성한 복약 가이드입니다</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-10 py-8 space-y-4">
        <div className="bg-green-50 rounded-2xl p-4 flex items-center gap-3">
          <span className="text-2xl">✅</span>
          <div>
            <p className="font-semibold text-green-700 text-sm">분석 완료!</p>
            <p className="text-green-600 text-xs">복약 가이드가 생성되었습니다.</p>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="font-bold mb-4 pb-3 border-b border-gray-100">복약 가이드</h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{guide}</p>
        </div>

        <div className="flex gap-3 pb-10">
          <button
            onClick={() => router.push('/ocr')}
            className="flex-1 border border-gray-200 py-4 rounded-xl text-gray-400 text-sm cursor-pointer hover:bg-gray-50">
            다시 촬영
          </button>
          <button
            onClick={() => { sessionStorage.removeItem('ocrGuide'); router.push('/main') }}
            className="flex-1 bg-blue-500 text-white py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600">
            확인
          </button>
        </div>
      </div>
    </main>
  )
}
