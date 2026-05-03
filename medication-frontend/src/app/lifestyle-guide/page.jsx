'use client'
// [신규 파일] 생활습관 가이드 페이지 (/lifestyle-guide)
// - AI가 생성한 5개 카테고리(약물상호작용/수면/식단/운동/증상) 가이드를 탭으로 표시
// - 이력 날짜 칩으로 과거 가이드 조회 가능 (과거 가이드는 챌린지 버튼 비활성화)
// - 각 탭에 연결된 챌린지를 하단 배너로 표시 (3-상태: 시작 전/진행중/완료)
// - 증상 탭에는 오늘의 일일 증상 로그 입력 폼 포함
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import BottomNav from '@/components/layout/BottomNav'
import EmptyState from '@/components/common/EmptyState'
import api, { showError } from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'
import { useLifestyleGuide } from '@/contexts/LifestyleGuideContext'
import { useChallenge, useChallengeStart, useChallengeCheck } from '@/contexts/ChallengeContext'
import { usePrescriptionGroup } from '@/contexts/PrescriptionGroupContext'
import StartChallengeModal from '@/components/common/StartChallengeModal'
import { useConfirm } from '@/components/common/ConfirmDialog'
import PrescriptionPickerModal from '@/components/lifestyle/PrescriptionPickerModal'
import SymptomLogForm from '@/components/lifestyle/SymptomLogForm'
import toast from 'react-hot-toast'
import { AlertTriangle, Moon, Utensils, Dumbbell, Stethoscope } from 'lucide-react'


const MAX_REVEALED_CHALLENGES = 15

const TABS = [
  {
    key: 'interaction',
    label: '약물 상호작용',
    icon: <AlertTriangle size={16} />,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    activeBorder: 'border-red-500',
  },
  {
    key: 'sleep',
    label: '수면·생체리듬',
    icon: <Moon size={16} />,
    color: 'text-indigo-500',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    activeBorder: 'border-indigo-500',
  },
  {
    key: 'diet',
    label: '식단·수분',
    icon: <Utensils size={16} />,
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-200',
    activeBorder: 'border-green-500',
  },
  {
    key: 'exercise',
    label: '운동',
    icon: <Dumbbell size={16} />,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    activeBorder: 'border-blue-500',
  },
  {
    key: 'symptom',
    label: '증상 트래킹',
    icon: <Stethoscope size={16} />,
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    activeBorder: 'border-orange-500',
  },
]

const DIFFICULTY_STYLE = {
  '쉬움': { bg: 'bg-blue-50', text: 'text-blue-500' },
  '보통': { bg: 'bg-green-50', text: 'text-green-500' },
  '어려움': { bg: 'bg-red-50', text: 'text-red-500' },
}

