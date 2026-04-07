'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'

export default function ChallengePage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('추천')
  const [accepted, setAccepted] = useState([])
  const [ongoing, setOngoing] = useState([
    { id: 1, abbr: '금연', title: '금연 챌린지', days: 30, current: 3, status: 'IN_PROGRESS', abbrColor: 'bg-red-100 text-red-600' },
  ])

  const recommended = [
    { id: 1, abbr: '금연', title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50', textColor: 'text-red-500', abbrColor: 'bg-red-100 text-red-600' },
    { id: 2, abbr: '걷기', title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50', textColor: 'text-green-500', abbrColor: 'bg-green-100 text-green-600' },
    { id: 3, abbr: '복약', title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50', textColor: 'text-blue-500', abbrColor: 'bg-blue-100 text-blue-600' },
    { id: 4, abbr: '식단', title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50', textColor: 'text-yellow-500', abbrColor: 'bg-yellow-100 text-yellow-600' },
  ]

  const handleAccept = (challenge) => {
    setAccepted(prev => [...prev, challenge.id])
    // 실제 환경에서는 여기서 API 호출 후 ongoing에 추가하는 로직이 들어갑니다.
  }

  const handleCheck = (id) => {
    setOngoing(prev => prev.map(item =>
      item.id === id
        ? { ...item, current: item.current + 1 }
        : item
    ))
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <Header title="생활습관 챌린지" subtitle="건강한 습관을 만들어보세요" showBack={true} />

      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* 탭 */}
        <div className="flex gap-8 mb-8 border-b border-gray-200">
          {['추천', '진행중'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-bold cursor-pointer transition-colors relative
                ${activeTab === tab ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400'} active:scale-[0.98] transition-transform duration-150`}
            >
              {tab}
              {tab === '진행중' && ongoing.length > 0 && (
                <span className="ml-1.5 bg-blue-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                  {ongoing.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* 추천 챌린지 */}
        {activeTab === '추천' && (
          <div className="space-y-4">
            {recommended.length > 0 ? (
              recommended.map((item) => (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50 hover:border-blue-200 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`${item.abbrColor} w-12 h-12 rounded-xl flex items-center justify-center text-xs font-black shadow-sm`}>
                        {item.abbr}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-1 leading-relaxed">{item.desc}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="bg-gray-100 text-gray-500 text-[10px] px-2 py-1 rounded-full font-bold">{item.days}일</span>
                          <span className={`${item.color} ${item.textColor} text-[10px] px-2 py-1 rounded-full font-bold`}>
                            {item.difficulty}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAccept(item)}
                      disabled={accepted.includes(item.id)}
                      className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-colors shadow-sm
                        ${accepted.includes(item.id)
                          ? 'bg-gray-100 text-gray-400'
                          : 'bg-blue-500 text-white hover:bg-blue-600'
                        }`}>
                      {accepted.includes(item.id) ? '시작됨' : '시작하기'}
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="추천할 챌린지가 없어요" message="잠시 후 다시 확인해 주세요!" />
            )}
          </div>
        )}

        {/* 진행중 챌린지 */}
        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.length > 0 ? (
              ongoing.map((item) => (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50">
                  <div className="flex items-center gap-4 mb-5">
                    <div className={`${item.abbrColor} w-12 h-12 rounded-xl flex items-center justify-center text-xs font-black shrink-0`}>{item.abbr}</div>
                    <div className="flex-1">
                      <h3 className="font-bold text-gray-900">{item.title}</h3>
                      <p className="text-gray-400 text-xs mt-0.5">{item.current}일째 진행 중!</p>
                    </div>
                    <span className="text-blue-500 text-sm font-bold">
                      {item.current}/{item.days}일
                    </span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 mb-4">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-500 shadow-sm"
                      style={{width: `${(item.current/item.days)*100}%`}}
                    />
                  </div>
                  <button
                    onClick={() => handleCheck(item.id)}
                    className="w-full bg-gray-50 text-gray-600 py-3.5 rounded-xl text-sm font-bold transition-colors hover:bg-gray-100 active:scale-[0.98]">
                    오늘 완료 체크
                  </button>
                </div>
              ))
            ) : (
              <EmptyState 
                title="진행 중인 챌린지가 없어요" 
                message="새로운 건강 습관을 시작해볼까요?" 
                actionLabel="추천 챌린지 보기"
                onAction={() => setActiveTab('추천')}
              />
            )}
          </div>
        )}
      </div>

      <BottomNav />
    </main>
  )
}
