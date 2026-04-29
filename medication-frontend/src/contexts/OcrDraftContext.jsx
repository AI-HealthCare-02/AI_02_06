'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

const OcrDraftContext = createContext(null)

/**
 * OCR Draft 단일 진실.
 *
 * - 활성 draft 목록 (BE 가 사용자 단위로 자동 필터링) 을 한 곳에서 관리.
 * - selectedProfileId 변경 시 자동 refetch.
 * - removeDraftLocally: result 페이지가 sessionStorage 에 남긴 marker 를
 *   다음 main 진입 시 즉시 반영하기 위해 — Provider 내부 useEffect 가 자동 처리.
 */
export function OcrDraftProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const [activeDrafts, setActiveDrafts] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const fetchDrafts = useCallback(async (profileId) => {
    if (!profileId) {
      setActiveDrafts([])
      return
    }
    setIsLoading(true)
    try {
      const res = await api.get('/api/v1/ocr/drafts/active', {
        params: { profile_id: profileId },
      })
      setActiveDrafts(res.data?.drafts || [])
    } catch {
      setActiveDrafts([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  // 프로필 전환 시 이전 프로필 drafts 가 잠시도 보이지 않도록 fetch 전에 즉시 비움.
  // (다른 Context 들은 array 단위로 페이지가 ProfileContext 의 selectedProfileId 변경을
  //  watch 해 자체 reset 하지만, ActiveDraftsCard 는 main 페이지에 floating 되어 있어
  //  Context 가 swap 시점을 직접 책임진다.)
  useEffect(() => {
    setActiveDrafts([])
    if (!selectedProfileId) return
    fetchDrafts(selectedProfileId)
  }, [selectedProfileId, fetchDrafts])

  const refetchDrafts = useCallback(
    () => fetchDrafts(selectedProfileId),
    [fetchDrafts, selectedProfileId],
  )

  const removeDraftLocally = useCallback((draftId) => {
    setActiveDrafts(prev => prev.filter(d => d.draft_id !== draftId))
  }, [])

  // sessionStorage marker 자동 처리 (mount 시 1회)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const consumedId = sessionStorage.getItem('ocr_consumed_draft_id')
    if (consumedId) {
      removeDraftLocally(consumedId)
      sessionStorage.removeItem('ocr_consumed_draft_id')
    }
  }, [removeDraftLocally])

  return (
    <OcrDraftContext.Provider value={{
      activeDrafts,
      isLoading,
      removeDraftLocally,
      refetchDrafts,
    }}>
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
 * 활성 draft (확인 대기 중인 ready, 처리 중인 pending) 가 있으면 result 화면으로
 * 보내 사용자가 진행을 마치도록 유도하고, 없을 때만 새 업로드(/ocr) 로 보낸다.
 *
 * 이 정책은 main 페이지의 큰 버튼 / medication 페이지의 + 버튼 / Navigation 의
 * 메뉴 등 모든 진입점에서 동일해야 하므로 hook 으로 한 곳에 둔다.
 */
export function useOcrEntryNavigator() {
  const router = useRouter()
  const { activeDrafts } = useOcrDraft()
  return useCallback(() => {
    const draft = activeDrafts[0]
    router.push(draft ? `/ocr/result?draft_id=${draft.draft_id}` : '/ocr')
  }, [activeDrafts, router])
}
