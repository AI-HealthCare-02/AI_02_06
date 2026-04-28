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
import StartChallengeModal from '@/components/common/StartChallengeModal'
import toast from 'react-hot-toast'
import { streamSSE } from '@/lib/sseClient'

const GUIDE_TERMINAL_ERROR_MESSAGES = {
  no_active_meds: '활성 약물이 없어 가이드를 만들 수 없어요. 복약 등록 후 다시 시도해주세요.',
  failed: '가이드 생성 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.',
}

/**
 * 가이드 생성 SSE 를 ready/terminal 까지 자동 재연결하며 await for-of 로 소비.
 * timeout event 시 새 연결 — 무한 재시도 (cancel 또는 ready 까지).
 *
 * @yields {{id, profile_id, status, content, medication_snapshot, created_at, processed_at}}
 */
async function* watchGuideStatus(guideId, signal) {
  while (true) {
    let timedOut = false
    for await (const ev of streamSSE(`/api/v1/lifestyle-guides/${guideId}/stream`, { signal })) {
      if (ev.event === 'update') yield ev.data
      else if (ev.event === 'timeout') { timedOut = true; break }
      else if (ev.event === 'error') throw new Error(ev.data?.detail || 'sse error')
    }
    if (!timedOut) return
  }
}

// ── 탭 메타데이터 ──────────────────────────────────────────────────────────────
// key: API 응답 content 객체의 키값 및 challenge.category 매핑 값과 일치해야 함
const TABS = [
  {
    key: 'interaction',
    label: '약물 상호작용',
    icon: '⚠️',
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    activeBorder: 'border-red-500',
  },
  {
    key: 'sleep',
    label: '수면·생체리듬',
    icon: '🌙',
    color: 'text-indigo-500',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    activeBorder: 'border-indigo-500',
  },
  {
    key: 'diet',
    label: '식단·수분',
    icon: '🥗',
    color: 'text-green-500',
    bg: 'bg-green-50',
    border: 'border-green-200',
    activeBorder: 'border-green-500',
  },
  {
    key: 'exercise',
    label: '운동',
    icon: '💪',
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    activeBorder: 'border-blue-500',
  },
  {
    key: 'symptom',
    label: '증상 트래킹',
    icon: '🩺',
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    activeBorder: 'border-orange-500',
  },
]

// 챌린지 난이도 뱃지 스타일 매핑
const DIFFICULTY_STYLE = {
  '쉬움': { bg: 'bg-blue-50', text: 'text-blue-500' },
  '보통': { bg: 'bg-green-50', text: 'text-green-500' },
  '어려움': { bg: 'bg-red-50', text: 'text-red-500' },
}

