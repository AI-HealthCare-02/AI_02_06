'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Clock, Utensils, Pill, AlertTriangle, AlertCircle, Ban } from 'lucide-react'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'

export default function MedicationPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('용법')

  const medication = {
    name: '암로디핀정 5mg',
    dose: '1정',
    frequency: '1일 1회',
    instruction: '식후 30분',
    days: 30,
    warnings: [
      '임산부 또는 수유 중인 경우 복용 전 의사와 상담하세요',
      '자몽 주스와 함께 복용하지 마세요',
      '어지러움이 있을 수 있으니 운전 시 주의하세요',
    ],
    sideEffects: [
      '두통', '부종', '어지러움', '홍조', '피로감'
    ],
    interactions: [
      '심바스타틴 - 병용 시 근육 부작용 위험 증가',
      '사이클로스포린 - 혈중 농도 증가 가능',
    ]
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      {/* 공통 헤더 적용 */}
      <Header title={medication.name} subtitle="용법 및 주의사항" showBack={true} />

      {/* 복약 정보 카드 */}
      <div className="max-w-3xl mx-auto px-6 py-6">
        <div className="bg-blue-500 rounded-2xl p-6 text-white mb-6 shadow-sm">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-blue-100 text-xs mb-1 opacity-80">1회 복용량</p>
              <p className="font-bold text-lg">{medication.dose}</p>
            </div>
            <div>
              <p className="text-blue-100 text-xs mb-1 opacity-80">복용 횟수</p>
              <p className="font-bold text-lg">{medication.frequency}</p>
            </div>
            <div>
              <p className="text-blue-100 text-xs mb-1 opacity-80">복용 방법</p>
              <p className="font-bold text-lg">{medication.instruction}</p>
            </div>
          </div>
        </div>

        {/* 탭 */}
        <div className="flex gap-6 mb-6 border-b border-gray-200 overflow-x-auto whitespace-nowrap scrollbar-hide">
          {['용법', '주의사항', '부작용', '상호작용'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-semibold cursor-pointer transition-colors active:scale-[0.98] transition-transform duration-150
                ${activeTab === tab
                  ? 'text-blue-500 border-b-2 border-blue-500'
                  : 'text-gray-400'
                }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* 탭 컨텐츠 영역 (여백 유지) */}
        <div className="space-y-4">
          {/* 용법 */}
          {activeTab === '용법' && (
            <div className="bg-white rounded-2xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="font-bold mb-4">복용 방법</h2>
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center shrink-0">
                    <Clock size={18} className="text-blue-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">복용 시간</p>
                    <p className="text-gray-400 text-xs mt-1">매일 같은 시간에 복용하세요</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center shrink-0">
                    <Utensils size={18} className="text-green-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">{medication.instruction}</p>
                    <p className="text-gray-400 text-xs mt-1">식사와 함께 복용하면 효과적이에요</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-10 h-10 bg-purple-50 rounded-xl flex items-center justify-center shrink-0">
                    <Pill size={18} className="text-purple-500" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">1회 {medication.dose} 복용</p>
                    <p className="text-gray-400 text-xs mt-1">임의로 용량을 변경하지 마세요</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 주의사항 */}
          {activeTab === '주의사항' && (
            <div className="bg-white rounded-2xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="font-bold mb-4">주의사항</h2>
              <div className="space-y-3">
                {medication.warnings.map((w, i) => (
                  <div key={i} className="flex gap-3 p-4 bg-yellow-50 rounded-xl">
                    <AlertTriangle size={16} className="text-yellow-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-600 leading-relaxed">{w}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 부작용 */}
          {activeTab === '부작용' && (
            <div className="bg-white rounded-2xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="font-bold mb-4">주요 부작용</h2>
              <div className="flex flex-wrap gap-2 mb-6">
                {medication.sideEffects.map((s, i) => (
                  <span key={i} className="bg-red-50 text-red-500 px-4 py-2 rounded-full text-sm font-medium">
                    {s}
                  </span>
                ))}
              </div>
              <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                <p className="text-red-600 text-sm font-semibold mb-1 flex items-center gap-1">
                  <AlertCircle size={14} />
                  이런 증상이 나타나면
                </p>
                <p className="text-gray-500 text-xs leading-relaxed">심한 부작용이 나타나면 즉시 복용을 중단하고 의사와 상담하세요</p>
              </div>
            </div>
          )}

          {/* 상호작용 */}
          {activeTab === '상호작용' && (
            <div className="bg-white rounded-2xl shadow-sm p-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <h2 className="font-bold mb-4">약물 상호작용</h2>
              <div className="space-y-3">
                {medication.interactions.map((item, i) => (
                  <div key={i} className="flex gap-3 p-4 bg-orange-50 rounded-xl">
                    <Ban size={16} className="text-orange-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-600 leading-relaxed">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 하단 탭 바 추가 */}
      <BottomNav />
    </main>
  )
}