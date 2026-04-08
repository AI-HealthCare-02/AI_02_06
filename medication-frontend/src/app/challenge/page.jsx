'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { showError } from '../../lib/api'

// SVG 아이콘 컴포넌트
const Icons = {
  NoSmoking: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
      <line x1="7" y1="12" x2="12" y2="12" />
      <line x1="15" y1="12" x2="17" y2="12" />
      <line x1="12" y1="10" x2="12" y2="10.5" />
    </svg>
  ),
  Walking: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="13" cy="4" r="1.5" />
      <path d="M9 8.5l1.5 2L13 9l2 4H9" />
      <path d="M9 14l-1 4" />
      <path d="M14 13l1.5 4" />
      <path d="M8 20h2" />
      <path d="M14 20h2" />
    </svg>
  ),
  Pill: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.5 20H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H20a2 2 0 0 1 2 2v3" />
      <circle cx="17" cy="17" r="5" />
      <path d="M14 17h6" />
    </svg>
  ),
  Salad: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 21h10" />
      <path d="M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z" />
      <path d="M11.38 12a2.4 2.4 0 0 1-.4-4.77 2.4 2.4 0 0 1 3.2-3.19 2.4 2.4 0 0 1 3.47-.63 2.4 2.4 0 0 1 3.37 3.37 2.4 2.4 0 0 1-1.1 3.7 2.51 2.51 0 0 1 .03 1.1" />
      <path d="m13 12 4-4" />
      <path d="M10.9 7.25A3.99 3.99 0 0 0 4 10c0 .73.2 1.41.54 2" />
    </svg>
  ),
  Target: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  ),
}

export default function ChallengePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('추천')
  const [profileId, setProfileId] = useState(null)
  const [ongoing, setOngoing] = useState([])
  const [processingIds, setProcessingIds] = useState([])

  const recommended = [
    { id: 'tpl_1', icon: <Icons.NoSmoking />, title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50', textColor: 'text-red-500', iconColor: 'text-red-400' },
    { id: 'tpl_2', icon: <Icons.Walking />, title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50', textColor: 'text-green-500', iconColor: 'text-green-400' },
    { id: 'tpl_3', icon: <Icons.Pill />, title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50', textColor: 'text-blue-500', iconColor: 'text-blue-400' },
    { id: 'tpl_4', icon: <Icons.Salad />, title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50', textColor: 'text-yellow-500', iconColor: 'text-yellow-400' },
  ]

  const getIconByTitle = (title: string) => {
    if (title.includes('금연')) return <Icons.NoSmoking />
    if (title.includes('걷기')) return <Icons.Walking />
    if (title.includes('복약')) return <Icons.Pill />
    if (title.includes('식단')) return <Icons.Salad />
    return <Icons.Target />
  }

  const isAlreadyStarted = (templateTitle: string) => {
    return ongoing.some((c: any) => c.title === templateTitle)
  }

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
      } catch (err: any) {
        if (err.response?.status !== 401) {
          showError('데이터를 불러오는데 실패했습니다.')
        }
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [router])

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
        showError('축하합니다! 챌린지를 완료했습니다! 🎉')
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
              className={`pb-3 text-sm font-bold cursor-pointer transition-colors relative active:scale-[0.98]
                ${activeTab === tab 
                  ? 'text-gray-900 border-b-2 border-gray-900' 
                  : 'text-gray-400 hover:text-gray-600'}`}
            >
              {tab}
              {tab === '진행중' && ongoing.length > 0 && (
                <span className="ml-1.5 bg-gray-900 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                  {ongoing.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {activeTab === '추천' && (
          <div className="space-y-4">
            {recommended.map((item) => {
              const started = isAlreadyStarted(item.title)
              const isProcessing = processingIds.includes(item.id)
              return (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50 hover:border-blue-200 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`${item.color} ${item.iconColor} w-12 h-12 rounded-xl flex items-center justify-center shadow-sm`}>
                        {item.icon}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-1 leading-relaxed">{item.desc}</p>
                        <div className="flex gap-2 mt-2">
                          <span className="bg-gray-100 text-gray-500 text-[10px] px-2 py-1 rounded-full font-bold">{item.days}일</span>
                          <span className={`${item.color} ${item.textColor} text-[10px] px-2 py-1 rounded-full font-bold`}>{item.difficulty}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAccept(item)}
                      disabled={started || isProcessing}
                      className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-colors shadow-sm
                        ${started 
                          ? 'bg-gray-100 text-gray-400' 
                          : isProcessing 
                            ? 'bg-blue-300 text-white cursor-wait' 
                            : 'bg-blue-500 text-white hover:bg-blue-600'}`}
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
                      <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center text-gray-500">
                        {item.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-0.5">{item.current}일째 진행 중!</p>
                      </div>
                      <span className="text-blue-500 text-sm font-bold">{item.current}/{item.target_days}일</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-4 overflow-hidden">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-500 shadow-sm"
                        style={{ width: `${(item.current / item.target_days) * 100}%` }}
                      />
                    </div>
                    <button
                      onClick={() => handleCheck(item)}
                      disabled={isProcessing || checkedToday}
                      className={`w-full py-3.5 rounded-xl text-sm font-bold transition-colors active:scale-[0.98]
                        ${checkedToday 
                          ? 'bg-green-50 text-green-500' 
                          : isProcessing 
                            ? 'bg-gray-100 text-gray-400 cursor-wait' 
                            : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}
                    >
                      {checkedToday ? '오늘 완료!' : isProcessing ? '처리중...' : '오늘 완료 체크'}
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