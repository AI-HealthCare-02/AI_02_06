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
import StartChallengeModal from '@/components/common/StartChallengeModal'
import toast from 'react-hot-toast'

// 가이드 생성 SSE / terminal error mapping 은 LifestyleGuideContext 로 이동 완료.

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

// formatFullDateTime: 과거 가이드 안내/삭제 confirm 등에 표시 — 시간까지 (예: "2026.04.30 18:23")
function formatFullDateTime(isoStr) {
  const d = new Date(isoStr)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const HH = String(d.getHours()).padStart(2, '0')
  const MM = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}.${mm}.${dd} ${HH}:${MM}`
}

// medication_snapshot 안의 처방일(dispensed_date) 분포에서 사용자에게 보여줄
// 대표 처방일 라벨을 만든다. 처방일이 모두 같으면 단일 날짜, 다르면 범위로.
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
function ChallengeBanner({ challenge, isViewingHistory }) {
  const router = useRouter()
  // 시작/체크 정책은 hook 으로 ─ 어디서 호출하든 동일 동작.
  const { isStarting, startTarget, requestStart } = useChallengeStart()
  const { checkingId, checkToday } = useChallengeCheck()

  if (!challenge) return null

  const isStartingThis = isStarting && startTarget?.id === challenge.id
  const isChecking = checkingId === challenge.id
  const isProcessing = isStartingThis || isChecking

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
            onClick={() => requestStart(challenge)}
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
              onClick={() => router.push('/challenge')}
              className="text-xs font-bold text-gray-400 hover:text-gray-700 px-2 py-2 rounded-xl hover:bg-gray-100 transition-colors cursor-pointer"
              title="챌린지 페이지에서 보기"
            >
              →
            </button>
          </div>
        ) : (
          // 상태 3-a: 진행중, 오늘 미체크 → 완료 체크 버튼 (PATCH {completed_dates, challenge_status})
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
  const { selectedProfileId: profileId } = useProfile()
  const {
    guides,
    latestGuide,
    isLoading: guidesLoading,
    generateGuide,
    deleteGuide,
  } = useLifestyleGuide()
  const { challengesByGuide } = useChallenge()
  // 챌린지 시작/체크 모두 hook 으로 단일 정책. 페이지는 derived 만 책임.
  const { startTarget, isStarting, requestStart, cancelStart, confirmStart } = useChallengeStart()
  const { checkingId, checkToday } = useChallengeCheck()

  const [isGenerating, setIsGenerating] = useState(false)
  const [selectedGuide, setSelectedGuide] = useState(null)   // 현재 본문에 표시되는 가이드
  // 사용자가 칩으로 명시 선택한 가이드 id — set 되어 있으면 sticky.
  // null 일 때만 자동으로 latestGuide 를 따라간다 (auto-follow).
  // 새 가이드 생성 또는 picked 가이드 삭제 시 null 로 리셋.
  const [userPickedGuideId, setUserPickedGuideId] = useState(null)
  const [activeTab, setActiveTab] = useState('interaction')  // 현재 선택된 탭 키


  const chipScrollRef = useRef(null)
  const isLoading = guidesLoading

  // selectedGuide 의 챌린지는 ChallengeContext store 에서 derived.
  // 화면 일관성을 위해 TABS 순서 (interaction -> sleep -> diet -> exercise
  // -> symptom) 로 정렬 후 target_days asc 로 tiebreak — store 의 union 순서
  // (가이드 ready 시 appendChallenges 가 push) 에 영향받지 않게 한다.
  const guideChallenges = (selectedGuide ? challengesByGuide(selectedGuide.id) : [])
    .slice()
    .sort((a, b) => {
      const ai = TABS.findIndex((t) => t.key === a.category)
      const bi = TABS.findIndex((t) => t.key === b.category)
      const aOrd = ai === -1 ? TABS.length : ai
      const bOrd = bi === -1 ? TABS.length : bi
      if (aOrd !== bOrd) return aOrd - bOrd
      return (a.target_days || 0) - (b.target_days || 0)
    })
  const isLoadingChallenges = false  // store 에서 derived 라 별도 로딩 없음

  // 과거 열람 = ready 가이드 중 가장 최신과 selectedGuide 가 다를 때.
  // placeholder (status='pending') 는 비교에 끼지 않는다 — 그래야 "+ 새 가이드"
  // 직후 placeholder 가 guides[0] 로 prepend 되어도 isViewingHistory 가
  // 갑자기 true 로 바뀌지 않는다 (사용자 우려).
  const firstReadyGuide = guides.find(g => g.status === 'ready') || null
  const isViewingHistory =
    !!selectedGuide && !!firstReadyGuide && selectedGuide.id !== firstReadyGuide.id

  // 가이드 store 변동 시 selectedGuide 자동 보정.
  //
  // 정책:
  //  1) userPickedGuideId 가 set 되어 있으면 그 가이드를 sticky 로 유지
  //     (단, 그 가이드가 사라졌으면 auto-follow 로 회귀)
  //  2) auto-follow: 항상 latestGuide (= 가장 최근 ready) 를 selectedGuide 로
  //     → "+ 새 가이드" → ready 도달 시 자동으로 새 가이드로 본문 전환
  //  3) latestGuide 가 없으면 guides 안의 ready 가이드 중 첫 번째
  useEffect(() => {
    if (userPickedGuideId) {
      const picked = guides.find(g => g.id === userPickedGuideId && g.status === 'ready')
      if (picked) {
        if (picked !== selectedGuide) setSelectedGuide(picked)
        return
      }
      // picked 가이드가 사라짐 (삭제됨) → auto-follow 로 회귀
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
    if (!profileId) {
      showError('프로필을 먼저 선택해주세요.')
      return
    }
    if (isGenerating) return
    setIsGenerating(true)
    // 새 가이드 생성 시 auto-follow 모드로 회귀 — ready 도달 시 자동 본문 전환
    setUserPickedGuideId(null)
    const abortController = new AbortController()
    try {
      // Context 의 generateGuide 가 placeholder 삽입 + SSE update + ready 자동 처리.
      // 사용자가 생성 중 placeholder 를 직접 삭제한 경우 result === null 로 silent.
      const result = await generateGuide(profileId, abortController.signal)
      if (!result) return
      toast.success('새 가이드가 생성되었습니다!')
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

  const handleDeleteGuide = async (guide) => {
    if (!confirm(`${formatFullDateTime(guide.created_at)} 가이드를 삭제하시겠습니까?`)) return
    try {
      // sticky picked 가 삭제 대상이면 auto-follow 로 회귀
      if (userPickedGuideId === guide.id) setUserPickedGuideId(null)
      await deleteGuide(guide.id)
      toast.success('가이드가 삭제되었습니다.')
    } catch {
      showError('가이드 삭제에 실패했습니다.')
    }
  }

  // ── 챌린지 시작 (모달 onConfirm) ──
  // useChallengeStart 의 confirmStart 가 PATCH /api/v1/challenges/{id}/start 호출.
  // ChallengeContext 가 응답으로 store in-place 갱신 → guideChallenges derived 자동 반영.
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

  // 체크 정책은 useChallengeCheck hook 으로 이전 — handleChallengeCheck 제거됨.

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

        {/* ── 생성 버튼 — 타이틀 우측 작은 버튼으로 변경 ── */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">
            {isGenerating ? '🤖 AI가 분석 중입니다...' : ''}
          </p>
          <button
            onClick={handleGenerate}
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

        {/* ── 첫 가이드 생성 중 (이력 없음) — 큰 스켈레톤 ── */}
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

        {/* ── 기존 가이드 보유 + 생성 중 — 작은 inline placeholder ── */}
        {/*    기존 selectedGuide 본문은 그대로 유지하고, 새 가이드는            */}
        {/*    이력 칩에서 "생성중" 표시 + 상단 알림 카드로만 안내한다.            */}
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

        {/* ── 과거 가이드 열람 배너 ──
            처방일이 아니라 "가이드 생성 시점" 기준임을 명확히 함.
            이후 처방 / 설문 변경이 있을 수 있어 새 가이드 생성을 권장.   */}
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

        {/* ── 가이드 내용 (가이드 선택된 경우) — 생성 중에도 기존 ready 가이드는 그대로 보인다 ── */}
        {selectedGuide && (
          <>
            {/* 복용 약 스냅샷 — 처방일이 있으면 chip 옆에 작은 라벨로 표기 */}
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

      {/* (lifestyle-guide 하단 챌린지 배너 제거 — main PR 의도. 챌린지 시작은
          가이드 내 추천 카드의 "시작하기" 버튼이 useChallengeStart hook 으로 직접
          처리, 별도 floating banner 는 화면을 가려 제거됨.) */}

      <BottomNav />

      {/* ── 챌린지 시작 모달 (난이도·기간 선택 바텀시트) ── */}
      {startTarget && (
        <StartChallengeModal
          challenge={startTarget}
          onConfirm={handleConfirmStart}
          onClose={cancelStart}
          isLoading={isStarting}
        />
      )}
    </main>
  )
}
