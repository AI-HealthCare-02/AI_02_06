'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { handleApiError } from '../../lib/api'
import toast from 'react-hot-toast'

export default function ChallengePage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('추천')
  const [isLoading, setIsLoading] = useState(true)
  const [ongoing, setOngoing] = useState([])
  const [profileId, setProfileId] = useState(null)

  const recommended = [
    { id: 'c1', icon: '🚭', title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50', textColor: 'text-red-500' },
    { id: 'c2', icon: '🏃', title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50', textColor: 'text-green-500' },
    { id: 'c3', icon: '💊', title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50', textColor: 'text-blue-500' },
    { id: 'c4', icon: '🥗', title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50', textColor: 'text-yellow-500' },
  ]

  // 초기 데이터 로딩: 프로필 정보 및 진행 중인 챌린지 조회
  useEffect(() => {
    const initData = async () => {
      try {
        setIsLoading(true)
        // 1. 테스트용으로 첫 번째 프로필 가져오기
        const profileRes = await api.get('/api/v1/profiles/')
        if (profileRes.data && profileRes.data.length > 0) {
          const pid = profileRes.data[0].id
          setProfileId(pid)
          
          // 2. 해당 계정의 챌린지 목록 조회
          const challengeRes = await api.get('/api/v1/challenges/')
          setOngoing(challengeRes.data)
        }
      } catch (err) {
        handleApiError(err)
      } finally {
        setIsLoading(false)
      }
    }
    initData()
  }, [])

  // 챌린지 시작 (DB 저장)
  const handleAccept = async (challenge) => {
    if (!profileId) {
      toast.error('프로필 정보를 찾을 수 없습니다.')
      return
    }

    try {
      const today = new Date().toISOString().split('T')[0]
      const newChallengeData = {
        profile_id: profileId,
        title: challenge.title,
        description: challenge.desc,
        target_days: challenge.days,
        started_date: today,
        challenge_status: 'IN_PROGRESS',
        completed_dates: []
      }

      const res = await api.post('/api/v1/challenges/', newChallengeData)
      
      // 상태 업데이트 및 탭 전환
      setOngoing(prev => [res.data, ...prev])
      setActiveTab('진행중')
      toast.success(`${challenge.title} 챌린지를 시작합니다! 💪`)
    } catch (err) {
      handleApiError(err)
    }
  }

  // 오늘 완료 체크 (DB 업데이트)
  const handleCheck = async (challenge) => {
    const today = new Date().toISOString().split('T')[0]
    
    // 이미 오늘 체크했는지 확인
    if (challenge.completed_dates.includes(today)) {
      toast.error('오늘은 이미 완료했습니다! ✅')
      return
    }

    try {
      const updatedDates = [...challenge.completed_dates, today]
      const res = await api.patch(`/api/v1/challenges/${challenge.id}`, {
        completed_dates: updatedDates
      })

      // 로컬 상태 업데이트
      setOngoing(prev => prev.map(item => 
        item.id === challenge.id ? res.data : item
      ))
      toast.success('오늘의 챌린지 성공! 🏆')
    } catch (err) {
      handleApiError(err)
    }
  }

  if (isLoading) {
    return <main className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </main>
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
              className={`pb-3 text-sm font-bold cursor-pointer transition-colors relative active:scale-[0.98] transition-transform duration-150
                ${activeTab === tab ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400'}`}
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
            {recommended.map((item) => {
              const isAlreadyOngoing = ongoing.some(o => o.title === item.title)
              return (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50 hover:border-blue-200 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`${item.color} w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-sm`}>
                        {item.icon}
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
                      disabled={isAlreadyOngoing}
                      className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm active:scale-[0.98] transition-transform duration-150
                        ${isAlreadyOngoing
                          ? 'bg-gray-100 text-gray-400'
                          : 'bg-blue-500 text-white hover:bg-blue-600'
                        }`}>
                      {isAlreadyOngoing ? '진행 중' : '시작하기'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* 진행중 챌린지 */}
        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.length > 0 ? (
              ongoing.map((item) => {
                const today = new Date().toISOString().split('T')[0]
                const isDoneToday = item.completed_dates.includes(today)
                const currentCount = item.completed_dates.length

                return (
                  <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50">
                    <div className="flex items-center gap-4 mb-5">
                      <span className="text-3xl drop-shadow-sm">
                        {recommended.find(r => r.title === item.title)?.icon || '🏆'}
                      </span>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-0.5">{currentCount}일째 성공 중!</p>
                      </div>
                      <span className="text-blue-500 text-sm font-bold">
                        {currentCount}/{item.target_days}일
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-4 overflow-hidden">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-1000 shadow-sm"
                        style={{width: `${Math.min((currentCount/item.target_days)*100, 100)}%`}}
                      />
                    </div>
                    <button
                      onClick={() => handleCheck(item)}
                      disabled={isDoneToday}
                      className={`w-full py-3.5 rounded-xl text-sm font-bold transition-all active:scale-[0.98] duration-150
                        ${isDoneToday 
                          ? 'bg-green-50 text-green-500' 
                          : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}>
                      {isDoneToday ? '오늘 완료! 내일 또 만나요 ✅' : '오늘 완료 체크 ✅'}
                    </button>
                  </div>
                )
              })
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
