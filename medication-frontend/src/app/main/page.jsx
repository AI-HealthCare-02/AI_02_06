'use client'
import { useState, useEffect, useRef, Suspense, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api from '@/lib/api'
import { Pill, Flame, Plus, MessageCircle, FileText, Loader2, X, Trash2 } from 'lucide-react'
import ChatModal from '@/components/chat/ChatModal'
import SurveyModal from '@/components/common/SurveyModal'
import { useProfile } from '@/contexts/ProfileContext'
import { useMedication } from '@/contexts/MedicationContext'
import { useChallenge } from '@/contexts/ChallengeContext'
import { useOcrDraft } from '@/contexts/OcrDraftContext'

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

function MainPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [activeChallenge, setActiveChallenge] = useState(null)
  const [greeting, setGreeting] = useState({ msg: '반가워요', sub: '오늘 하루도 건강하게 시작해봐요' })

  const { selectedProfileId, selectedProfile } = useProfile()
  // 4 Context 가 모든 server state 를 단일 진실로 관리 — 자체 fetch 0
  const { activeMedications: medications } = useMedication()
  const { activeChallenges } = useChallenge()
  const { activeDrafts, removeDraftLocally, refetchDrafts } = useOcrDraft()
  const userName = selectedProfile?.name?.split('(')[0] || '사용자'
  const isInitialLoad = useRef(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  // 설문 팝업 쿼리 파라미터 감지
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (searchParams.get('showSurvey') === 'true') {
      setShowSurvey(true)
      router.replace('/main', { scroll: false })
    }
  }, [searchParams, router])
  /* eslint-enable react-hooks/set-state-in-effect */

  // Context 들이 자동으로 server state 를 관리 — 페이지는 derived state 만 갱신.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!selectedProfileId) return
    isInitialLoad.current = false
    setIsLoading(false)
    const hour = new Date().getHours()
    if (hour < 12) setGreeting({ msg: '좋은 아침이에요', sub: '오늘 하루도 건강하게 시작해봐요' })
    else if (hour < 17) setGreeting({ msg: '좋은 오후예요', sub: '점심 식사 후 약 챙기셨나요?' })
    else setGreeting({ msg: '좋은 저녁이에요', sub: '저녁 복약 시간을 확인해보세요' })
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
  /* eslint-enable react-hooks/set-state-in-effect */

  // window focus 시 drafts 재동기화 (백그라운드에서 다른 탭에서 등록·완료한 draft 반영)
  useEffect(() => {
    if (!selectedProfileId) return
    window.addEventListener('focus', refetchDrafts)
    return () => window.removeEventListener('focus', refetchDrafts)
  }, [selectedProfileId, refetchDrafts])

  // 처리 중이거나 확인 대기 중인 draft 가 있으면 그쪽으로 이동, 없으면 업로드 페이지로.
  // 업로드 버튼 + 빈 약 카드의 등록 버튼 모두 동일 분기를 공유한다.
  const goToOcrFlow = useCallback(() => {
    if (activeDrafts.length > 0) {
      router.push(`/ocr/result?draft_id=${activeDrafts[0].draft_id}`)
    } else {
      router.push('/ocr')
    }
  }, [activeDrafts, router])

  // 카드에서 개별 draft 폐기 — 백엔드 DELETE 후 즉시 목록에서 제외.
  // 실패 시에도 사용자 흐름을 차단하지 않고 silently skip (24h 후 자동 정리됨).
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

      {/* ── 히어로 섹션 (main의 다크 테마 + donghoon의 이름 데이터) ── */}
      <section className="relative w-full min-h-[540px] flex items-center justify-center overflow-hidden bg-black">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="relative z-10 text-center px-6 max-w-3xl mx-auto py-24">
          <p className="text-gray-500 text-xs font-bold mb-5 tracking-[0.2em] uppercase">{greeting.sub}</p>
          <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-8">
            {greeting.msg},<br /><span className="text-gray-600">{userName} 님</span>
          </h1>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button onClick={goToOcrFlow} className="px-8 py-4 bg-white text-black font-bold rounded-full hover:bg-gray-100 transition-all cursor-pointer">처방전 등록하기</button>
            <button onClick={() => setShowChat(true)} className="px-8 py-4 bg-gray-900 text-white font-bold rounded-full border border-gray-800 hover:bg-gray-800 transition-all cursor-pointer flex items-center gap-2 justify-center">
              <MessageCircle size={20}/> AI 상담하기
            </button>
          </div>
        </div>
      </section>

      {/* ── 대시보드 ── */}
      <main className="max-w-7xl mx-auto w-full px-6 py-14">
        <div className="grid md:grid-cols-12 gap-6 items-start">
          {/* 복약 현황 */}
          <section className="md:col-span-8 bg-white rounded-[32px] p-8 border border-gray-100">
            <div className="flex justify-between items-center mb-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-100 rounded-2xl flex items-center justify-center"><Pill size={20} className="text-gray-900" /></div>
                <h2 className="text-xl font-bold text-gray-900">복용 중인 약</h2>
              </div>
              <button onClick={() => router.push('/medication')} className="text-sm font-bold text-gray-400 hover:text-gray-900 transition-colors cursor-pointer">
                전체보기 →
              </button>
            </div>
            {medications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
                  <Pill size={28} className="text-gray-300" />
                </div>
                <p className="text-gray-400 font-bold mb-1">등록된 약이 없어요</p>
                <p className="text-gray-300 text-sm mb-6">처방전을 촬영해서 약을 등록해보세요</p>
                <button onClick={goToOcrFlow} className="px-6 py-3 bg-gray-900 text-white text-sm font-bold rounded-full cursor-pointer hover:bg-gray-800 transition-colors">
                  처방전 등록하기
                </button>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {medications.slice(0, 6).map((med) => (
                  <div
                    key={med.id}
                    onClick={() => router.push(`/medication/${med.id}`)}
                    className="p-5 rounded-2xl border border-gray-100 bg-white shadow-sm hover:border-gray-300 hover:shadow-md transition-all cursor-pointer"
                  >
                    <div className="flex justify-between items-start mb-3">
                      {med.category && (
                        <span className="text-[10px] font-bold text-blue-500 bg-blue-50 px-2 py-1 rounded-full">{med.category}</span>
                      )}
                      <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center ml-auto">
                        <Plus size={12} className="text-gray-400" />
                      </div>
                    </div>
                    <h3 className="font-bold text-gray-900 text-sm mb-2 leading-snug">{med.medicine_name}</h3>
                    <p className="text-xs text-gray-400">
                      {[med.dose_per_intake, med.intake_instruction].filter(Boolean).join(' · ') || '복용 정보 없음'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 사이드바 */}
          <div className="md:col-span-4 space-y-6">
            <div onClick={() => router.push('/challenge')} className="bg-gray-900 rounded-[32px] p-8 text-white cursor-pointer hover:-translate-y-1 transition-all min-h-[220px] flex flex-col justify-end relative overflow-hidden group">
              <Flame size={120} className="absolute -right-4 -top-4 opacity-[0.05] group-hover:scale-110 transition-transform" />
              <p className="text-gray-500 font-bold text-xs mb-2 tracking-widest">CHALLENGE</p>
              {activeChallenge ? (
                <>
                  <h2 className="text-2xl font-black mb-3">{activeChallenge.title}</h2>
                  <p className="text-orange-500 text-sm font-bold">
                    {activeChallenge.completed_dates?.length || 0}일째 성공 중! →
                  </p>
                </>
              ) : (
                <>
                  <h2 className="text-2xl font-black mb-3">챌린지 시작하기</h2>
                  <p className="text-gray-400 text-sm font-bold">건강한 습관을 만들어보세요 →</p>
                </>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* 처리 중·확인 대기 OCR draft 카드 (우측하단 floating) */}
      <ActiveDraftsCard
        drafts={activeDrafts}
        onSelect={(draftId) => router.push(`/ocr/result?draft_id=${draftId}`)}
        onDelete={handleDeleteDraft}
      />
    </div>
  )
}

// Suspense로 감싸서 export (useSearchParams 필수)
export default function MainPage() {
  return (
    <Suspense fallback={<MainSkeleton />}>
      <MainPageContent />
    </Suspense>
  )
}
