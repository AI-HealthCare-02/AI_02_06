'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OcrResultPage() {
  const router = useRouter()

  // 가짜 OCR 결과 데이터 (나중에 API 연결)
  const [meds, setMeds] = useState([
    {
      id: 1,
      name: '암로디핀정 5mg',
      dose: '1정',
      instruction: '식후 30분',
      frequency: '1일 1회',
      days: 30,
    },
    {
      id: 2,
      name: '메트포르민정 500mg',
      dose: '1정',
      instruction: '식후 즉시',
      frequency: '1일 2회',
      days: 30,
    },
  ])

  const handleChange = (id, field, value) => {
    setMeds(prev => prev.map(med =>
      med.id === id ? { ...med, [field]: value } : med
    ))
  }

  return (
    <main className="min-h-screen bg-gray-50">

      {/* 상단 헤더 */}
      <div className="bg-white border-b border-gray-200 px-10 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push('/ocr')}
          className="text-gray-400 hover:text-black cursor-pointer text-xl">
          ←
        </button>
        <div>
          <h1 className="font-bold">처방전 인식 결과</h1>
          <p className="text-xs text-gray-400">인식된 정보를 확인하고 수정해주세요</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-10 py-8 space-y-4">

        {/* 인식 완료 배너 */}
        <div className="bg-green-50 rounded-2xl p-4 flex items-center gap-3">
          <span className="text-2xl">✅</span>
          <div>
            <p className="font-semibold text-green-700 text-sm">인식 완료!</p>
            <p className="text-green-600 text-xs">{meds.length}개의 약품 정보를 인식했어요. 내용을 확인해주세요.</p>
          </div>
        </div>

        {/* 약품 목록 */}
        {meds.map((med, i) => (
          <div key={med.id} className="bg-white rounded-2xl shadow-sm p-6">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
              <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded-full">{i + 1}</span>
              <h2 className="font-bold">{med.name}</h2>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-gray-400 text-xs mb-1 block">약품명</label>
                <input
                  value={med.name}
                  onChange={(e) => handleChange(med.id, 'name', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">1회 복용량</label>
                <input
                  value={med.dose}
                  onChange={(e) => handleChange(med.id, 'dose', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">복용 방법</label>
                <input
                  value={med.instruction}
                  onChange={(e) => handleChange(med.id, 'instruction', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">복용 횟수</label>
                <input
                  value={med.frequency}
                  onChange={(e) => handleChange(med.id, 'frequency', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">복용 일수</label>
                <input
                  type="number"
                  value={med.days}
                  onChange={(e) => handleChange(med.id, 'days', e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm"
                />
              </div>
            </div>
          </div>
        ))}

        {/* 버튼 */}
        <div className="flex gap-3 pb-10">
          <button
            onClick={() => router.push('/ocr')}
            className="flex-1 border border-gray-200 py-4 rounded-xl text-gray-400 text-sm cursor-pointer hover:bg-gray-50">
            다시 촬영
          </button>
          <button
            onClick={() => router.push('/main')}
            className="flex-1 bg-blue-500 text-white py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600">
            저장하기
          </button>
        </div>

      </div>
    </main>
  )
}