function formatDate(isoStr) {
  const d = new Date(isoStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatFullDateTime(isoStr) {
  const d = new Date(isoStr)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const HH = String(d.getHours()).padStart(2, '0')
  const MM = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}.${mm}.${dd} ${HH}:${MM}`
}

function summarizePrescribedRange(snapshot) {
  if (!Array.isArray(snapshot) || snapshot.length === 0) return null
  const dates = snapshot
    .map((m) => (typeof m === 'object' ? m.dispensed_date || m.start_date : null))
    .filter(Boolean)
    .sort()
  if (dates.length === 0) return null
  const first = dates[0].slice(0, 10).replace(/-/g, '.')
  const last = dates[dates.length - 1].slice(0, 10).replace(/-/g, '.')
  return first === last ? first : `${first} ~ ${last}`
}

// ── 챌린지 배너 컴포넌트 ────────────────────────────────────────────────────────
function ChallengeBanner({ challenge, isViewingHistory }) {
  const router = useRouter()
  const { isStarting, startTarget, requestStart } = useChallengeStart()
  const { checkingId, checkToday } = useChallengeCheck()

  if (!challenge) return null

  const isStartingThis = isStarting && startTarget?.id === challenge.id
  const isChecking = checkingId === challenge.id
  const isProcessing = isStartingThis || isChecking

  const today = new Date().toISOString().split('T')[0]
  const checkedToday = challenge.completed_dates?.some(
    (d) => (typeof d === 'string' ? d : d.toISOString?.().split('T')[0]) === today
  )

  if (challenge.challenge_status === 'COMPLETED') {
    return (
      <div className="fixed bottom-20 left-0 w-full px-4 z-40 pointer-events-none">
        <div className="max-w-3xl mx-auto bg-green-50 border border-green-200 rounded-2xl px-4 py-3 flex items-center justify-between shadow-lg">
          <div className="min-w-0">
            <p className="text-[10px] font-bold text-green-400 uppercase tracking-wide">챌린지 완료</p>
            <p className="text-sm font-bold text-green-700 truncate">{challenge.title}</p>
          </div>
          <span className="bg-green-500 text-white text-xs font-bold px-3 py-1.5 rounded-full shrink-0 ml-3">완료</span>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-20 left-0 w-full px-4 z-40">
      <div className="max-w-3xl mx-auto bg-white border border-gray-200 rounded-2xl px-4 py-3 flex items-center justify-between shadow-lg">
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide">이 가이드 관련 챌린지</p>
          <p className="text-sm font-bold text-gray-900 truncate">{challenge.title}</p>
          {challenge.target_days && (
            <p className="text-xs text-gray-400">
              {challenge.completed_dates?.length || 0}/{challenge.target_days}일
            </p>
          )}
        </div>

        {isViewingHistory ? (
          <span className="text-xs text-gray-400 shrink-0 ml-3">과거 가이드</span>
        ) : !challenge.is_active ? (
          <button
            onClick={() => requestStart(challenge)}
            disabled={isProcessing}
            className={`ml-3 px-4 py-2 rounded-xl text-xs font-bold shrink-0 transition-colors cursor-pointer ${
              isProcessing ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-gray-900 text-white hover:bg-gray-800 active:scale-95'
            }`}
          >
            {isProcessing && startTarget?.id === challenge.id ? '처리중...' : '시작하기'}
          </button>
        ) : checkedToday ? (
          <div className="flex items-center gap-2 ml-3 shrink-0">
            <span className="bg-green-50 text-green-500 text-xs font-bold px-3 py-2 rounded-xl">
              오늘 완료!
            </span>
            <button
              onClick={() => router.push('/challenge')}
              className="text-xs font-bold text-gray-400 hover:text-gray-700 px-2 py-2 rounded-xl hover:bg-gray-100 transition-colors cursor-pointer"
              title="챌린지 페이지에서 보기"
            >
              →
            </button>
          </div>
        ) : (
          <button
            onClick={() => checkToday(challenge)}
            disabled={isProcessing}
            className={`ml-3 px-3 py-2 rounded-xl text-xs font-bold shrink-0 transition-colors cursor-pointer ${
              isProcessing ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {isProcessing ? '처리중...' : '오늘 완료 체크'}
          </button>
        )}
      </div>
    </div>
  )
}

