'use client'

// OCR Draft 도메인 — TanStack Query adapter (PR-B 마이그레이션).
//
// 외부 API: activeDrafts, isLoading, removeDraftLocally, refetchDrafts +
// useOcrEntryNavigator hook.

import { createContext, useCallback, useContext, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'
import { qk, STALE } from '@/queries/keys'

const OcrDraftContext = createContext(null)

export function OcrDraftProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const qc = useQueryClient()

  const listQuery = useQuery({
    queryKey: qk.ocrDraft.activeList(selectedProfileId),
    enabled: !!selectedProfileId,
    staleTime: STALE.ocrDraft,
    queryFn: async () => {
      const res = await api.get('/api/v1/ocr/drafts/active', {
        params: { profile_id: selectedProfileId },
      })
      return res.data?.drafts || []
    },
  })
  const activeDrafts = listQuery.data || []
  const isLoading = listQuery.isLoading

  const refetchDrafts = useCallback(() => listQuery.refetch(), [listQuery])

  // result 페이지가 confirm/abandon 후 sessionStorage 에 남긴 marker 를 다음
  // main 진입 시 cache 에서 즉시 제거 — 깜빡임 방지.
  const removeDraftLocally = useCallback(
    (draftId) => {
      qc.setQueryData(qk.ocrDraft.activeList(selectedProfileId), (prev = []) =>
        prev.filter((d) => d.draft_id !== draftId),
      )
    },
    [qc, selectedProfileId],
  )

  useEffect(() => {
    if (typeof window === 'undefined') return
    const consumedId = sessionStorage.getItem('ocr_consumed_draft_id')
    if (consumedId) {
      removeDraftLocally(consumedId)
      sessionStorage.removeItem('ocr_consumed_draft_id')
    }
  }, [removeDraftLocally])

  return (
    <OcrDraftContext.Provider
      value={{
        activeDrafts,
        isLoading,
        removeDraftLocally,
        refetchDrafts,
      }}
    >
      {children}
    </OcrDraftContext.Provider>
  )
}

export function useOcrDraft() {
  const ctx = useContext(OcrDraftContext)
  if (!ctx) throw new Error('useOcrDraft must be used within OcrDraftProvider')
  return ctx
}

/**
 * "처방전 등록" 진입의 단일 정책 — UI 어디서 호출하든 동일 동작.
 *
 * 활성 draft (확인 대기 ready / 처리 중 pending) 가 있으면 result 로,
 * 없으면 새 업로드(/ocr) 로.
 */
export function useOcrEntryNavigator() {
  const router = useRouter()
  const { activeDrafts } = useOcrDraft()
  return useCallback(() => {
    const draft = activeDrafts[0]
    router.push(draft ? `/ocr/result?draft_id=${draft.draft_id}` : '/ocr')
  }, [activeDrafts, router])
}
