'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function ChallengePage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('추천')
  const [accepted, setAccepted] = useState([])
  const [ongoing, setOngoing] = useState([
    { id: 1, icon: '🚭', title: '금연 챌린지', days: 30, current: 3, status: 'IN_PROGRESS' },
  ])

  const recommended = [
    { id: 1, icon: '🚭', title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50' },
    { id: 2, icon: '🏃', title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50' },
    { id: 3, icon: '💊', title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50' },
    { id: 4, icon: '🥗', title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50' },
  ]

  const handleAccept = (challenge) => {
    setAccepted(prev => [...prev, challenge.id])
    alert(`${challenge.title} 챌린지를 시작했어요! 💪`)
  }

  const handleCheck = (id) => {
    setOngoing(prev => prev.map(item =>
      item.id === id
        ? { ...item, current: item.current + 1 }
        : item
    ))
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-20">

      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push('/main')}
          className="text-gray-400 hover:text-black cursor-pointer text-xl">
          ←
        </button>
        <div>
          <h1 className="font-bold">생활습관 챌린지</h1>
          <p className="text-xs text-gray-400">건강한 습관을 만들어보세요</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-6">

        {/* 탭 */}
        <div className="flex gap-6 mb-6 border-b border-gray-200">
          {['추천', '진행중'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-semibold cursor-pointer
                ${activeTab === tab
                  ? 'text-blue-500 border-b-2 border-blue-500'
                  : 'text-gray-400'
                }`}
            >
              {tab}
              {tab === '진행중' && (
                <span className="ml-1 bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {ongoing.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* 추천 챌린지 */}
        {activeTab === '추천' && (
          <div className="space-y-4">
            {recommended.map((item) => (
              <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`${item.color} w-12 h-12 rounded-xl flex items-center justify-center text-2xl`}>
                      {item.icon}
                    </div>
                    <div>
                      <h3 className="font-bold">{item.title}</h3>
                      <p className="text-gray-400 text-xs mt-1">{item.desc}</p>
                      <div className="flex gap-2 mt-2">
                        <span className="bg-gray-100 text-gray-500 text-xs px-2 py-1 rounded-full">{item.days}일</span>
                        <span className={`text-xs px-2 py-1 rounded-full
                          ${item.difficulty === '쉬움' ? 'bg-green-50 text-green-500' :
                            item.difficulty === '보통' ? 'bg-yellow-50 text-yellow-500' :
                            'bg-red-50 text-red-500'}`}>
                          {item.difficulty}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleAccept(item)}
                    disabled={accepted.includes(item.id)}
                    className={`px-4 py-2 rounded-xl text-sm font-semibold cursor-pointer
                      ${accepted.includes(item.id)
                        ? 'bg-gray-100 text-gray-400'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                      }`}>
                    {accepted.includes(item.id) ? '시작됨' : '시작하기'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 진행중 챌린지 */}
        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.map((item) => (
              <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6">
                <div className="flex items-center gap-4 mb-4">
                  <span className="text-2xl">{item.icon}</span>
                  <div className="flex-1">
                    <h3 className="font-bold">{item.title}</h3>
                    <p className="text-gray-400 text-xs">{item.current}일째 진행 중!</p>
                  </div>
                  <span className="text-blue-500 text-sm font-semibold">
                    {item.current}/{item.days}일
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{width: `${(item.current/item.days)*100}%`}}
                  />
                </div>
                <button
                  onClick={() => handleCheck(item.id)}
                  className="w-full border border-gray-200 py-3 rounded-xl text-sm text-gray-500 cursor-pointer hover:bg-gray-50">
                  오늘 완료 체크 ✅
                </button>
              </div>
            ))}
          </div>
        )}

      </div>

      {/* 하단 네비게이션 */}
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
        <button onClick={() => router.push('/main')} className="flex-1 py-4 text-blue-500 text-sm font-semibold">홈</button>
        <button onClick={() => router.push('/mypage')} className="flex-1 py-4 text-gray-400 text-sm">마이페이지</button>
      </div>

    </main>
  )
}