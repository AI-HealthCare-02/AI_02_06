'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

const ChallengeContext = createContext(null)

/**
 * Challenge 단일 진실.
 *
 * - 프로필별 모든 challenges (모든 status, all is_active 포함) 를 한 번 fetch.
 *   탭별 / 가이드별 분리는 client-side filter (selectors).
 * - selectedProfileId 변경 시 자동 refetch.
 * - mutation (start / update / delete) 모두 응답으로 setChallenges 직접 갱신.
 */
export function ChallengeProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const [challenges, setChallenges] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const fetchChallenges = useCallback(async (profileId) => {
    if (!profileId) return
    setIsLoading(true)
    try {
      const res = await api.get(`/api/v1/challenges?profile_id=${profileId}`)
      setChallenges(res.data || [])
    } catch (err) {
      if (err.response?.status !== 401) console.error('챌린지 조회 실패:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!selectedProfileId) {
      setChallenges([])
      return
    }
    fetchChallenges(selectedProfileId)
  }, [selectedProfileId, fetchChallenges])

  // ── 응답 기반 mutation ──────────────────────────────
  const startChallenge = useCallback(async (id, { difficulty, target_days } = {}) => {
    const payload = {}
    if (difficulty !== undefined) payload.difficulty = difficulty
    if (target_days !== undefined) payload.target_days = target_days
    const url = `/api/v1/challenges/${id}/start`
    const { data: updated } = Object.keys(payload).length > 0
      ? await api.patch(url, payload)
      : await api.patch(`/api/v1/challenges/${id}`, { is_active: true })
    setChallenges(prev => prev.map(c => (c.id === id ? { ...c, ...updated } : c)))
    return updated
  }, [])

  const updateChallenge = useCallback(async (id, patch) => {
    const { data: updated } = await api.patch(`/api/v1/challenges/${id}`, patch)
    setChallenges(prev => prev.map(c => (c.id === id ? { ...c, ...updated } : c)))
    return updated
  }, [])

  const deleteChallenge = useCallback(async (id) => {
    await api.delete(`/api/v1/challenges/${id}`)
    setChallenges(prev => prev.filter(c => c.id !== id))
  }, [])

  // ── computed selectors ──────────────────────────────
  const activeChallenges = challenges.filter(
    c => c.challenge_status === 'IN_PROGRESS' && c.is_active,
  )
  const completedChallenges = challenges.filter(c => c.challenge_status === 'COMPLETED')
  const unstartedByGuide = (guideId) => challenges.filter(
    c => c.guide_id === guideId && !c.is_active && c.challenge_status !== 'DELETED',
  )
  const challengesByGuide = (guideId) => challenges.filter(c => c.guide_id === guideId)

  const refetchChallenges = useCallback(
    () => fetchChallenges(selectedProfileId),
    [fetchChallenges, selectedProfileId],
  )

  return (
    <ChallengeContext.Provider value={{
      challenges,
      activeChallenges,
      completedChallenges,
      unstartedByGuide,
      challengesByGuide,
      isLoading,
      startChallenge,
      updateChallenge,
      deleteChallenge,
      refetchChallenges,
    }}>
      {children}
    </ChallengeContext.Provider>
  )
}

export function useChallenge() {
  const ctx = useContext(ChallengeContext)
  if (!ctx) throw new Error('useChallenge must be used within ChallengeProvider')
  return ctx
}