// ── 메인 페이지 ────────────────────────────────────────────────────────────────
export default function LifestyleGuidePage() {
  const router = useRouter()
  const confirm = useConfirm()
  const { selectedProfileId: profileId } = useProfile()
  const {
    guides,
    latestGuide,
    isLoading: guidesLoading,
    generateGuide,
    deleteGuide,
    revealMoreChallenges,
  } = useLifestyleGuide()
  const { challengesByGuide } = useChallenge()
  const { groups: prescriptionGroups, isLoading: groupsLoading } = usePrescriptionGroup()
  const { startTarget, isStarting, requestStart, cancelStart, confirmStart } = useChallengeStart()
  const { checkingId, checkToday } = useChallengeCheck()

  const [isGenerating, setIsGenerating] = useState(false)
  const [isPickerOpen, setIsPickerOpen] = useState(false)
  const [isRevealing, setIsRevealing] = useState(false)
  const [selectedGuide, setSelectedGuide] = useState(null)
  const [userPickedGuideId, setUserPickedGuideId] = useState(null)
  const [activeTab, setActiveTab] = useState('interaction')

  // ── 오늘의 증상 상태 ──
  const [todaySymptoms, setTodaySymptoms] = useState([])
  const [todayNote, setTodayNote] = useState('')
  const [symptomsLoading, setSymptomsLoading] = useState(false)

  const chipScrollRef = useRef(null)
  const isLoading = guidesLoading

  // ── 오늘의 증상 fetch ──
  // GET /api/v1/daily-logs?profile_id=...&days=1
  // 응답: list[DailySymptomLogResponse]
  // 필드: { id, profile_id, log_date, symptoms: string[], note: string|null, created_at }
  // 후속 정정: 다른 페이지/컴포넌트와 동일하게 axios 기반 `api` client 사용 (auth
  // 헤더 자동 주입 + 일관된 에러 처리). 직접 fetch 제거.
  const fetchTodaySymptoms = async () => {
    if (!profileId) return
    const today = new Date().toISOString().split('T')[0]
    setSymptomsLoading(true)
    try {
      const res = await api.get('/api/v1/daily-logs', {
        params: { profile_id: profileId, days: 1 },
      })
      const data = res.data || [] // list[DailySymptomLogResponse]
      // days=1 이지만 혹시 어제 것도 포함될 수 있으니 오늘 날짜로 한 번 더 필터
      const todayLog = data.find((log) => log.log_date === today)
      setTodaySymptoms(todayLog?.symptoms ?? [])
      setTodayNote(todayLog?.note ?? '')
    } catch {
      // 조용히 실패 — 카드 빈 상태로 표시
    } finally {
      setSymptomsLoading(false)
    }
  }

  // 페이지 마운트 시 조회
  useEffect(() => {
    fetchTodaySymptoms()
  }, [profileId])

  // 증상 탭 진입 시 재조회
  useEffect(() => {
    if (activeTab === 'symptom') {
      fetchTodaySymptoms()
    }
  }, [activeTab])

  // ── guideChallenges ──
  const guideChallenges = (selectedGuide ? challengesByGuide(selectedGuide.id) : [])
    .slice()
    .sort((a, b) => {
      const da = a.target_days || 0
      const db = b.target_days || 0
      if (da !== db) return da - db
      const ta = a.title || ''
      const tb = b.title || ''
      const cmp = ta.localeCompare(tb, 'ko')
      if (cmp !== 0) return cmp
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0
    })
  const isLoadingChallenges = false

  const firstReadyGuide = guides.find(g => g.status === 'ready') || null
  const isViewingHistory =
    !!selectedGuide && !!firstReadyGuide && selectedGuide.id !== firstReadyGuide.id

  // ── selectedGuide 자동 보정 ──
  useEffect(() => {
    if (userPickedGuideId) {
      const picked = guides.find(g => g.id === userPickedGuideId && g.status === 'ready')
      if (picked) {
        if (picked !== selectedGuide) setSelectedGuide(picked)
        return
      }
      setUserPickedGuideId(null)
      return
    }

    if (latestGuide && latestGuide.status === 'ready') {
      if (selectedGuide?.id !== latestGuide.id || selectedGuide !== latestGuide) {
        setSelectedGuide(latestGuide)
      }
      return
    }

    if (guides.length > 0) {
      const firstReady = guides.find(g => g.status === 'ready')
      setSelectedGuide(firstReady || null)
    } else {
      setSelectedGuide(null)
    }
  }, [latestGuide, guides, selectedGuide, userPickedGuideId])

  const eligibleGroups = (prescriptionGroups || []).filter((g) => g.has_active_medication)
  const hasEligibleGroup = eligibleGroups.length > 0

  // ── 새 가이드 버튼 클릭 ──
  const handleClickNewGuide = () => {
    if (!profileId) {
      showError('프로필을 먼저 선택해주세요.')
      return
    }
    if (isGenerating) return
    if (groupsLoading) return
    if (!hasEligibleGroup) {
      showError('처방전이 등록되어야 맞춤 가이드 생성이 가능합니다.')
      router.push('/ocr')
      return
    }
    setIsPickerOpen(true)
  }

  // ── 가이드 생성 ──
  const handleConfirmPickGroup = async (prescriptionGroupId) => {
    setIsPickerOpen(false)
    if (isGenerating) return
    setIsGenerating(true)
    setUserPickedGuideId(null)
    const abortController = new AbortController()
    try {
      const result = await generateGuide(profileId, prescriptionGroupId, abortController.signal)
      if (!result) return
      if (result.deduped) {
        toast.success('동일 처방전 + 건강정보 가이드가 이미 있어 그대로 보여드려요.')
      } else {
        toast.success('새 가이드가 생성되었습니다!')
      }
    } catch (err) {
      const detail = err.response?.data?.detail
      if (err.response?.status === 409 && detail?.code === 'NO_ACTIVE_MEDICATIONS') {
        showError(detail.message || '이 처방전엔 복용 중인 약이 없어 가이드를 만들 수 없어요.')
        router.push(detail.redirect_to || '/medication')
        return
      }
      showError(
        err.parsed?.message ||
          err.message ||
          '가이드 생성에 실패했습니다. 잠시 후 다시 시도해주세요.',
      )
    } finally {
      abortController.abort()
      setIsGenerating(false)
    }
  }

  // ── 가이드 삭제 ──
  const handleDeleteGuide = async (guide) => {
    const ok = await confirm({
      title: '가이드 삭제',
      message: `${formatFullDateTime(guide.created_at)} 에 만들어진 가이드를 삭제하시겠습니까?`,
      confirmLabel: '삭제',
      danger: true,
    })
    if (!ok) return
    try {
      if (userPickedGuideId === guide.id) setUserPickedGuideId(null)
      await deleteGuide(guide.id)
      toast.success('가이드가 삭제되었습니다.')
    } catch {
      showError('가이드 삭제에 실패했습니다.')
    }
  }

  // ── 챌린지 시작 ──
  const handleConfirmStart = async (difficulty, targetDays) => {
    try {
      const updated = await confirmStart(difficulty, targetDays)
      if (!updated) return
      toast(
        (t) => (
          <div className="flex items-center gap-3">
            <span className="text-sm">챌린지가 시작되었습니다!</span>
            <button
              onClick={() => { toast.dismiss(t.id); router.push('/challenge') }}
              className="text-blue-500 font-bold text-sm shrink-0 cursor-pointer"
            >
              보러가기
            </button>
          </div>
        ),
        { duration: 4000 }
      )
    } catch {
      showError('챌린지 시작에 실패했습니다.')
    }
  }

  // ── 로딩 스켈레톤 ──
  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 pb-24">
        <Header title="생활습관 가이드" subtitle="맞춤형 건강 가이드" showBack={false} />
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4 animate-pulse">
          <div className="h-10 bg-white rounded-xl w-full" />
          <div className="flex gap-2 overflow-hidden">
            {[1, 2, 3].map((i) => <div key={i} className="h-8 bg-white rounded-full w-16 shrink-0" />)}
          </div>
          {[1, 2, 3].map((i) => <div key={i} className="h-24 bg-white rounded-2xl w-full" />)}
        </div>
        <BottomNav />
      </main>
    )
  }

  const currentTab = TABS.find((t) => t.key === activeTab)

  return (
    <main className="min-h-screen bg-gray-50 pb-40">
      <Header title="생활습관 가이드" subtitle="맞춤형 건강 가이드" showBack={false} />

      <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">

        {/* ── 새 가이드 버튼 ── */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">
            {isGenerating ? '🤖 AI가 분석 중입니다...' : ''}
          </p>
          <button
            onClick={handleClickNewGuide}
            disabled={isGenerating || !profileId}
            className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all ${
              isGenerating || !profileId
                ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-wait'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 cursor-pointer'
            }`}
          >
            {isGenerating ? '생성 중...' : '+ 새 가이드'}
          </button>
        </div>

        {/* ── 가이드 없음 ── */}
        {guides.length === 0 && !isGenerating && (
          <>
            <EmptyState
              title="아직 생활습관 가이드가 없어요"
              message={
                hasEligibleGroup
                  ? '위 버튼을 눌러 AI 맞춤 가이드를 받아보세요'
                  : '처방전을 먼저 등록하면 맞춤 가이드를 받을 수 있어요'
              }
            />
            {!hasEligibleGroup && !groupsLoading && (
              <button
                onClick={() => router.push('/ocr')}
                className="mx-auto block px-5 py-2.5 rounded-xl text-sm font-bold bg-gray-900 text-white hover:bg-gray-700 cursor-pointer"
              >
                처방전 등록하러 가기
              </button>
            )}
          </>
        )}

        {/* ── 첫 가이드 생성 중 스켈레톤 ── */}
        {isGenerating && guides.filter(g => g.status === 'ready').length === 0 && (
          <div className="animate-pulse space-y-4">
            <div className="flex gap-2">
              <div className="h-7 bg-gray-200 rounded-full w-20" />
            </div>
            <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-50">
              <div className="h-3 bg-gray-200 rounded w-32 mb-3" />
              <div className="flex flex-wrap gap-1.5">
                {[1, 2, 3].map((i) => <div key={i} className="h-6 bg-gray-200 rounded-full w-16" />)}
              </div>
            </div>
            <div className="flex gap-1 overflow-hidden">
              {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-9 bg-gray-200 rounded-xl w-20 shrink-0" />)}
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="h-6 w-6 bg-gray-200 rounded" />
                <div className="h-5 bg-gray-200 rounded w-28" />
              </div>
              <div className="space-y-2.5">
                {['w-full', 'w-11/12', 'w-4/5', 'w-full', 'w-3/4', 'w-5/6'].map((w, i) => (
                  <div key={i} className={`h-4 bg-gray-200 rounded ${w}`} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── 기존 가이드 있고 신규 생성 중 — inline 알림 ── */}
        {isGenerating && guides.filter(g => g.status === 'ready').length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex items-center gap-3">
            <div className="h-4 w-4 rounded-full border-2 border-blue-300 border-t-blue-600 animate-spin shrink-0" />
            <div className="min-w-0">
              <p className="text-xs font-bold text-blue-700">새 가이드 생성 중</p>
              <p className="text-[11px] text-blue-500 mt-0.5">
                완료되면 자동으로 새 칩으로 추가됩니다. 기존 가이드는 계속 열람 가능.
              </p>
            </div>
          </div>
        )}

        {/* ── 이력 날짜 칩 ── */}
        {guides.length > 0 && (
          <div ref={chipScrollRef} className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {guides.map((guide) => {
              const isSelected = selectedGuide?.id === guide.id
              return (
                <div
                  key={guide.id}
                  className={`shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
                    isSelected
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
                  }`}
                >
                  <button
                    onClick={() => guide.status === 'ready' && setUserPickedGuideId(guide.id)}
                    disabled={guide.status !== 'ready'}
                    className={guide.status === 'ready' ? 'cursor-pointer' : 'cursor-wait'}
                  >
                    {guide.status !== 'ready'
                      ? '생성중...'
                      : firstReadyGuide?.id === guide.id
                        ? `${formatDate(guide.created_at)} 최신`
                        : formatDate(guide.created_at)}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteGuide(guide) }}
                    className={`ml-0.5 leading-none cursor-pointer transition-colors ${
                      isSelected ? 'text-gray-300 hover:text-white' : 'text-gray-300 hover:text-red-400'
                    }`}
                    title="가이드 삭제"
                  >
                    ×
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {/* ── 과거 가이드 열람 배너 ── */}
        {isViewingHistory && (() => {
          const prescribed = summarizePrescribedRange(selectedGuide.medication_snapshot)
          return (
            <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-amber-500 text-sm">⚠️</span>
                <p className="text-xs text-amber-800 font-bold">
                  {formatFullDateTime(selectedGuide.created_at)} 에 만들어진 가이드예요
                </p>
              </div>
              <p className="text-[11px] text-amber-700 leading-relaxed pl-5">
                {prescribed && <>처방일 {prescribed} 기준으로 작성됐어요. </>}
                이후 처방이나 설문조사가 바뀌었다면 새 가이드를 만들어 주세요.
              </p>
            </div>
          )
        })()}

        {/* ── 가이드 내용 ── */}
        {selectedGuide && (
          <>
            {/* 복용 약 스냅샷 */}
            {selectedGuide.medication_snapshot?.length > 0 && (
              <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-50">
                <p className="text-xs font-bold text-gray-400 mb-2">💊 가이드 생성 시 복용 약</p>
                <div className="flex flex-wrap gap-1.5">
                  {selectedGuide.medication_snapshot.map((med, i) => {
                    const name =
                      typeof med === 'string'
                        ? med
                        : med.medicine_name || med.name || JSON.stringify(med)
                    const dispensed =
                      typeof med === 'object' ? med.dispensed_date || med.start_date : null
                    return (
                      <span
                        key={i}
                        className="bg-gray-100 text-gray-600 text-xs px-2.5 py-1 rounded-full font-bold inline-flex items-center gap-1.5"
                      >
                        {name}
                        {dispensed && (
                          <span className="text-[10px] font-normal text-gray-400">
                            처방 {dispensed.slice(5, 10).replace('-', '/')}
                          </span>
                        )}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* 5개 탭 네비게이션 */}
            <div className="overflow-x-auto scrollbar-hide">
              <div className="flex gap-1 min-w-max pb-1">
                {TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                      activeTab === tab.key
                        ? `${tab.bg} ${tab.color}`
                        : 'bg-white text-gray-400 hover:text-gray-600'
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 탭 콘텐츠 */}
            <div className={`bg-white rounded-2xl shadow-sm border ${currentTab?.border || 'border-gray-100'} p-5`}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{currentTab?.icon}</span>
                <h2 className={`font-black text-base ${currentTab?.color}`}>{currentTab?.label}</h2>
              </div>

              {selectedGuide.content?.[activeTab] ? (
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                  {selectedGuide.content[activeTab]}
                </p>
              ) : (
                <p className="text-sm text-gray-400">이 카테고리의 가이드 내용이 없습니다.</p>
              )}

              {/* ── 증상 탭: 오늘의 증상 요약 카드 + 입력 폼 ── */}
              {activeTab === 'symptom' && (
                <div className="mt-5 space-y-4">

                  {/* 오늘의 증상 요약 카드 */}
                  <div className="bg-orange-50/40 border border-orange-100 rounded-2xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-7 h-7 bg-orange-50 rounded-lg flex items-center justify-center text-orange-500">
                        <Stethoscope size={14} />
                      </div>
                      <p className="text-xs font-black text-orange-700">오늘의 증상 요약</p>
                    </div>

                    {symptomsLoading ? (
                      <div className="animate-pulse flex gap-2">
                        <div className="h-7 bg-orange-100 rounded-full w-16" />
                        <div className="h-7 bg-orange-100 rounded-full w-20" />
                      </div>
                    ) : todaySymptoms.length > 0 ? (
                      <div className="space-y-3">
                        <div className="flex flex-wrap gap-1.5">
                          {todaySymptoms.map((s, idx) => (
                            <span
                              key={idx}
                              className="px-3 py-1.5 bg-white text-orange-700 rounded-full text-xs font-bold border border-orange-100"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                        {todayNote && (
                          <p className="text-gray-500 text-xs leading-relaxed bg-white/70 p-3 rounded-xl border border-dashed border-orange-100">
                            "{todayNote}"
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-orange-400">
                        아직 오늘 기록된 증상이 없어요. 아래에서 입력해보세요.
                      </p>
                    )}
                  </div>

                  {/* 증상 입력 폼 — 저장 후 요약 카드 자동 갱신 */}
                  <SymptomLogForm
                    profileId={profileId}
                    onSaved={() => fetchTodaySymptoms()}
                  />
                </div>
              )}
            </div>

            {/* ── 챌린지 목록 ── */}
            {guideChallenges.length > 0 && (() => {
              const revealed = selectedGuide.revealed_challenge_count ?? 5
              const reachedLimit = revealed >= MAX_REVEALED_CHALLENGES
              return (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-50 p-4">
                  <div className="flex items-center justify-between mb-3 gap-2">
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-gray-400">🎯 이 가이드에서 생성된 챌린지</p>
                      <p className="text-[11px] text-gray-400 mt-0.5 break-keep">
                        한 가이드에서 최대 {MAX_REVEALED_CHALLENGES}개까지 추천받을 수 있어요 ({revealed}/{MAX_REVEALED_CHALLENGES})
                      </p>
                    </div>
                    {!isViewingHistory && (
                      <button
                        type="button"
                        onClick={async () => {
                          if (isRevealing) return
                          if (reachedLimit) {
                            showError(`더 이상 추천받을 수 없어요. 최대 ${MAX_REVEALED_CHALLENGES}개까지 추천받을 수 있어요.`)
                            return
                          }
                          setIsRevealing(true)
                          try {
                            await revealMoreChallenges(selectedGuide.id)
                            toast.success('추천 챌린지 5개를 추가로 보여드려요!')
                          } catch (err) {
                            const detail = err.response?.data?.detail
                            if (err.response?.status === 409 && detail?.code === 'REVEAL_LIMIT_REACHED') {
                              showError(detail.message || `최대 ${MAX_REVEALED_CHALLENGES}개까지 추천받을 수 있어요.`)
                            } else {
                              showError('챌린지 더 보기를 처리하지 못했어요. 잠시 후 다시 시도해주세요.')
                            }
                          } finally {
                            setIsRevealing(false)
                          }
                        }}
                        disabled={reachedLimit || isRevealing}
                        title={reachedLimit ? `최대 ${MAX_REVEALED_CHALLENGES}개까지 추천받을 수 있어요.` : undefined}
                        className={`shrink-0 text-[11px] font-bold px-3 py-1.5 rounded-full border transition-colors ${
                          reachedLimit
                            ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                            : isRevealing
                              ? 'bg-gray-100 text-gray-400 border-gray-200 cursor-wait'
                              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50 cursor-pointer'
                        }`}
                      >
                        {isRevealing ? '...' : '추천 챌린지 더 보기'}
                      </button>
                    )}
                  </div>

                  <div className="space-y-2">
                    {isLoadingChallenges ? (
                      <div className="animate-pulse space-y-2">
                        {[1, 2].map((i) => <div key={i} className="h-10 bg-gray-100 rounded-xl" />)}
                      </div>
                    ) : (
                      guideChallenges.map((c) => {
                        const tabMeta = TABS.find((t) => t.key === c.category)
                        const diffStyle = c.difficulty ? (DIFFICULTY_STYLE[c.difficulty] || DIFFICULTY_STYLE['보통']) : null
                        const today = new Date().toISOString().split('T')[0]
                        const checkedToday = c.completed_dates?.some(
                          (d) => (typeof d === 'string' ? d : d.toISOString?.().split('T')[0]) === today
                        )
                        const isProcessing =
                          (isStarting && startTarget?.id === c.id) || checkingId === c.id

                        return (
                          <div
                            key={c.id}
                            className="flex items-center justify-between gap-3 py-2 px-3 bg-gray-50 rounded-xl"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              {tabMeta && (
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${tabMeta.bg} ${tabMeta.color}`}>
                                  {tabMeta.icon}
                                </span>
                              )}
                              <span className="text-sm font-bold text-gray-800 truncate">{c.title}</span>
                              {diffStyle && (
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${diffStyle.bg} ${diffStyle.text}`}>
                                  {c.difficulty}
                                </span>
                              )}
                            </div>

                            <div className="shrink-0">
                              {c.challenge_status === 'COMPLETED' ? (
                                <span className="bg-green-50 text-green-500 text-[10px] font-bold px-2 py-1 rounded-full">완료</span>
                              ) : !c.is_active ? (
                                <button
                                  onClick={() => requestStart(c)}
                                  disabled={isViewingHistory || isProcessing}
                                  className={`text-[10px] font-bold px-3 py-1.5 rounded-full transition-colors ${
                                    isViewingHistory
                                      ? 'bg-gray-100 text-gray-400 cursor-default'
                                      : isProcessing
                                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                                        : 'bg-gray-900 text-white hover:bg-gray-700 cursor-pointer'
                                  }`}
                                >
                                  {isProcessing ? '...' : '시작하기'}
                                </button>
                              ) : checkedToday ? (
                                <span className="bg-green-50 text-green-500 text-[10px] font-bold px-2 py-1 rounded-full">오늘 완료</span>
                              ) : (
                                <button
                                  onClick={() => checkToday(c)}
                                  disabled={isViewingHistory || isProcessing}
                                  className={`text-[10px] font-bold px-3 py-1.5 rounded-full transition-colors ${
                                    isViewingHistory
                                      ? 'bg-gray-100 text-gray-400 cursor-default'
                                      : isProcessing
                                        ? 'bg-gray-100 text-gray-400 cursor-wait'
                                        : 'bg-gray-900 text-white hover:bg-gray-800 active:scale-95 cursor-pointer'
                                  }`}
                                >
                                  {isProcessing ? '...' : '오늘 체크'}
                                </button>
                              )}
                            </div>
                          </div>
                        )
                      })
                    )}
                  </div>
                </div>
              )
            })()}
          </>
        )}
      </div>

      <BottomNav />

      {/* ── 챌린지 시작 모달 ── */}
      {startTarget && (
        <StartChallengeModal
          challenge={startTarget}
          onConfirm={handleConfirmStart}
          onClose={cancelStart}
          isLoading={isStarting}
        />
      )}

      {/* ── 처방전 선택 모달 ── */}
      {isPickerOpen && (
        <PrescriptionPickerModal
          onConfirm={handleConfirmPickGroup}
          onClose={() => setIsPickerOpen(false)}
          isLoading={isGenerating}
        />
      )}
    </main>
  )
}
