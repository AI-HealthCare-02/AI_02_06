'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../../components/Header'
import BottomNav from '../../../components/BottomNav'

export default function OcrResultPage() {
  const router = useRouter()
  
  // 예시 데이터
  const [meds, setMeds] = useState([
    { name: '암로디핀정 5mg', dose: '1정', frequency: '1일 1회', instruction: '식후 30분' },
    { name: '아스피린프로텍트정', dose: '1정', frequency: '1일 1회', instruction: '식후 즉시' },
  ])

  return (
    <main className="min-h-screen bg-gray-50 pb-32">
      <Header title="분석 결과" subtitle="인식된 약품 정보를 확인하세요" showBack={true} />

      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-6 flex justify-between items-center px-1">
          <h2 className="font-bold text-gray-900">검색된 약품 {meds.length}건</h2>
          <button className="text-xs text-blue-500 font-bold hover:underline">+ 직접 추가</button>
        </div>

        <div className="space-y-4 mb-10">
          {meds.map((med, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-50 animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ animationDelay: `${i * 100}ms` }}>
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-lg text-gray-900">{med.name}</h3>
                <button className="text-gray-300 hover:text-red-400 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                  </svg>
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

        {/* 하단 액션 버튼 */}
        <div className="flex gap-3">
          <button
            onClick={() => router.push('/ocr')}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
          >
            다시 촬영
          </button>
          <button
            onClick={() => router.push('/main')}
            className="flex-1 bg-blue-500 text-white py-4 rounded-xl text-sm font-bold shadow-sm hover:bg-blue-600 active:scale-[0.95] transition-all duration-150"
          >
            모두 저장하기
          </button>
        </div>
      </div>

      <BottomNav />
    </main>
  )
}