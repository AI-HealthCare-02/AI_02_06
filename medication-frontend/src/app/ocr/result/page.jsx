'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import Header from '../../../components/Header'

function ResultSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-32 animate-pulse">
      <div className="h-48 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="flex justify-between items-center mb-8 px-1">
          <div className="h-6 w-32 bg-gray-200 rounded-lg" />
          <div className="h-6 w-20 bg-gray-200 rounded-lg" />
        </div>
        <div className="space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-48 bg-white rounded-3xl border border-gray-100 shadow-sm" />
          ))}
        </div>
        <div className="mt-12 flex gap-4">
          <div className="flex-1 h-16 bg-white border border-gray-200 rounded-2xl" />
          <div className="flex-1 h-16 bg-blue-100 rounded-2xl" />
        </div>
      </div>
    </div>
  )
}

export default function OcrResultPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  
  // 예시 데이터
  const [meds, setMeds] = useState([
    { name: '암로디핀정 5mg', dose: '1정', frequency: '1일 1회', instruction: '식후 30분' },
    { name: '아스피린프로텍트정', dose: '1정', frequency: '1일 1회', instruction: '식후 즉시' },
  ])


  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800)
  }, [])

  if (isLoading) return <ResultSkeleton />

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

        <div className="space-y-4 mb-10">
          {meds.map((med, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-50 animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ animationDelay: `${i * 100}ms` }}>
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-lg text-gray-900">{med.name}</h3>
                <button className="text-gray-300 hover:text-red-400 transition-colors">
                  <Trash2 size={20} />
                </button>
              </div>
              
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-gray-50 p-3 rounded-xl">
                  <p className="text-[10px] text-gray-400 mb-1">1회 복용량</p>
                  <p className="text-sm font-bold text-gray-700">{med.dose}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-xl">
                  <p className="text-[10px] text-gray-400 mb-1">복용 횟수</p>
                  <p className="text-sm font-bold text-gray-700">{med.frequency}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-xl">
                  <p className="text-[10px] text-gray-400 mb-1">복용 방법</p>
                  <p className="text-sm font-bold text-gray-700">{med.instruction}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-3 pb-10">
          <button
            onClick={() => router.push('/ocr')}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
          >
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
