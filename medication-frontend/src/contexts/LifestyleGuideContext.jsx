'use client'

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import api from '@/lib/api'
import { streamSSE } from '@/lib/sseClient'
import { useProfile } from '@/contexts/ProfileContext'
import { useChallenge } from '@/contexts/ChallengeContext'

const LifestyleGuideContext = createContext(null)

const GUIDE_TERMINAL_ERROR_MESSAGES = {
  no_active_meds: '활성 약물이 없어 가이드를 만들 수 없어요. 복약 등록 후 다시 시도해주세요.',
  failed: '가이드 생성 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.',
}

/**
 * 가이드 생성 SSE 를 ready/terminal 까지 자동 재연결하며 await for-of 로 소비.
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

/**
 * LifestyleGuide 단일 진실.
 *
 * - 프로필별 가이드 list + latest 를 한 곳에서 관리.
 * - generateGuide 가 SSE 진행 중에도 store 의 placeholder/ready 교체를 자동 처리.
 *   페이지는 promise 결과만 await 하면 됨.
 * - deleteGuide 응답 후 list 에서 in-place 제거.
 */
export function LifestyleGuideProvider({ children }) {
  const { selectedProfileId } = useProfile()
  // 가이드 ready 시 BE 가 INSERT 한 챌린지를 ChallengeContext store 에 union.
  // ChallengeProvider 가 상위에 mount 되어 있어야 한다 (layout.js 참조).
  const { appendChallenges } = useChallenge()
  const [guides, setGuides] = useState([])
  const [latestGuide, setLatestGuide] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  // 사용자가 생성 중인 가이드를 직접 삭제한 경우, SSE 의 "Guide not found" error
  // 가 generateGuide 까지 throw 되어 토스트 두 개 ("Guide not found." + "가이드가
  // 삭제되었습니다") 가 동시에 뜨던 문제를 해결하기 위한 silent-cancel ref.
  const cancelledGuideIds = useRef(new Set())

  const fetchGuides = useCallback(async (profileId) => {
    if (!profileId) return
    setIsLoading(true)
    try {
      const [latestRes, listRes] = await Promise.allSettled([
        api.get(`/api/v1/lifestyle-guides/latest?profile_id=${profileId}`),
        api.get(`/api/v1/lifestyle-guides?profile_id=${profileId}`),
      ])
      const list = listRes.status === 'fulfilled' ? (listRes.value.data || []) : []
      setGuides(list)
      if (latestRes.status === 'fulfilled') {
        setLatestGuide(latestRes.value.data)
      } else if (list.length > 0) {
        setLatestGuide(list[0])
      } else {
        setLatestGuide(null)
      }
    } catch (err) {
      if (err.response?.status !== 401) console.error('가이드 조회 실패:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!selectedProfileId) {
      setGuides([])
      setLatestGuide(null)
      return
    }
    fetchGuides(selectedProfileId)
  }, [selectedProfileId, fetchGuides])

  // ── 응답 기반 mutation ──────────────────────────────

  const deleteGuide = useCallback(async (id) => {
    // SSE 진행 중인 placeholder 도 삭제될 수 있음 — 그 경우 generateGuide 측의
    // SSE error 가 silent 처리되도록 cancelled set 에 미리 등록.
    cancelledGuideIds.current.add(id)
    await api.delete(`/api/v1/lifestyle-guides/${id}`)
    setGuides(prev => prev.filter(g => g.id !== id))
    setLatestGuide(prev => (prev?.id === id ? null : prev))
  }, [])

  /**
   * 가이드 생성 (SSE wrap):
   *  1) POST → 즉시 placeholder 를 store 에 삽입 (스켈레톤 렌더 유도)
   *  2) SSE update 수신
   *  3) ready 도달 시 store 의 placeholder 를 ready 결과로 교체
   *  4) terminal error 시 placeholder 제거 + 에러 throw
   *
   * 페이지는 promise 의 ready guide 를 받거나 throw 를 catch 하면 됨.
   */
  const generateGuide = useCallback(async (profileId, prescriptionGroupId, signal) => {
    if (!prescriptionGroupId) {
      // 호출자(페이지) 가 처방전 선택 모달을 열어 group_id 를 보장해야 한다.
      // BE 는 group_id 필수라 fallback 없음 — 명확한 에러로 throw.
      throw new Error('처방전을 먼저 선택해주세요.')
    }
    const params = new URLSearchParams({
      profile_id: profileId,
      prescription_group_id: prescriptionGroupId,
    })
    const enqueueRes = await api.post(
      `/api/v1/lifestyle-guides/generate?${params.toString()}`,
      null,
    )
    const pendingId = enqueueRes.data.id

    // Phase B dedupe hit — BE 가 같은 입력 fingerprint 의 ready 가이드를
    // 즉시 반환. SSE 건너뛰고 가이드 + 챌린지 한 번에 fetch.
    if (enqueueRes.data.status === 'ready') {
      const { data: ready } = await api.get(`/api/v1/lifestyle-guides/${pendingId}`)
      setGuides(prev => {
        const exists = prev.some(g => g.id === ready.id)
        return exists ? prev.map(g => (g.id === ready.id ? ready : g)) : [ready, ...prev]
      })
      setLatestGuide(ready)
      try {
        const { data: chs } = await api.get(`/api/v1/lifestyle-guides/${pendingId}/challenges`)
        appendChallenges(chs)
      } catch (err) {
        if (err.response?.status !== 401) console.error('dedupe 챌린지 sync 실패:', err)
      }
      ready.deduped = true  // page 측에서 토스트 분기 가능
      return ready
    }

    const pendingGuide = {
      id: pendingId,
      profile_id: profileId,
      status: 'pending',
      content: {},
      medication_snapshot: [],
      created_at: new Date().toISOString(),
      processed_at: null,
    }
    setGuides(prev => [pendingGuide, ...prev])
    // latestGuide 는 ready 일 때만 갱신 — 생성 중에도 페이지가 직전 ready
    // 가이드를 selectedGuide 로 유지할 수 있게 하기 위함.

    try {
      for await (const payload of watchGuideStatus(pendingId, signal)) {
        if (payload.status === 'ready') {
          setGuides(prev => prev.map(g => (g.id === pendingId ? payload : g)))
          setLatestGuide(payload)
          // 가이드와 함께 BE 가 INSERT 한 챌린지를 ChallengeContext store 에 즉시 union
          // → 페이지 reload 없이 추천 챌린지 카드/배너가 곧바로 렌더된다.
          try {
            const { data: newChallenges } = await api.get(
              `/api/v1/lifestyle-guides/${pendingId}/challenges`,
            )
            appendChallenges(newChallenges)
          } catch (err) {
            if (err.response?.status !== 401) console.error('가이드 챌린지 sync 실패:', err)
          }
          return payload
        }
        if (payload.status in GUIDE_TERMINAL_ERROR_MESSAGES) {
          setGuides(prev => prev.filter(g => g.id !== pendingId))
          setLatestGuide(prev => (prev?.id === pendingId ? null : prev))
          const err = new Error(GUIDE_TERMINAL_ERROR_MESSAGES[payload.status])
          err.terminal_status = payload.status
          throw err
        }
      }
    } catch (err) {
      // 사용자가 생성 중 placeholder 를 직접 삭제한 경우 — silent return.
      // (deleteGuide 가 띄우는 "가이드가 삭제되었습니다" 토스트만 보이게.)
      if (cancelledGuideIds.current.has(pendingId)) {
        cancelledGuideIds.current.delete(pendingId)
        return null
      }
      setGuides(prev => prev.filter(g => g.id !== pendingId))
      setLatestGuide(prev => (prev?.id === pendingId ? null : prev))
      throw err
    }
    // SSE 가 ready 없이 종료된 경우 — placeholder 정리 후 throw
    setGuides(prev => prev.filter(g => g.id !== pendingId))
    setLatestGuide(prev => (prev?.id === pendingId ? null : prev))
    throw new Error('가이드 생성이 완료되지 않았어요. 잠시 후 다시 시도해주세요.')
  }, [appendChallenges])

  const refetchGuides = useCallback(
    () => fetchGuides(selectedProfileId),
    [fetchGuides, selectedProfileId],
  )

  // ── "추천 챌린지 더 보기" — 노출 카운트만 +5 (LLM 호출 X) ──
  // BE 가 응답으로 갱신된 LifestyleGuideResponse 를 돌려주므로 store 의 가이드를
  // in-place 갱신 (revealed_challenge_count 동기화). 이후 호출자가 챌린지 list
  // 를 다시 fetch 해 ChallengeContext 에 union.
  const revealMoreChallenges = useCallback(async (guideId) => {
    const { data: updated } = await api.post(
      `/api/v1/lifestyle-guides/${guideId}/reveal-more-challenges`,
    )
    setGuides(prev => prev.map(g => (g.id === guideId ? updated : g)))
    setLatestGuide(prev => (prev?.id === guideId ? updated : prev))
    // 새로 노출된 챌린지를 ChallengeContext store 에 union
    try {
      const { data: chs } = await api.get(`/api/v1/lifestyle-guides/${guideId}/challenges`)
      appendChallenges(chs)
    } catch (err) {
      if (err.response?.status !== 401) console.error('reveal more sync 실패:', err)
    }
    return updated
  }, [appendChallenges])

  return (
    <LifestyleGuideContext.Provider value={{
      guides,
      latestGuide,
      isLoading,
      generateGuide,
      deleteGuide,
      refetchGuides,
      revealMoreChallenges,
    }}>
      {children}
    </LifestyleGuideContext.Provider>
  )
}

export function useLifestyleGuide() {
  const ctx = useContext(LifestyleGuideContext)
  if (!ctx) throw new Error('useLifestyleGuide must be used within LifestyleGuideProvider')
  return ctx
}

export { GUIDE_TERMINAL_ERROR_MESSAGES }
