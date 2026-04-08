'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { showError } from '../../lib/api'

export default function ChallengePage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('추천')
  const [isLoading, setIsLoading] = useState(true)
  const [profileId, setProfileId] = useState(null)
  const [ongoing, setOngoing] = useState([])
  const [processingIds, setProcessingIds] = useState([]) // 중복 클릭 방지용

  // 챌린지 템플릿
  const recommended = [
    { id: 'tpl_1', icon: '🚭', title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50', textColor: 'text-red-500' },
    { id: 'tpl_2', icon: '🏃', title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50', textColor: 'text-green-500' },
    { id: 'tpl_3', icon: '💊', title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50', textColor: 'text-blue-500' },
    { id: 'tpl_4', icon: '🥗', title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50', textColor: 'text-yellow-500' },
  ]

  // 아이콘 매핑
  const getIconByTitle = (title: string) => {
    if (title.includes('금연')) return '🚭'
    if (title.includes('걷기')) return '🏃'
    if (title.includes('복약')) return '💊'
    if (title.includes('식단')) return '🥗'
    return '🎯'
  }

  // 초기 데이터 로드 (프로필 검증 및 리다이렉트 포함)
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true)
        const profileRes = await api.get('/api/v1/profiles/')
        const profiles = profileRes.data

        if (!profiles || profiles.length === 0) {
          router.replace('/survey')
          return
        }

        const selfProfile = profiles.find((p: any) => p.relation_type === 'SELF') || profiles[0]
        setProfileId(selfProfile.id)

        const challengeRes = await api.get('/api/v1/challenges/')
        const activeChallenges = challengeRes.data
          .filter((c: any) => c.challenge_status === 'IN_PROGRESS')
          .map((c: any) => ({
            ...c,
            icon: getIconByTitle(c.title),
            current: c.completed_dates?.length || 0,
          }))

        setOngoing(activeChallenges)
      } catch (err) {
        showError('데이터를 불러오는데 실패했습니다.')
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [router])

  // 챌린지 시작
  const handleAccept = async (template: any) => {
    if (!profileId || processingIds.includes(template.id)) return
    setProcessingIds(prev => [...prev, template.id])

    try {
      const response = await api.post('/api/v1/challenges/', {
        profile_id: profileId,
        title: template.title,
        description: template.desc,
        target_days: template.days,
      })

      const newChallenge = {
        ...response.data,
        icon: template.icon,
        current: 0,
      }
      setOngoing(prev => [...prev, newChallenge])
      setActiveTab('진행중')
    } catch (err: any) {
      showError(err.parsed?.message || '챌린지 시작에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== template.id))
    }
  }

  // 오늘 완료 체크
  const handleCheck = async (challenge: any) => {
    if (processingIds.includes(challenge.id)) return
    const today = new Date().toISOString().split('T')[0]
    
    if (challenge.completed_dates?.includes(today)) {
      showError('오늘은 이미 체크했습니다!')
      return
    }

    setProcessingIds(prev => [...prev, challenge.id])

    try {
      const newCompletedDates = [...(challenge.completed_dates || []), today]
      const isCompleted = newCompletedDates.length >= challenge.target_days

      const response = await api.patch(`/api/v1/challenges/${challenge.id}`, {
        completed_dates: newCompletedDates,
        challenge_status: isCompleted ? 'COMPLETED' : 'IN_PROGRESS',
      })

      if (response.data.challenge_status === 'COMPLETED') {
        setOngoing(prev => prev.filter(c => c.id !== challenge.id))
        showError('축하합니다! 챌린지를 완료했습니다! 🎉') // 실제로는 성공 토스트지만 showError 유틸을 공용으로 쓰는 경우
      } else {
        setOngoing(prev => prev.map(c =>
          c.id === challenge.id
            ? { ...c, completed_dates: newCompletedDates, current: newCompletedDates.length }
            : c
        ))
      }
    } catch (err: any) {
      showError(err.parsed?.message || '체크에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== challenge.id))
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 pb-24">
        <Header title="생활습관 챌린지" subtitle="건강한 습관을 만들어보세요" showBack={true} />
        <div className="max-w-3xl mx-auto px-6 py-6 space-y-4 animate-pulse">
          {[1, 2, 3].map(i => <div key={i} className="bg-white rounded-2xl h-32 w-full" />)}
        </div>
        <BottomNav />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <Header title="생활습관 챌린지" subtitle="건강한 습관을 만들어보세요" showBack={true} />

      <div className="max-w-3xl mx-auto px-6 py-6">
        <div className="flex gap-8 mb-8 border-b border-gray-200">
          {['추천', '진행중'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-bold cursor-pointer transition-all relative
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

        {activeTab === '추천' && (
          <div className="space-y-4">
            {recommended.map((item) => {
              const started = ongoing.some(c => c.title === item.title)
              const isProcessing = processingIds.includes(item.id)
              return (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50 hover:border-blue-200 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`${item.color} w-12 h-12 rounded-xl flex items-center justify-center text-2xl`}>
                        {item.icon}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-1">{item.desc}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="bg-gray-100 text-gray-500 text-[10px] px-2 py-1 rounded-full font-bold">{item.days}일</span>
                          <span className={`${item.color} ${item.textColor} text-[10px] px-2 py-1 rounded-full font-bold`}>{item.difficulty}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAccept(item)}
                      disabled={started || isProcessing}
                      className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all active:scale-[0.98]
                        ${started ? 'bg-gray-100 text-gray-400' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
                    >
                      {started ? '진행중' : isProcessing ? '처리중...' : '시작하기'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.length > 0 ? (
              ongoing.map((item: any) => {
                const isProcessing = processingIds.includes(item.id)
                const today = new Date().toISOString().split('T')[0]
                const checkedToday = item.completed_dates?.includes(today)
                return (
                  <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50">
                    <div className="flex items-center gap-4 mb-5">
                      <span className="text-3xl">{item.icon}</span>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-0.5">{item.current}일째 진행 중!</p>
                      </div>
                      <span className="text-blue-500 text-sm font-bold">{item.current}/{item.target_days}일</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-4 overflow-hidden">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${(item.current / item.target_days) * 100}%` }}
                      />
                    </div>
                    <button
                      onClick={() => handleCheck(item)}
                      disabled={isProcessing || checkedToday}
                      className={`w-full py-3.5 rounded-xl text-sm font-bold transition-all active:scale-[0.98]
                        ${checkedToday ? 'bg-green-50 text-green-500' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}
                    >
                      {checkedToday ? '오늘 완료! ✅' : isProcessing ? '처리중...' : '오늘 완료 체크'}
                    </button>
                  </div>
                )
              })
            ) : (
              <EmptyState title="진행 중인 챌린지가 없어요" message="새로운 습관을 시작해보세요!" onAction={() => setActiveTab('추천')} actionLabel="추천 챌린지 보기" />
            )}
          </div>
        )}
      </div>
      <BottomNav />
    </main>
  )
}