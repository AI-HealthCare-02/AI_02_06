'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import { streamSSE } from '@/lib/sseClient'
import { useProfile } from '@/contexts/ProfileContext'

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
  const [guides, setGuides] = useState([])
  const [latestGuide, setLatestGuide] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

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
  const generateGuide = useCallback(async (profileId, signal) => {
    const enqueueRes = await api.post(`/api/v1/lifestyle-guides/generate?profile_id=${profileId}`, null)
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
    setGuides(prev => [pendingGuide, ...prev])
    setLatestGuide(pendingGuide)

    for await (const payload of watchGuideStatus(pendingId, signal)) {
      if (payload.status === 'ready') {
        setGuides(prev => prev.map(g => (g.id === pendingId ? payload : g)))
        setLatestGuide(payload)
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
    // SSE 가 ready 없이 종료된 경우 — placeholder 정리 후 throw
    setGuides(prev => prev.filter(g => g.id !== pendingId))
    setLatestGuide(prev => (prev?.id === pendingId ? null : prev))
    throw new Error('가이드 생성이 완료되지 않았어요. 잠시 후 다시 시도해주세요.')
  }, [])

  const refetchGuides = useCallback(
    () => fetchGuides(selectedProfileId),
    [fetchGuides, selectedProfileId],
  )

  return (
    <LifestyleGuideContext.Provider value={{
      guides,
      latestGuide,
      isLoading,
      generateGuide,
      deleteGuide,
      refetchGuides,
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
