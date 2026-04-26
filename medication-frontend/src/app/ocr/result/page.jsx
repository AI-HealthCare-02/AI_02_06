'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { streamSSE } from '@/lib/sseClient'

const TERMINAL_ERROR_MESSAGES = {
  no_text: '이미지에서 텍스트를 찾지 못했어요.',
  no_candidates: '약품 정보를 인식하지 못했어요.',
  failed: '처리 중 오류가 발생했어요.',
}

/**
 * SSE 연결을 ready/terminal 까지 자동 재연결하며 await for-of 로 소비.
 * timeout event 시 새 연결 — 무한 재시도 (cancel 또는 ready 까지).
 */
async function* watchDraftStatus(draftId, signal) {
  while (true) {
    let timedOut = false
    for await (const ev of streamSSE(`/api/v1/ocr/draft/${draftId}/stream`, { signal })) {
      if (ev.event === 'update') yield ev.data
      else if (ev.event === 'timeout') { timedOut = true; break }
      else if (ev.event === 'error') throw new Error(ev.data?.detail || 'sse error')
    }
    if (!timedOut) return
  }
}

// 로딩 스켈레톤 UI
function ResultSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-32 animate-pulse">
      <div className="h-48 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="flex justify-between items-center mb-8 px-1">
          <div className="h-6 w-32 bg-gray-200 rounded-lg" />
          <div className="h-6 w-20 bg-gray-200 rounded-lg" />
        </div>
        <div className="space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-48 bg-white rounded-3xl border border-gray-100 shadow-sm" />
          ))}
        </div>
        <div className="mt-12 flex gap-4">
          <div className="flex-1 h-16 bg-white border border-gray-200 rounded-2xl" />
          <div className="flex-1 h-16 bg-blue-100 rounded-2xl" />
        </div>
      </div>
    </div>
  )
}

function OcrResultContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const draftId = searchParams.get('draft_id')

  const [isLoading, setIsLoading] = useState(true)
  const [meds, setMeds] = useState([])
  const [prescriptionDate, setPrescriptionDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    // [뒤로가기 기능] URL에 draft_id가 없으면 튕겨냅니다.
    if (!draftId) {
      router.push('/ocr')
      return
    }

    // SSE 로 ai-worker 진행 상태를 수신. status='ready' 까지 isLoading=true 유지
    // -> 사용자에게 ResultSkeleton 노출. terminal status 시 안내 + /ocr 복귀.
    // (단발 GET 폐기 — 이미 ready 인 draft 도 SSE 가 첫 yield 즉시 보내므로 비용 동일)
    const abortController = new AbortController()

    const consumeStream = async () => {
      try {
        for await (const payload of watchDraftStatus(draftId, abortController.signal)) {
          const { status, medicines } = payload
          if (status === 'ready') {
            setMeds(medicines || [])
            setPrescriptionDate(medicines?.[0]?.dispensed_date || '')
            setIsLoading(false)
            return
          }
          if (status in TERMINAL_ERROR_MESSAGES) {
            alert(`${TERMINAL_ERROR_MESSAGES[status]} 다시 촬영해주세요.`)
            router.push('/ocr')
            return
          }
          // status='pending' — 다음 update 대기 (스켈레톤 유지)
        }
      } catch (err) {
        if (abortController.signal.aborted) return
        alert('데이터가 만료되었거나 불러올 수 없습니다. 다시 촬영해주세요.')
        router.push('/ocr')
      }
    }

    consumeStream()
    return () => abortController.abort()
  }, [draftId, router])

  // 사용자가 텍스트를 수정할 때 상태 업데이트하는 함수
  const handleInputChange = (index, field, value) => {
    const updatedMeds = [...meds]
    updatedMeds[index][field] = value
    setMeds(updatedMeds)
  }

  // 약품 삭제 기능
  const handleDelete = (index) => {
    const updatedMeds = meds.filter((_, i) => i !== index)
    setMeds(updatedMeds)
  }

  // 다시 촬영 — 현재 draft 를 백엔드에서 폐기 처리한 뒤 업로드 페이지로 이동.
  // 폐기 실패해도 사용자 흐름은 막지 않음 (UX 우선, 24h 후 자동 정리됨).
  const handleRetake = async () => {
    if (draftId) {
      try {
        await api.delete(`/api/v1/ocr/draft/${draftId}`)
      } catch {
        // ignore — 사용자 흐름 차단하지 않음
      }
    }
    router.push('/ocr')
  }

  // 최종 확인 버튼 (Phase 3으로 연결될 부분)
  const handleConfirm = async () => {
    if (isSubmitting) return
    if (meds.length === 0) {
      alert('등록할 약이 없습니다.')
      return
    }

    setIsSubmitting(true)
    try {
      // 처방일을 모든 약품에 공통 적용
      const confirmedMedicines = meds.map(med => ({
        ...med,
        dispensed_date: prescriptionDate || null,
      }))
      await api.post('/api/v1/ocr/confirm', {
        draft_id: draftId,
        confirmed_medicines: confirmedMedicines,
      }, { timeout: 60000 })

      // confirm 직후 main 페이지의 활성 카드에서 즉시 제거되도록 마킹.
      // (client cache 로 main useEffect 재실행 보장이 안 되므로 단방향 신호)
      sessionStorage.setItem('ocr_consumed_draft_id', draftId)
      alert('저장 완료! 복약 목록에서 확인해보세요.')
      router.push('/medication')

    } catch (error) {
      alert('저장 중 오류가 발생했습니다.')
      setIsSubmitting(false)
    }
  }

  if (isLoading) return <ResultSkeleton />

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      {/* 상단 헤더 영역 — ← 는 메인으로, "다시 촬영" 은 /ocr 로 분리 */}
      <div className="bg-white border-b border-gray-200 px-10 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push('/main')}
          className="text-gray-400 hover:text-black cursor-pointer text-xl"
          aria-label="메인으로 이동"
        >
          ←
        </button>
        <div>
          <h1 className="font-bold text-gray-900">처방전 확인 및 수정</h1>
          <p className="text-xs text-gray-400">오탈자가 있다면 직접 수정해주세요</p>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-10 py-8 space-y-4">
        {/* 안내 배너 */}
        <div className="bg-blue-50 rounded-2xl p-4 flex items-center gap-3">
          <span className="text-2xl">!</span>
          <div>
            <p className="font-semibold text-blue-800 text-sm">확인해주세요!</p>
            <p className="text-blue-600 text-xs">AI가 인식한 결과입니다. 틀린 글자는 터치해서 고칠 수 있어요.</p>
          </div>
        </div>

        {/* 처방일 (처방전 전체 공통) */}
        <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-gray-900">처방일</p>
            <p className="text-xs text-gray-400 mt-0.5">처방전에 적힌 날짜를 확인해주세요</p>
          </div>
          <input
            type="date"
            value={prescriptionDate}
            onChange={(e) => setPrescriptionDate(e.target.value)}
            className="text-sm font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50"
          />
        </div>

        {/* 약물 리스트 카드 (수정 가능한 Input UI 적용) */}
        <div className="space-y-4 mb-10">
          {meds.map((med, i) => (
            <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 animate-in fade-in slide-in-from-bottom-2 duration-300" style={{ animationDelay: `${i * 100}ms` }}>
              <div className="flex justify-between items-start mb-4 gap-4">
                <input
                  type="text"
                  value={med.medicine_name || ''}
                  onChange={(e) => handleInputChange(i, 'medicine_name', e.target.value)}
                  className="font-bold text-lg text-gray-900 border-b-2 border-transparent hover:border-blue-200 focus:border-blue-500 focus:outline-none bg-transparent w-full transition-colors"
                  placeholder="약품명 입력"
                />
                <button onClick={() => handleDelete(i)} className="text-gray-300 hover:text-red-400 mt-1 cursor-pointer">
                  <Trash2 size={20} />
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                  <p className="text-[10px] text-gray-500 mb-1 px-1">1회 복용량</p>
                  <input
                    type="text"
                    value={med.dose_per_intake || ''}
                    onChange={(e) => handleInputChange(i, 'dose_per_intake', e.target.value)}
                    className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                    placeholder="예: 1정"
                  />
                </div>
                <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                  <p className="text-[10px] text-gray-500 mb-1 px-1">1일 복용 횟수</p>
                  <input
                    type="number"
                    value={med.daily_intake_count || ''}
                    onChange={(e) => handleInputChange(i, 'daily_intake_count', Number(e.target.value))}
                    className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                    placeholder="예: 3"
                  />
                </div>
                <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                  <p className="text-[10px] text-gray-500 mb-1 px-1">총 복용 일수</p>
                  <input
                    type="number"
                    value={med.total_intake_days || ''}
                    onChange={(e) => handleInputChange(i, 'total_intake_days', Number(e.target.value))}
                    className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                    placeholder="예: 5"
                  />
                </div>
                <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                  <p className="text-[10px] text-gray-500 mb-1 px-1">복용 방법</p>
                  <input
                    type="text"
                    value={med.intake_instruction || ''}
                    onChange={(e) => handleInputChange(i, 'intake_instruction', e.target.value)}
                    className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                    placeholder="예: 식후 30분"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 하단 액션 버튼 */}
        <div className="flex gap-3 pb-10">
          <button
            onClick={handleRetake}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
          >
            다시 촬영
          </button>
          <button
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="flex-1 bg-gray-900 text-white py-4 rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:bg-gray-800 enabled:cursor-pointer">
            {isSubmitting ? '저장 중...' : '수정 완료 및 저장'}
          </button>
        </div>
      </div>

      <BottomNav />
    </main>
  )
}

// Suspense로 감싸서 export (useSearchParams 필수)
export default function OcrResultPage() {
  return (
    <Suspense fallback={<ResultSkeleton />}>
      <OcrResultContent />
    </Suspense>
  )
}
