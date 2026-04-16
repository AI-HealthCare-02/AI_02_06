'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { showError } from '../../lib/api'
import toast from 'react-hot-toast'

// SVG 아이콘 컴포넌트
const Icons = {
  NoSmoking: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
      <line x1="7" y1="12" x2="12" y2="12" />
      <line x1="15" y1="12" x2="17" y2="12" />
    </svg>
  ),
  Walking: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="13" cy="4" r="1.5" />
      <path d="M9 8.5l1.5 2L13 9l2 4H9" />
      <path d="M9 14l-1 4" />
      <path d="M14 13l1.5 4" />
    </svg>
  ),
  Pill: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="m10.5 20.5-8-8a5 5 0 1 1 7.07-7.07l8 8a5 5 0 1 1-7.07 7.07Z" />
      <line x1="8.5" y1="8.5" x2="15.5" y2="15.5" />
    </svg>
  ),
  Salad: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 21h10" />
      <path d="M12 21a9 9 0 0 0 9-9H3a9 9 0 0 0 9 9Z" />
      <path d="M11.38 12a2.4 2.4 0 0 1-.4-4.77 2.4 2.4 0 0 1 3.2-3.19 2.4 2.4 0 0 1 3.47-.63 2.4 2.4 0 0 1 3.37 3.37 2.4 2.4 0 0 1-1.1 3.7" />
      <path d="m13 12 4-4" />
    </svg>
  ),
  Water: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2C6 9 4 13 4 16a8 8 0 0 0 16 0c0-3-2-7-8-14Z" />
    </svg>
  ),
  Moon: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  ),
  Heart: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
    </svg>
  ),
  Activity: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  Coffee: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 8h1a4 4 0 1 1 0 8h-1" />
      <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
      <line x1="6" y1="2" x2="6" y2="4" />
      <line x1="10" y1="2" x2="10" y2="4" />
      <line x1="14" y1="2" x2="14" y2="4" />
    </svg>
  ),
  Stretch: ({ className = "w-6 h-6" }) => (
    <svg viewBox="0 0 24 24" fill="none" className={className} stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="5" r="1" />
      <path d="M9 20l3-6 3 6" />
      <path d="M6 8l6 4 6-4" />
      <path d="M12 12v3" />
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

// 난이도 설정 모달
function DifficultyModal({ template, onConfirm, onCancel }) {
  const [selected, setSelected] = useState(template.difficulty || '보통')

  const options = [
    { value: '쉬움', label: '쉬움', desc: '가볍게 시작하고 싶어요', color: 'border-blue-300 bg-blue-50 text-blue-600' },
    { value: '보통', label: '보통', desc: '적당한 도전을 원해요', color: 'border-green-300 bg-green-50 text-green-600' },
    { value: '어려움', label: '어려움', desc: '강한 의지로 도전해요', color: 'border-red-300 bg-red-50 text-red-600' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 px-4 pb-6">
      <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-5">
        <div>
          <p className="text-xs text-gray-400 font-bold mb-1">챌린지 시작</p>
          <h3 className="font-black text-gray-900 text-lg">{template.title}</h3>
          <p className="text-gray-400 text-sm mt-1">{template.desc}</p>
        </div>

        <div>
          <p className="text-xs font-bold text-gray-500 mb-3">난이도를 선택해주세요</p>
          <div className="space-y-2">
            {options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setSelected(opt.value)}
                className={`w-full flex items-center gap-3 p-3.5 rounded-xl border-2 transition-all cursor-pointer text-left ${
                  selected === opt.value ? opt.color : 'border-gray-100 bg-gray-50 text-gray-500'
                }`}
              >
                <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  selected === opt.value ? 'border-current' : 'border-gray-300'
                }`}>
                  {selected === opt.value && <div className="w-2 h-2 rounded-full bg-current" />}
                </div>
                <div>
                  <p className="text-sm font-bold">{opt.label}</p>
                  <p className="text-xs opacity-70">{opt.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-gray-500 bg-gray-100 cursor-pointer hover:bg-gray-200 transition-colors"
          >
            취소
          </button>
          <button
            onClick={() => onConfirm(selected)}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-white bg-blue-500 cursor-pointer hover:bg-blue-600 transition-colors"
          >
            시작하기
          </button>
        </div>
      </div>
    </div>
  )
}

const DIFFICULTY_STYLE = {
  '쉬움':   { bg: 'bg-blue-50',   text: 'text-blue-500' },
  '보통':   { bg: 'bg-green-50',  text: 'text-green-500' },
  '어려움': { bg: 'bg-red-50',    text: 'text-red-500' },
}

const TEMPLATES = [
  {
    id: 'tpl_1',
    icon: <Icons.NoSmoking />,
    title: '금연 챌린지',
    desc: '담배 없이 30일을 버텨보세요. 폐 건강이 눈에 띄게 좋아집니다.',
    days: 30,
    difficulty: '어려움',
    color: 'bg-red-50',
    textColor: 'text-red-500',
    iconColor: 'text-red-400',
  },
  {
    id: 'tpl_2',
    icon: <Icons.Walking />,
    title: '매일 30분 걷기',
    desc: '가볍게 걷는 것만으로도 심혈관 건강이 개선됩니다.',
    days: 21,
    difficulty: '보통',
    color: 'bg-green-50',
    textColor: 'text-green-500',
    iconColor: 'text-green-400',
  },
  {
    id: 'tpl_3',
    icon: <Icons.Pill />,
    title: '복약 완료 챌린지',
    desc: '7일 연속 빠짐없이 약을 챙겨보세요.',
    days: 7,
    difficulty: '쉬움',
    color: 'bg-blue-50',
    textColor: 'text-blue-500',
    iconColor: 'text-blue-400',
  },
  {
    id: 'tpl_4',
    icon: <Icons.Salad />,
    title: '균형 잡힌 식단',
    desc: '21일 동안 채소와 단백질 위주의 식사를 해보세요.',
    days: 21,
    difficulty: '보통',
    color: 'bg-yellow-50',
    textColor: 'text-yellow-500',
    iconColor: 'text-yellow-400',
  },
  {
    id: 'tpl_5',
    icon: <Icons.Water />,
    title: '하루 2L 물 마시기',
    desc: '충분한 수분 섭취로 신진대사를 개선해보세요.',
    days: 14,
    difficulty: '쉬움',
    color: 'bg-cyan-50',
    textColor: 'text-cyan-500',
    iconColor: 'text-cyan-400',
  },
  {
    id: 'tpl_6',
    icon: <Icons.Moon />,
    title: '규칙적인 수면',
    desc: '매일 같은 시간에 자고 일어나 수면 사이클을 잡아보세요.',
    days: 14,
    difficulty: '보통',
    color: 'bg-indigo-50',
    textColor: 'text-indigo-500',
    iconColor: 'text-indigo-400',
  },
  {
    id: 'tpl_7',
    icon: <Icons.Heart />,
    title: '혈압 매일 체크',
    desc: '아침저녁으로 혈압을 측정하고 기록하는 습관을 만들어보세요.',
    days: 30,
    difficulty: '쉬움',
    color: 'bg-pink-50',
    textColor: 'text-pink-500',
    iconColor: 'text-pink-400',
  },
  {
    id: 'tpl_8',
    icon: <Icons.Activity />,
    title: '혈당 관리 챌린지',
    desc: '식후 혈당 측정과 식단 조절로 혈당 수치를 안정시켜보세요.',
    days: 30,
    difficulty: '어려움',
    color: 'bg-orange-50',
    textColor: 'text-orange-500',
    iconColor: 'text-orange-400',
  },
  {
    id: 'tpl_9',
    icon: <Icons.Coffee />,
    title: '카페인 줄이기',
    desc: '하루 커피를 1잔으로 줄이고 대신 물이나 허브차를 마셔보세요.',
    days: 21,
    difficulty: '보통',
    color: 'bg-amber-50',
    textColor: 'text-amber-600',
    iconColor: 'text-amber-500',
  },
  {
    id: 'tpl_10',
    icon: <Icons.Stretch />,
    title: '아침 스트레칭',
    desc: '매일 아침 10분 스트레칭으로 하루를 상쾌하게 시작해보세요.',
    days: 14,
    difficulty: '쉬움',
    color: 'bg-purple-50',
    textColor: 'text-purple-500',
    iconColor: 'text-purple-400',
  },
]

export default function ChallengePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('추천')
  const [profileId, setProfileId] = useState(null)
  const [ongoing, setOngoing] = useState([])
  const [completed, setCompleted] = useState([])
  const [processingIds, setProcessingIds] = useState([])
  const [difficultyTarget, setDifficultyTarget] = useState(null) // 난이도 모달용

  const getIconByTitle = (title) => {
    if (title.includes('금연')) return <Icons.NoSmoking />
    if (title.includes('걷기')) return <Icons.Walking />
    if (title.includes('복약')) return <Icons.Pill />
    if (title.includes('식단')) return <Icons.Salad />
    if (title.includes('물')) return <Icons.Water />
    if (title.includes('수면')) return <Icons.Moon />
    if (title.includes('혈압')) return <Icons.Heart />
    if (title.includes('혈당')) return <Icons.Activity />
    if (title.includes('카페인')) return <Icons.Coffee />
    if (title.includes('스트레칭')) return <Icons.Stretch />
    return <Icons.Target />
  }

  const isAlreadyStarted = (templateTitle) => {
    return ongoing.some((c) => c.title === templateTitle)
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true)
        const profileRes = await api.get('/api/v1/profiles')
        const profiles = profileRes.data

        if (!profiles || profiles.length === 0) {
          router.replace('/survey')
          return
        }

        const selfProfile = profiles.find((p) => p.relation_type === 'SELF') || profiles[0]
        setProfileId(selfProfile.id)

        const challengeRes = await api.get('/api/v1/challenges')

        const activeChallenges = challengeRes.data
          .filter((c) => c.challenge_status === 'IN_PROGRESS')
          .map((c) => ({
            ...c,
            icon: getIconByTitle(c.title),
            current: c.completed_dates?.length || 0,
          }))

        const completedChallenges = challengeRes.data
          .filter((c) => c.challenge_status === 'COMPLETED')
          .map((c) => ({
            ...c,
            icon: getIconByTitle(c.title),
          }))

        setOngoing(activeChallenges)
        setCompleted(completedChallenges)
      } catch (err) {
        if (err.response?.status !== 401) {
          showError('데이터를 불러오는데 실패했습니다.')
        }
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [router])

  const handleAccept = (template) => {
    if (!profileId || processingIds.includes(template.id)) return
    setDifficultyTarget(template)
  }

  const handleConfirmStart = async (difficulty) => {
    const template = difficultyTarget
    setDifficultyTarget(null)
    setProcessingIds(prev => [...prev, template.id])

    try {
      const response = await api.post('/api/v1/challenges', {
        profile_id: profileId,
        title: template.title,
        description: template.desc,
        target_days: template.days,
        difficulty,
      })

      const newChallenge = {
        ...response.data,
        icon: template.icon,
        current: 0,
      }
      setOngoing(prev => [...prev, newChallenge])
      toast.success('챌린지가 시작되었습니다!')
      setActiveTab('진행중')
    } catch (err) {
      showError(err.parsed?.message || '챌린지 시작에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== template.id))
    }
  }

  const handleCheck = async (challenge) => {
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
        setCompleted(prev => [{ ...response.data, icon: challenge.icon }, ...prev])
        toast.success('챌린지를 완료했습니다! 수고하셨어요.')
        setActiveTab('완료')
      } else {
        setOngoing(prev => prev.map(c =>
          c.id === challenge.id
            ? { ...c, completed_dates: newCompletedDates, current: newCompletedDates.length }
            : c
        ))
      }
    } catch (err) {
      showError(err.parsed?.message || '체크에 실패했습니다.')
    } finally {
      setProcessingIds(prev => prev.filter(id => id !== challenge.id))
    }
  }

  const handleAbandon = async (challenge) => {
    if (!confirm(`'${challenge.title}' 챌린지를 포기하시겠습니까?`)) return
    try {
      await api.delete(`/api/v1/challenges/${challenge.id}`)
      setOngoing(prev => prev.filter(c => c.id !== challenge.id))
      toast.success('챌린지가 삭제되었습니다.')
    } catch (err) {
      showError(err.parsed?.message || '삭제에 실패했습니다.')
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

      {difficultyTarget && (
        <DifficultyModal
          template={difficultyTarget}
          onConfirm={handleConfirmStart}
          onCancel={() => setDifficultyTarget(null)}
        />
      )}

      <div className="max-w-3xl mx-auto px-6 py-6">
        <div className="flex gap-8 mb-8 border-b border-gray-200">
          {['추천', '진행중', '완료'].map((tab) => (
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
              {tab === '완료' && completed.length > 0 && (
                <span className="ml-1.5 bg-green-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                  {completed.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* 추천 탭 */}
        {activeTab === '추천' && (
          <div className="space-y-3">
            {TEMPLATES.map((item) => {
              const started = isAlreadyStarted(item.title)
              const isProcessing = processingIds.includes(item.id)
              const diffStyle = DIFFICULTY_STYLE[item.difficulty] || DIFFICULTY_STYLE['보통']
              return (
                <div key={item.id} className="bg-white rounded-2xl shadow-sm p-5 border border-gray-50 hover:border-blue-100 transition-all">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className={`${item.color} ${item.iconColor} w-11 h-11 rounded-xl flex items-center justify-center shrink-0`}>
                        {item.icon}
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-bold text-gray-900 text-sm">{item.title}</h3>
                        <p className="text-gray-400 text-xs mt-0.5 leading-relaxed line-clamp-1">{item.desc}</p>
                        <div className="flex gap-1.5 mt-1.5">
                          <span className="bg-gray-100 text-gray-500 text-[10px] px-2 py-0.5 rounded-full font-bold">{item.days}일</span>
                          <span className={`${diffStyle.bg} ${diffStyle.text} text-[10px] px-2 py-0.5 rounded-full font-bold`}>{item.difficulty}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAccept(item)}
                      disabled={started || isProcessing}
                      className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors shrink-0
                        ${started
                          ? 'bg-gray-100 text-gray-400 cursor-default'
                          : isProcessing
                            ? 'bg-blue-300 text-white cursor-wait'
                            : 'bg-blue-500 text-white hover:bg-blue-600 cursor-pointer'}`}
                    >
                      {started ? '진행중' : isProcessing ? '처리중...' : '시작하기'}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* 진행중 탭 */}
        {activeTab === '진행중' && (
          <div className="space-y-4">
            {ongoing.length > 0 ? (
              ongoing.map((item) => {
                const isProcessing = processingIds.includes(item.id)
                const today = new Date().toISOString().split('T')[0]
                const checkedToday = item.completed_dates?.includes(today)
                const diffStyle = item.difficulty ? (DIFFICULTY_STYLE[item.difficulty] || DIFFICULTY_STYLE['보통']) : null
                return (
                  <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50">
                    <div className="flex items-center gap-4 mb-5">
                      <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center text-gray-500">
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-bold text-gray-900">{item.title}</h3>
                          {diffStyle && (
                            <span className={`${diffStyle.bg} ${diffStyle.text} text-[10px] px-2 py-0.5 rounded-full font-bold`}>
                              {item.difficulty}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-400 text-xs mt-0.5">
                          {item.current}일째 진행 중
                          {item.started_date && <span className="ml-1">· {item.started_date} 시작</span>}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-blue-500 text-sm font-bold">{item.current}/{item.target_days}일</span>
                        <button
                          onClick={() => handleAbandon(item)}
                          className="w-7 h-7 flex items-center justify-center rounded-full text-gray-300 hover:text-red-400 hover:bg-red-50 transition-all cursor-pointer"
                          title="챌린지 포기"
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                          </svg>
                        </button>
                      </div>
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
                            : 'bg-gray-50 text-gray-600 hover:bg-gray-100 cursor-pointer'}`}
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

        {/* 완료 탭 */}
        {activeTab === '완료' && (
          <div className="space-y-4">
            {completed.length > 0 ? (
              completed.map((item) => {
                const diffStyle = item.difficulty ? (DIFFICULTY_STYLE[item.difficulty] || DIFFICULTY_STYLE['보통']) : null
                return (
                  <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6 border border-gray-50 opacity-80">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center text-green-400">
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-bold text-gray-900">{item.title}</h3>
                          {diffStyle && (
                            <span className={`${diffStyle.bg} ${diffStyle.text} text-[10px] px-2 py-0.5 rounded-full font-bold`}>
                              {item.difficulty}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-400 text-xs mt-0.5">
                          {item.target_days}일 달성
                          {item.started_date && <span className="ml-1">· {item.started_date} 시작</span>}
                        </p>
                      </div>
                      <span className="bg-green-50 text-green-500 text-xs font-bold px-3 py-1.5 rounded-full border border-green-100 shrink-0">
                        완료
                      </span>
                    </div>
                  </div>
                )
              })
            ) : (
              <EmptyState title="완료한 챌린지가 없어요" message="도전을 시작하고 목표를 달성해보세요!" onAction={() => setActiveTab('추천')} actionLabel="추천 챌린지 보기" />
            )}
          </div>
        )}
      </div>
      <BottomNav />
    </main>
  )
}