// ── 날짜 포맷 유틸 ─────────────────────────────────────────────────────────────
// formatDate: 이력 날짜 칩에 표시 (예: "4/24")
function formatDate(isoStr) {
  const d = new Date(isoStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// formatFullDate: 과거 가이드 열람 안내 배너에 표시 (예: "2026.04.24")
function formatFullDate(isoStr) {
  const d = new Date(isoStr)
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
}

// ── 증상 로그 폼 컴포넌트 ──────────────────────────────────────────────────────
// '증상 트래킹' 탭에서만 렌더링되는 일일 증상 기록 입력 폼
// - POST /api/v1/daily-logs 로 {profile_id, log_date, symptoms[], note} 전송
// - 409 충돌 시 "오늘 기록이 이미 있습니다." 안내 (하루 1회 제한)
function SymptomLogForm({ profileId, onSaved }) {
  // 선택 가능한 증상 프리셋 태그 목록
  const PRESET_SYMPTOMS = [
    '어지러움', '두통', '구역질', '복통', '설사', '변비',
    '피로감', '수면 장애', '식욕 부진', '발진', '심계항진',
  ]

  const [selected, setSelected] = useState([])
  const [note, setNote] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const today = new Date().toISOString().split('T')[0]

  // 프리셋 태그 토글: 선택된 항목이면 제거, 아니면 추가
  const toggle = (symptom) => {
    setSelected((prev) =>
      prev.includes(symptom) ? prev.filter((s) => s !== symptom) : [...prev, symptom]
    )
  }

  const handleSave = async () => {
    if (!profileId) return
    setIsSaving(true)
    try {
      await api.post('/api/v1/daily-logs', {
        profile_id: profileId,
        log_date: today,
        symptoms: selected,
        note: note || null,
      })
      toast.success('증상 기록이 저장되었습니다.')
      setSelected([])
      setNote('')
      onSaved?.()
    } catch (err) {
      // 409: 당일 중복 기록 방지
      if (err.response?.status === 409) {
        showError('오늘 기록이 이미 있습니다.')
      } else {
        showError('저장에 실패했습니다.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="mt-4 space-y-4">
      <div>
        <p className="text-xs font-bold text-gray-500 mb-2">오늘의 증상 선택</p>
        <div className="flex flex-wrap gap-2">
          {PRESET_SYMPTOMS.map((s) => (
            <button
              key={s}
              onClick={() => toggle(s)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${
                selected.includes(s)
                  ? 'bg-orange-500 text-white border-orange-500'
                  : 'bg-white text-gray-500 border-gray-200 hover:border-orange-300'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-bold text-gray-500 mb-1">메모 (선택)</p>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="오늘 몸 상태를 자유롭게 적어보세요"
          maxLength={512}
          rows={3}
          className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 resize-none focus:outline-none focus:border-orange-300"
        />
      </div>

      <button
        onClick={handleSave}
        disabled={isSaving}
        className={`w-full py-3 rounded-xl text-sm font-bold transition-colors ${
          isSaving
            ? 'bg-gray-100 text-gray-400 cursor-wait'
            : 'bg-orange-500 text-white hover:bg-orange-600 cursor-pointer'
        }`}
      >
        {isSaving ? '저장 중...' : '오늘 증상 기록하기'}
      </button>
    </div>
  )
}

// ── 챌린지 배너 컴포넌트 ────────────────────────────────────────────────────────
// 화면 하단에 고정되는 배너로, 현재 선택된 탭 카테고리에 해당하는 챌린지 1개를 표시
// 챌린지 3-상태 패턴:
//   1) COMPLETED → 초록 "완료" 뱃지 (버튼 없음)
//   2) is_active=false → "시작하기" 버튼 (과거 가이드 열람 시 비활성화)
//   3) is_active=true → 오늘 체크 여부에 따라 "오늘 완료 체크" 버튼 or "오늘 완료!" 텍스트
function ChallengeBanner({ challenge, isViewingHistory, onStart, onCheck, isProcessing, onGoToChallenge }) {
  if (!challenge) return null

  const today = new Date().toISOString().split('T')[0]
  // completed_dates 배열에 오늘 날짜가 있는지 확인 (string/Date 양쪽 타입 대응)
  const checkedToday = challenge.completed_dates?.some(
    (d) => (typeof d === 'string' ? d : d.toISOString?.().split('T')[0]) === today
  )

  // 상태 1: COMPLETED - 완료 뱃지 표시
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

        {/* 과거 가이드 열람 중이면 모든 챌린지 액션 비활성화 */}
        {isViewingHistory ? (
          <span className="text-xs text-gray-400 shrink-0 ml-3">과거 가이드</span>
        ) : !challenge.is_active ? (
          // 상태 2: 미시작 → 시작하기 버튼 (PATCH {is_active: true})
          <button
            onClick={() => onStart(challenge)}
            disabled={isProcessing}
            className={`ml-3 px-4 py-2 rounded-xl text-xs font-bold shrink-0 transition-colors cursor-pointer ${
              isProcessing ? 'bg-gray-100 text-gray-400 cursor-wait' : 'bg-gray-900 text-white hover:bg-gray-700'
            }`}
          >
            {isProcessing ? '처리중...' : '시작하기'}
          </button>
        ) : checkedToday ? (
          // 상태 3-b: 오늘 이미 체크함 → 완료 텍스트 + 챌린지 페이지 이동 버튼
          <div className="flex items-center gap-2 ml-3 shrink-0">
            <span className="bg-green-50 text-green-500 text-xs font-bold px-3 py-2 rounded-xl">
              오늘 완료!
            </span>
            <button
              onClick={onGoToChallenge}
              className="text-xs font-bold text-gray-400 hover:text-gray-700 px-2 py-2 rounded-xl hover:bg-gray-100 transition-colors cursor-pointer"
              title="챌린지 페이지에서 보기"
            >
              →
            </button>
          </div>
        ) : (
          // 상태 3-a: 진행중, 오늘 미체크 → 완료 체크 버튼 (PATCH {completed_dates, challenge_status})
          <button
            onClick={() => onCheck(challenge)}
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
  const { selectedProfileId: profileId } = useProfile()

  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [guides, setGuides] = useState([])                   // 전체 가이드 이력 목록 (최신순)
  const [selectedGuide, setSelectedGuide] = useState(null)   // 현재 날짜 칩으로 선택된 가이드
  const [activeTab, setActiveTab] = useState('interaction')  // 현재 선택된 탭 키

  const [guideChallenges, setGuideChallenges] = useState([])         // 선택된 가이드에 연결된 챌린지 목록
  const [isLoadingChallenges, setIsLoadingChallenges] = useState(false)
  const [processingChallengeId, setProcessingChallengeId] = useState(null) // 현재 처리 중인 챌린지 ID
  const [startTarget, setStartTarget] = useState(null)   // 모달에 전달할 챌린지 객체
  const [isStarting, setIsStarting] = useState(false)    // 모달 확인 버튼 처리 중 여부

  const isInitialLoad = useRef(true)
  const chipScrollRef = useRef(null)

  // 선택된 가이드가 최신(guides[0])이 아닌 경우 과거 열람 모드
  // → 과거 열람 모드에서는 챌린지 시작/체크 버튼이 모두 비활성화됨
  const isViewingHistory = guides.length > 0 && selectedGuide?.id !== guides[0]?.id

  // ── 초기 로딩 ──
  // profileId가 확정되면 최신 가이드와 전체 이력을 병렬로 요청
  // Promise.allSettled 사용: 하나가 실패해도 나머지 결과는 활용
  useEffect(() => {
    if (!profileId) return
    const load = async () => {
      try {
        if (isInitialLoad.current) setIsLoading(true)

        const [latestRes, listRes] = await Promise.allSettled([
          api.get(`/api/v1/lifestyle-guides/latest?profile_id=${profileId}`),
          api.get(`/api/v1/lifestyle-guides?profile_id=${profileId}`),
        ])

        const list = listRes.status === 'fulfilled' ? listRes.value.data : []
        setGuides(list)

        // 최신 가이드를 기본 선택 (실패 시 목록의 첫 번째로 대체)
        if (latestRes.status === 'fulfilled') {
          setSelectedGuide(latestRes.value.data)
        } else if (list.length > 0) {
          setSelectedGuide(list[0])
        }
      } catch (err) {
        if (err.response?.status !== 401) showError('데이터를 불러오는데 실패했습니다.')
      } finally {
        setIsLoading(false)
        isInitialLoad.current = false
      }
    }
    load()
  }, [profileId])

  // ── 선택된 가이드의 챌린지 로딩 ──
  // 날짜 칩으로 다른 가이드 선택 시마다 해당 가이드에 연결된 챌린지 목록 재요청
  useEffect(() => {
    if (!selectedGuide?.id) {
      setGuideChallenges([])
      return
    }
    const loadChallenges = async () => {
      setIsLoadingChallenges(true)
      try {
        const res = await api.get(`/api/v1/lifestyle-guides/${selectedGuide.id}/challenges`)
        setGuideChallenges(res.data)
      } catch {
        setGuideChallenges([])
      } finally {
        setIsLoadingChallenges(false)
      }
    }
    loadChallenges()
  }, [selectedGuide?.id])

  // ── 현재 탭에 해당하는 챌린지 1개 ──
  // 하단 배너에 표시할 챌린지: 현재 탭의 category와 일치하는 것 중 DELETED 제외
  const activeBannerChallenge = guideChallenges.find(
    (c) => c.category === activeTab && c.challenge_status !== 'DELETED'
  ) || null

  // ── 가이드 생성 (RQ + SSE) ──
  // 1) POST /api/v1/lifestyle-guides/generate → 즉시 202 + {id, status:'pending'}
  // 2) pending placeholder 를 selectedGuide + guides 에 삽입 (스켈레톤 렌더 유도)
  // 3) GET /lifestyle-guides/{id}/stream SSE 로 status 변화 수신
  // 4) ready 도달 시 받은 payload 로 guides/selectedGuide 교체
  // 5) terminal error 시 안내 + placeholder 제거
  const handleGenerate = async () => {
    if (!profileId || isGenerating) return
    setIsGenerating(true)
    const abortController = new AbortController()

    try {
      const enqueueRes = await api.post(
        `/api/v1/lifestyle-guides/generate?profile_id=${profileId}`,
        null,
      )
      const pendingId = enqueueRes.data.id
      const pendingGuide = {
        id: pendingId,
        profile_id: profileId,
        status: 'pending',
        content: {},
        medication_snapshot: [],
        created_at: new Date().toISOString(),
        processed_at: null,
      }
      setGuides((prev) => [pendingGuide, ...prev])
      setSelectedGuide(pendingGuide)

      for await (const payload of watchGuideStatus(pendingId, abortController.signal)) {
        const status = payload.status
        if (status === 'ready') {
          setGuides((prev) => prev.map((g) => (g.id === pendingId ? payload : g)))
          setSelectedGuide(payload)
          toast.success('새 가이드가 생성되었습니다!')
          return
        }
        if (status in GUIDE_TERMINAL_ERROR_MESSAGES) {
          showError(GUIDE_TERMINAL_ERROR_MESSAGES[status])
          setGuides((prev) => prev.filter((g) => g.id !== pendingId))
          setSelectedGuide((prev) => (prev?.id === pendingId ? null : prev))
          return
        }
        // status='pending' — 다음 update 대기 (스켈레톤 유지)
      }
    } catch (err) {
      // BE 409 + detail.code=NO_ACTIVE_MEDICATIONS → 토스트 + 처방전 등록 페이지 자동 이동
      const detail = err.response?.data?.detail
      if (err.response?.status === 409 && detail?.code === 'NO_ACTIVE_MEDICATIONS') {
        showError(detail.message || '처방전이 등록되어야 맞춤 가이드 생성이 가능합니다.')
        router.push(detail.redirect_to || '/ocr')
        return
      }
      showError(err.parsed?.message || err.message || '가이드 생성에 실패했습니다. 잠시 후 다시 시도해주세요.')
    } finally {
      abortController.abort()
      setIsGenerating(false)
    }
  }

  // ── 가이드 삭제 ──
  // DELETE /api/v1/lifestyle-guides/{id}
  // 미시작 챌린지는 서버에서 소프트 삭제, 진행중/완료 챌린지는 guide_id=NULL로 유지
  const handleDeleteGuide = async (guide) => {
    if (!confirm(`${formatFullDate(guide.created_at)} 가이드를 삭제하시겠습니까?`)) return
    try {
      await api.delete(`/api/v1/lifestyle-guides/${guide.id}`)
      const newGuides = guides.filter((g) => g.id !== guide.id)
      setGuides(newGuides)
      if (selectedGuide?.id === guide.id) {
        setSelectedGuide(newGuides[0] || null)
      }
      toast.success('가이드가 삭제되었습니다.')
    } catch {
      showError('가이드 삭제에 실패했습니다.')
    }
  }

  // ── 챌린지 시작 ──
  // 시작하기 버튼 클릭 → 모달 표시 (즉시 API 호출 X)
  const handleChallengeStart = (challenge) => {
    setStartTarget(challenge)
  }

  // ── 챌린지 시작 확인 (모달 onConfirm) ──
  // PATCH /api/v1/challenges/{id}/start { difficulty, target_days }
  // /start 엔드포인트: is_active=True + started_at 타임스탬프 기록 + 커스텀값 저장
  const handleConfirmStart = async (difficulty, targetDays) => {
    if (!startTarget || isStarting) return
    setIsStarting(true)
    setProcessingChallengeId(startTarget.id)
    try {
      const res = await api.patch(`/api/v1/challenges/${startTarget.id}/start`, {
        difficulty,
        target_days: targetDays,
      })
      setGuideChallenges((prev) =>
        prev.map((c) => (c.id === startTarget.id ? { ...c, ...res.data } : c))
      )
      setStartTarget(null)
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
    } finally {
      setIsStarting(false)
      setProcessingChallengeId(null)
    }
  }

  // ── 챌린지 오늘 완료 체크 ──
  // PATCH /api/v1/challenges/{id} { completed_dates, challenge_status }
  // 목표 달성 일수(target_days) 도달 시 자동으로 COMPLETED 상태로 전환
  const handleChallengeCheck = async (challenge) => {
    if (processingChallengeId) return
    const today = new Date().toISOString().split('T')[0]
    const alreadyChecked = challenge.completed_dates?.some(
      (d) => (typeof d === 'string' ? d : d.toISOString?.().split('T')[0]) === today
    )
    if (alreadyChecked) {
      showError('오늘은 이미 체크했습니다!')
      return
    }

    setProcessingChallengeId(challenge.id)
    try {
      const newDates = [...(challenge.completed_dates || []), today]
      // 완료 날짜 수가 목표 일수 이상이면 COMPLETED, 아니면 IN_PROGRESS 유지
      const isCompleted = newDates.length >= challenge.target_days
      const res = await api.patch(`/api/v1/challenges/${challenge.id}`, {
        completed_dates: newDates,
        challenge_status: isCompleted ? 'COMPLETED' : 'IN_PROGRESS',
      })
      setGuideChallenges((prev) =>
        prev.map((c) => (c.id === challenge.id ? { ...c, ...res.data } : c))
      )
      if (isCompleted) toast.success('챌린지를 완료했습니다! 수고하셨어요.')
    } catch {
      showError('체크에 실패했습니다.')
    } finally {
      setProcessingChallengeId(null)
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

        {/* ── 생성 버튼 ── */}
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className={`w-full py-3.5 rounded-2xl text-sm font-bold transition-all ${
            isGenerating
              ? 'bg-gray-100 text-gray-400 cursor-wait'
              : 'bg-gray-900 text-white hover:bg-gray-700 cursor-pointer active:scale-[0.98]'
          }`}
        >
          {isGenerating ? '🤖 AI가 복약 기록을 분석 중입니다...' : '✨ 새 가이드 생성하기'}
        </button>

        {/* ── 가이드 없음: EmptyState + 처방전 선행 안내 ── */}
        {guides.length === 0 && !isGenerating && (
          <>
            <EmptyState
              title="아직 생활습관 가이드가 없어요"
              message="위 버튼을 눌러 AI 맞춤 가이드를 받아보세요"
            />
            <p className="text-center text-sm font-bold text-red-500 -mt-2">
              처방전이 등록되어야 맞춤 가이드 생성이 됩니다
            </p>
          </>
        )}

        {/* ── 가이드 생성 중 스켈레톤 ── */}
        {isGenerating && (
          <div className="animate-pulse space-y-4">
            <div className="flex gap-2">
              <div className="h-7 bg-gray-200 rounded-full w-20" />
              {guides.length > 0 && <div className="h-7 bg-gray-200 rounded-full w-14" />}
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
                <div className="h-4 bg-gray-200 rounded w-full" />
                <div className="h-4 bg-gray-200 rounded w-11/12" />
                <div className="h-4 bg-gray-200 rounded w-4/5" />
                <div className="h-4 bg-gray-200 rounded w-full" />
                <div className="h-4 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-5/6" />
              </div>
            </div>
          </div>
        )}

        {/* ── 이력 날짜 칩 (가이드 있을 때만) ── */}
        {guides.length > 0 && (
          <div ref={chipScrollRef} className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {guides.map((guide, idx) => {
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
                    onClick={() => setSelectedGuide(guide)}
                    className="cursor-pointer"
                  >
                    {idx === 0 ? `${formatDate(guide.created_at)} 최신` : formatDate(guide.created_at)}
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
        {isViewingHistory && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5 flex items-center gap-2">
            <span className="text-amber-500 text-sm">⚠️</span>
            <p className="text-xs text-amber-700 font-bold">
              이 가이드는 {formatFullDate(selectedGuide.created_at)} 기준 과거 처방 기준입니다
            </p>
          </div>
        )}

        {/* ── 가이드 내용 (가이드 선택된 경우, 생성 중에는 스켈레톤으로 대체) ── */}
        {selectedGuide && !isGenerating && (
          <>
            {/* 복용 약 스냅샷 */}
            {selectedGuide.medication_snapshot?.length > 0 && (
              <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-50">
                <p className="text-xs font-bold text-gray-400 mb-2">💊 가이드 생성 시 복용 약</p>
                <div className="flex flex-wrap gap-1.5">
                  {selectedGuide.medication_snapshot.map((med, i) => (
                    <span
                      key={i}
                      className="bg-gray-100 text-gray-600 text-xs px-2.5 py-1 rounded-full font-bold"
                    >
                      {typeof med === 'string' ? med : med.medicine_name || med.name || JSON.stringify(med)}
                    </span>
                  ))}
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

              {/* 증상 탭: 일일 로그 입력 폼 */}
              {activeTab === 'symptom' && (
                <SymptomLogForm profileId={profileId} onSaved={() => {}} />
              )}
            </div>

            {/* 이 가이드의 전체 챌린지 목록 (배너 외) */}
            {guideChallenges.length > 0 && (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-50 p-4">
                <p className="text-xs font-bold text-gray-400 mb-3">🎯 이 가이드에서 생성된 챌린지</p>
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
                      const isProcessing = processingChallengeId === c.id

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
                                onClick={() => handleChallengeStart(c)}
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
                                onClick={() => handleChallengeCheck(c)}
                                disabled={isViewingHistory || isProcessing}
                                className={`text-[10px] font-bold px-3 py-1.5 rounded-full transition-colors ${
                                  isViewingHistory
                                    ? 'bg-gray-100 text-gray-400 cursor-default'
                                    : isProcessing
                                      ? 'bg-gray-100 text-gray-400 cursor-wait'
                                      : 'bg-blue-500 text-white hover:bg-blue-600 cursor-pointer'
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
            )}
          </>
        )}
      </div>

      {/* ── 하단 고정 챌린지 배너 ── */}
      {!isLoadingChallenges && (
        <ChallengeBanner
          challenge={activeBannerChallenge}
          isViewingHistory={isViewingHistory}
          onStart={handleChallengeStart}
          onCheck={handleChallengeCheck}
          isProcessing={processingChallengeId === activeBannerChallenge?.id}
          onGoToChallenge={() => router.push('/challenge')}
        />
      )}

      <BottomNav />

      {/* ── 챌린지 시작 모달 (난이도·기간 선택 바텀시트) ── */}
      {startTarget && (
        <StartChallengeModal
          challenge={startTarget}
          onConfirm={handleConfirmStart}
          onClose={() => setStartTarget(null)}
          isLoading={isStarting}
        />
      )}
    </main>
  )
}
