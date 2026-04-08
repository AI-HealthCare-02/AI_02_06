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
  const [processingIds, setProcessingIds] = useState([]) // 처리 중인 챌린지 ID 목록

  // 추천 챌린지 템플릿 (서버에서 가져올 수도 있음)
  const recommended = [
    { id: 'tpl_1', icon: '🚭', title: '금연 챌린지', desc: '30일 동안 금연해보세요', days: 30, difficulty: '어려움', color: 'bg-red-50', textColor: 'text-red-500' },
    { id: 'tpl_2', icon: '🏃', title: '매일 걷기', desc: '매일 30분씩 걸어보세요', days: 21, difficulty: '보통', color: 'bg-green-50', textColor: 'text-green-500' },
    { id: 'tpl_3', icon: '💊', title: '복약 완료 챌린지', desc: '7일 연속 복약을 완료해보세요', days: 7, difficulty: '쉬움', color: 'bg-blue-50', textColor: 'text-blue-500' },
    { id: 'tpl_4', icon: '🥗', title: '건강한 식단', desc: '21일 동안 균형 잡힌 식사를 해보세요', days: 21, difficulty: '보통', color: 'bg-yellow-50', textColor: 'text-yellow-500' },
  ]

  // 아이콘 매핑 (제목 기반)
  const getIconByTitle = (title) => {
    if (title.includes('금연')) return '🚭'
    if (title.includes('걷기')) return '🏃'
    if (title.includes('복약')) return '💊'
    if (title.includes('식단')) return '🥗'
    return '🎯'
  }

  // 초기 데이터 로드
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 1. 프로필 목록 조회 (본인 프로필 가져오기)
        const profileRes = await api.get('/api/v1/profiles/')
        const profiles = profileRes.data

        if (profiles.length === 0) {
          // 프로필이 없으면 설문조사 페이지로 이동
          router.replace('/survey')
          return
        }

        // SELF 프로필 우선, 없으면 첫 번째 프로필 사용
        const selfProfile = profiles.find(p => p.relation_type === 'SELF') || profiles[0]
        setProfileId(selfProfile.id)

        // 2. 챌린지 목록 조회
        const challengeRes = await api.get('/api/v1/challenges/')
        const challenges = challengeRes.data

        // 진행 중인 챌린지만 필터링 + 아이콘 추가
        const activeChallenges = challenges
          .filter(c => c.challenge_status === 'IN_PROGRESS')
          .map(c => ({
            ...c,
            icon: getIconByTitle(c.title),
            current: c.completed_dates?.length || 0,
          }))

        setOngoing(activeChallenges)
      } catch (err) {
        console.error('데이터 로드 실패:', err)
        // 401 에러는 api 인터셉터에서 처리
        if (err.response?.status !== 401) {
          showError('데이터를 불러오는데 실패했습니다.')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [router])

  // 챌린지 시작하기
  const handleAccept = async (template) => {
    if (!profileId || processingIds.includes(template.id)) return

    setProcessingIds(prev => [...prev, template.id])

    try {
      const response = await api.post('/api/v1/challenges/', {
        profile_id: profileId,
        title: template.title,
        description: template.desc,
        target_days: template.days,
      })

      // 생성된 챌린지를 ongoing에 추가
      const newChallenge = {
        ...response.data,
        icon: template.icon,
        current: 0,
      }
      setOngoing(prev => [...prev, newChallenge])

      // 진행중 탭으로 이동
      setActiveTab('진행중')
    } catch (err) {
      console.error('챌린지 시작 실패:', err)
      showError(err.parsed?.message || '챌린지 시작에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== template.id))
    }
  }

  // 오늘 완료 체크
  const handleCheck = async (challenge) => {
    if (processingIds.includes(challenge.id)) return

    // 오늘 날짜 확인 (이미 체크했는지)
    const today = new Date().toISOString().split('T')[0]
    if (challenge.completed_dates?.includes(today)) {
      showError('오늘은 이미 체크했습니다!')
      return
    }

    setProcessingIds(prev => [...prev, challenge.id])

    try {
      // completed_dates에 오늘 날짜 추가
      const newCompletedDates = [...(challenge.completed_dates || []), today]

      const response = await api.patch(`/api/v1/challenges/${challenge.id}`, {
        completed_dates: newCompletedDates,
        // 목표 달성 시 상태 변경
        challenge_status: newCompletedDates.length >= challenge.target_days ? 'COMPLETED' : 'IN_PROGRESS',
      })

      // 상태 업데이트
      if (response.data.challenge_status === 'COMPLETED') {
        // 완료된 챌린지는 목록에서 제거
        setOngoing(prev => prev.filter(c => c.id !== challenge.id))
        showError('축하합니다! 챌린지를 완료했습니다! 🎉')
      } else {
        // 진행도 업데이트
        setOngoing(prev => prev.map(c =>
          c.id === challenge.id
            ? { ...c, completed_dates: newCompletedDates, current: newCompletedDates.length }
            : c
        ))
      }
    } catch (err) {
      console.error('체크 실패:', err)
      showError(err.parsed?.message || '체크에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== challenge.id))
    }
  }

  // 이미 시작한 챌린지인지 확인
  const isAlreadyStarted = (templateTitle) => {
    return ongoing.some(c => c.title === templateTitle)
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 pb-24">
        <Header title="생활습관 챌린지" subtitle="건강한 습관을 만들어보세요" showBack={true} />
        <div className="max-w-3xl mx-auto px-6 py-6">
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-2xl h-32 w-full" />
            ))}
          </div>
        </div>
        <BottomNav />
      </main>
    )
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
              recommended.map((item) => {
                const started = isAlreadyStarted(item.title)
                const isProcessing = processingIds.includes(item.id)

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
                        disabled={started || isProcessing}
                        className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-colors shadow-sm
                          ${started
                            ? 'bg-gray-100 text-gray-400'
                            : isProcessing
                              ? 'bg-blue-300 text-white cursor-wait'
                              : 'bg-blue-500 text-white hover:bg-blue-600'
                          }`}>
                        {started ? '진행중' : isProcessing ? '처리중...' : '시작하기'}
                      </button>
                    </div>
                  </div>
                )
              })
            ) : (
              <EmptyState title="추천할 챌린지가 없어요" message="잠시 후 다시 확인해 주세요!" />
            )}
          </div>
        )}

        {/* 진행중 챌린지 */}
        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.length > 0 ? (
              ongoing.map((item) => {
                const isProcessing = processingIds.includes(item.id)
                const today = new Date().toISOString().split('T')[0]
                const checkedToday = item.completed_dates?.includes(today)

                return (
                  <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50">
                    <div className="flex items-center gap-4 mb-5">
                      <span className="text-3xl drop-shadow-sm">{item.icon}</span>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-0.5">{item.current}일째 진행 중!</p>
                      </div>
                      <span className="text-blue-500 text-sm font-bold">
                        {item.current}/{item.target_days}일
                      </span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2 mb-4">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-500 shadow-sm"
                        style={{width: `${(item.current/item.target_days)*100}%`}}
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
                            : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                        }`}>
                      {checkedToday ? '오늘 완료!' : isProcessing ? '처리중...' : '오늘 완료 체크'}
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
