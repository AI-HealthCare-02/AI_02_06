'use client'
import { useState, useEffect, useRef, Suspense, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api from '@/lib/api'
import { Pill, Flame, Plus, MessageCircle, FileText, Loader2, X, Trash2, Activity } from 'lucide-react'
import ChatModal from '@/components/chat/ChatModal'
import SurveyModal from '@/components/common/SurveyModal'
import { useProfile } from '@/contexts/ProfileContext'
import { useMedication } from '@/contexts/MedicationContext'
import { useChallenge } from '@/contexts/ChallengeContext'
import { useOcrDraft, useOcrEntryNavigator } from '@/contexts/OcrDraftContext'
import TodaySchedule from '@/components/medication/TodaySchedule'

// ── 히어로 배경 이미지 슬라이드쇼 ────────────────────────────────────────────
// 흐름: 3초 타이머 → 다음 이미지 인덱스로 순환 → CSS transition으로 페이드
const HERO_BG_IMAGES = [
  '/hero_bg_1.png',
  '/hero_bg_2.png',
  '/hero_bg_3.png',
]

// 활성 OCR draft 카드 — main 우측하단 floating (챗봇 아이콘 위)
// 사용자가 X 로 카드 전체를 숨길 수 있고 (새로고침 시 다시 표시),
// 각 항목 좌측의 휴지통으로 개별 draft 를 폐기할 수도 있다.
function ActiveDraftsCard({ drafts, onSelect, onDelete }) {
  const [dismissed, setDismissed] = useState(false)
  if (!drafts || drafts.length === 0 || dismissed) return null

  const formatTime = (iso) => {
    const d = new Date(iso)
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  const STATUS_LABEL = {
    pending: '처리 중',
    ready: '확인 대기',
    no_text: '텍스트 없음',
    no_candidates: '인식 실패',
    failed: '오류',
  }

  return (
    <div className="fixed right-6 bottom-44 z-40 w-72 bg-white rounded-2xl border border-gray-200 shadow-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-gray-700" />
          <p className="font-bold text-sm text-gray-900">처방전 ({drafts.length}건)</p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-gray-400 hover:text-gray-700 cursor-pointer"
          aria-label="카드 숨기기"
        >
          <X size={16} />
        </button>
      </div>
      <ul className="space-y-1 max-h-56 overflow-y-auto">
        {drafts.map((d) => (
          <li key={d.draft_id} className="flex items-center gap-1">
            <button
              onClick={() => onDelete(d.draft_id)}
              className="text-gray-300 hover:text-red-500 cursor-pointer flex-shrink-0 p-2 rounded-lg hover:bg-red-50 transition-colors"
              aria-label="처방전 폐기"
            >
              <Trash2 size={14} />
            </button>
            <button
              onClick={() => onSelect(d.draft_id)}
              className="flex-1 flex items-center justify-between gap-3 px-3 py-2 rounded-xl hover:bg-gray-50 cursor-pointer transition-colors text-left"
            >
              <div className="flex items-center gap-2 min-w-0">
                {d.status === 'pending' ? (
                  <Loader2 size={14} className="text-blue-500 animate-spin flex-shrink-0" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                )}
                <span className="text-sm font-bold text-gray-900 truncate">
                  {formatTime(d.created_at)} 업로드
                </span>
              </div>
              <span className="text-xs text-gray-400 flex-shrink-0">
                {STATUS_LABEL[d.status] || d.status}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

// 스켈레톤은 main의 레이아웃을 따름
function MainSkeleton() {
  return (
    <>
      <div className="w-full min-h-[540px] bg-gray-950 animate-pulse" />
      <main className="max-w-7xl mx-auto w-full px-6 py-14 animate-pulse">
        <div className="grid md:grid-cols-12 gap-6">
          <div className="md:col-span-8 bg-gray-100 rounded-[32px] h-[420px]" />
          <div className="md:col-span-4 space-y-6">
            <div className="bg-gray-100 rounded-[32px] h-52" />
            <div className="bg-gray-100 rounded-[32px] h-52" />
          </div>
        </div>
      </main>
    </>
  )
}

// ── 복약 잔여 일수 계산 ────────────────────────────────────────────────────────
// 흐름: end_date 우선 → 없으면 start_date + total_intake_days 로 추정
function getRemainingDays(med) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (med.end_date) {
    const end = new Date(med.end_date)
    end.setHours(0, 0, 0, 0)
    const diff = Math.ceil((end - today) / (1000 * 60 * 60 * 24))
    if (diff > 0) return `${diff}일 남음`
    if (diff === 0) return '오늘 종료'
    return null
  }

  if (med.total_intake_days && med.start_date) {
    const start = new Date(med.start_date)
    start.setHours(0, 0, 0, 0)
    const elapsed = Math.ceil((today - start) / (1000 * 60 * 60 * 24))
    const remaining = med.total_intake_days - elapsed
    if (remaining > 0) return `${remaining}일 남음`
    return null
  }

  return null
}

// ── 메인 페이지 컴포넌트 (Suspense 적용) ──────────────────────────────────────────
export default function MainPage() {
  return (
    <Suspense fallback={<MainSkeleton />}>
      <MainPageContent />
    </Suspense>
  )
}

function MainPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [activeChallenge, setActiveChallenge] = useState(null)
  const [greeting, setGreeting] = useState({ msg: '반가워요', sub: '오늘 하루도 건강하게 시작해봐요' })

  // [추가] 오늘의 증상 관련 상태 관리
  const [todaySymptoms, setTodaySymptoms] = useState([])
  const [todayNote, setTodayNote] = useState('')

  const { selectedProfileId, selectedProfile } = useProfile()
  // 4 Context 가 모든 server state 를 단일 진실로 관리 — 자체 fetch 0
  const { activeMedications: medications } = useMedication()
  const { activeChallenges } = useChallenge()
  const { activeDrafts, removeDraftLocally, refetchDrafts } = useOcrDraft()
  const goToOcrFlow = useOcrEntryNavigator()
  const userName = selectedProfile?.name?.split('(')[0] || '사용자'
  const isInitialLoad = useRef(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [currentBgIndex, setCurrentBgIndex] = useState(0)
  const bgTimerRef = useRef(null)

  // ── 히어로 배경 이미지 슬라이드쇼 ──────────────────────────────────────────
  // 흐름: mount → 3초 타이머 → 인덱스 순환 → 이전 타이머 클린업
  useEffect(() => {
    bgTimerRef.current = setTimeout(() => {
      setCurrentBgIndex((prev) => (prev + 1) % HERO_BG_IMAGES.length)
    }, 3000)
    return () => clearTimeout(bgTimerRef.current)
  }, [currentBgIndex])

  // 설문 팝업 쿼리 파라미터 감지
  useEffect(() => {
    if (searchParams.get('showSurvey') === 'true') {
      setShowSurvey(true)
      router.replace('/main', { scroll: false })
    }
  }, [searchParams, router])

  // Context 들이 자동으로 server state 를 관리 — 페이지는 derived state 만 갱신.
  // [수정] 증상 데이터 fetch 로직 통합
  useEffect(() => {
    if (!selectedProfileId) return

    const fetchData = async () => {
      isInitialLoad.current = false
      setIsLoading(false)

      // 인사말 설정 로직
      const hour = new Date().getHours()
      if (hour < 12) setGreeting({ msg: '좋은 아침이에요', sub: '오늘 하루도 건강하게 시작해봐요' })
      else if (hour < 17) setGreeting({ msg: '좋은 오후예요', sub: '점심 식사 후 약 챙기셨나요?' })
      else setGreeting({ msg: '좋은 저녁이에요', sub: '저녁 복약 시간을 확인해보세요' })

      // [추가] 오늘 증상 데이터 가져오기 (API 호출)
      try {
        const today = new Date().toISOString().split('T')[0]
        const response = await api.get(`/api/v1/daily-logs`, {
          params: {
            profile_id: selectedProfileId,
            data: today
          }
        })
        if (response.data && response.data.length > 0) {
          const latestLog = response.data[0]
          setTodaySymptoms(latestLog.symptoms || [])
          setTodayNote(latestLog.note || '')
        } else {
          setTodaySymptoms([])
          setTodayNote('')
        }
      } catch (error) {
        console.warn('Failed to fetch symptoms:', error)
        setTodaySymptoms([])
        setTodayNote('')
      }
    }

    fetchData()
  }, [selectedProfileId])

  // 진행 중 챌린지에서 랜덤 1개 — activeChallenges 갱신 시 자동 반영
  useEffect(() => {
    if (activeChallenges.length === 0) {
      setActiveChallenge(null)
      return
    }
    const random = activeChallenges[Math.floor(Math.random() * activeChallenges.length)]
    setActiveChallenge(random)
  }, [activeChallenges])

  // main 페이지 진입 시 / 프로필 전환 시 OCR drafts 동기화.
  useEffect(() => {
    if (selectedProfileId) refetchDrafts()
  }, [selectedProfileId, refetchDrafts])

  // window focus 시 drafts 재동기화 (백그라운드에서 다른 탭에서 등록·완료한 draft 반영)
  useEffect(() => {
    if (!selectedProfileId) return
    window.addEventListener('focus', refetchDrafts)
    return () => window.removeEventListener('focus', refetchDrafts)
  }, [selectedProfileId, refetchDrafts])

  // 카드에서 개별 draft 폐기 — 백엔드 DELETE 후 즉시 목록에서 제외.
  const handleDeleteDraft = useCallback(async (draftId) => {
    try {
      await api.delete(`/api/v1/ocr/draft/${draftId}`, {
        params: selectedProfileId ? { profile_id: selectedProfileId } : undefined,
      })
    } catch {
      // ignore
    }
    removeDraftLocally(draftId)
  }, [removeDraftLocally, selectedProfileId])

  if (isLoading) return <MainSkeleton />

  return (
    <div className={`transition-opacity duration-200 ${isRefreshing ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} userName={userName} profileId={selectedProfileId} />}
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={selectedProfileId} />}

      {/* ── 히어로 섹션 (배경 이미지 슬라이드쇼 + 다크 오버레이) ── */}
      <section
        className="relative w-full min-h-[540px] flex items-center justify-center overflow-hidden bg-black"
        style={{
          backgroundImage: `url('${HERO_BG_IMAGES[currentBgIndex]}')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          transition: 'background-image 1s ease-in-out',
        }}
      >
        {/* 다크 오버레이 — 텍스트 가독성 확보 */}
        <div className="absolute inset-0 bg-black/50" />
        {/* 그리드 패턴 */}
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

        <div className="relative z-10 text-center px-6 max-w-3xl mx-auto py-24">
          <p className="text-gray-400 text-sm font-bold mb-5 tracking-[0.2em] uppercase">{greeting.sub}</p>
          <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-8">
            {greeting.msg},<br /><span className="text-gray-400">{userName} 님</span>
          </h1>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button onClick={goToOcrFlow} className="px-8 py-4 bg-white text-black font-bold rounded-full hover:bg-gray-100 transition-all cursor-pointer">처방전 등록하기</button>
            <button onClick={() => setShowChat(true)} className="px-8 py-4 bg-gray-900/80 text-white font-bold rounded-full border border-gray-700 hover:bg-gray-800 transition-all cursor-pointer flex items-center gap-2 justify-center">
              <MessageCircle size={20}/> AI 상담하기
            </button>
          </div>

          {/* 이미지 인디케이터 — 클릭으로 수동 전환 가능 */}
          <div className="flex gap-2 justify-center mt-10">
            {HERO_BG_IMAGES.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setCurrentBgIndex(i)}
                aria-label={`배경 이미지 ${i + 1}`}
                className="py-3 px-1 cursor-pointer flex items-center justify-center"
              >
                <span className={`block h-2 rounded-full transition-all ${currentBgIndex === i ? 'w-8 bg-white' : 'w-2 bg-white/30'}`} />
              </button>
            ))}
          </div>
        </div>
      </section>

      <main className="max-w-7xl mx-auto w-full px-6 py-14">
        <div className="grid md:grid-cols-12 gap-8">
          <div className="md:col-span-8 space-y-8">

            {/* [추가] 오늘의 증상 요약 카드 섹션 */}
            <section className="bg-white rounded-[32px] p-8 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center text-red-500">
                    <Activity size={20} />
                  </div>
                  <h2 className="text-xl font-black text-gray-900">오늘의 증상</h2>
                </div>
                <button
                  onClick={() => router.push('/lifestyle-guide?tab=symptom')}
                  className="text-sm font-bold text-gray-400 hover:text-gray-600 transition-colors"
                >
                  기록하기
                </button>
              </div>

              {todaySymptoms.length > 0 ? (
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    {todaySymptoms.map((s, idx) => (
                      <span key={idx} className="px-4 py-2 bg-gray-50 text-gray-700 rounded-full text-sm font-bold border border-gray-100">
                        {s}
                      </span>
                    ))}
                  </div>
                  {todayNote && (
                    <p className="text-gray-500 text-sm leading-relaxed bg-gray-50/50 p-4 rounded-2xl border border-dashed border-gray-200">
                      "{todayNote}"
                    </p>
                  )}
                </div>
              ) : (
                <div className="py-4 text-center">
                  <p className="text-gray-400 text-sm mb-4">오늘 기록된 증상이 없습니다.</p>
                  <button
                    onClick={() => router.push('/lifestyle-guide?tab=symptom')}
                    className="px-6 py-2 bg-gray-900 text-white text-xs font-bold rounded-full hover:bg-black transition-all"
                  >
                    지금 기록하기
                  </button>
                </div>
              )}
            </section>

            {/* ── 복약 스케줄 ── */}
            <section className="bg-white rounded-[32px] p-8 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-500">
                    <Pill size={20} />
                  </div>
                  <h2 className="text-xl font-black text-gray-900">오늘의 복약 스케줄</h2>
                </div>
              </div>
              <TodaySchedule medications={medications} profileId={selectedProfileId} />
            </section>
          </div>

          <div className="md:col-span-4 space-y-8">
            {/* ── 챌린지 카드 ── */}
            <section className="bg-gray-900 rounded-[32px] p-8 text-white relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform duration-500">
                <Flame size={80} />
              </div>
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-6">
                  <span className="px-3 py-1 bg-white/10 rounded-full text-[10px] font-bold tracking-wider uppercase">Active Challenge</span>
                </div>
                {activeChallenge ? (
                  <>
                    <h3 className="text-2xl font-black mb-2">{activeChallenge.title}</h3>
                    <p className="text-gray-400 text-sm mb-8 leading-relaxed">{activeChallenge.description}</p>
                    <button onClick={() => router.push('/challenge')} className="w-full py-4 bg-white text-black font-bold rounded-2xl hover:bg-gray-100 transition-all">진행 상황 보기</button>
                  </>
                ) : (
                  <>
                    <h3 className="text-2xl font-black mb-2">새로운 도전을<br />시작해보세요</h3>
                    <p className="text-gray-400 text-sm mb-8">건강한 습관을 만드는 가장 쉬운 방법</p>
                    <button onClick={() => router.push('/challenge')} className="w-full py-4 bg-white text-black font-bold rounded-2xl hover:bg-gray-100 transition-all">챌린지 둘러보기</button>
                  </>
                )}
              </div>
            </section>

            {/* ── 복약 관리 카드 ── */}
            <section className="bg-white rounded-[32px] p-8 shadow-sm border border-gray-100">
              <h3 className="text-lg font-black text-gray-900 mb-6">복약 관리</h3>
              <div className="space-y-4">
                {medications.slice(0, 2).map((med) => (
                  <div key={med.medication_id} className="p-4 rounded-2xl bg-gray-50 border border-gray-100">
                    <div className="flex justify-between items-start mb-1">
                      <p className="font-bold text-gray-900 truncate flex-1">{med.medicine_name}</p>
                      <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full ml-2 flex-shrink-0">
                        {getRemainingDays(med)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400">{med.dosage}</p>
                  </div>
                ))}
                <button onClick={() => router.push('/medication')} className="w-full py-4 bg-gray-50 text-gray-900 font-bold rounded-2xl hover:bg-gray-100 transition-all flex items-center justify-center gap-2">
                  <Plus size={18} /> 전체 보기
                </button>
              </div>
            </section>
          </div>
        </div>
      </main>

      <ActiveDraftsCard
        drafts={activeDrafts}
        onSelect={(id) => router.push(`/ocr/result?draft_id=${id}`)}
        onDelete={handleDeleteDraft}
      />
    </div>
  )
}
