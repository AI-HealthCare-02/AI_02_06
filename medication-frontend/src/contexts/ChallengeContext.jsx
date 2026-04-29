'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import toast from 'react-hot-toast'
import api, { showError } from '@/lib/api'
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

/**
 * "챌린지 시작" 단일 정책 — 어디서 호출하든 StartChallengeModal 로 확인 후 시작.
 *
 * 사용:
 *   const { startTarget, isStarting, requestStart, cancelStart, confirmStart } = useChallengeStart()
 *   <button onClick={() => requestStart(challenge)}>시작하기</button>
 *   {startTarget && (
 *     <StartChallengeModal
 *       challenge={startTarget}
 *       onConfirm={(d, t) => confirmStart(d, t).then(...) }
 *       onClose={cancelStart}
 *       isLoading={isStarting}
 *     />
 *   )}
 *
 * confirmStart 는 성공 시 갱신된 challenge 를 반환, 실패 시 throw — 호출 페이지가
 * toast 문구/후속 동작 (탭 이동, 라우팅 등) 을 직접 결정한다.
 */
export function useChallengeStart() {
  const { startChallenge } = useChallenge()
  const [startTarget, setStartTarget] = useState(null)
  const [isStarting, setIsStarting] = useState(false)

  const requestStart = useCallback((challenge) => {
    if (isStarting) return
    setStartTarget(challenge)
  }, [isStarting])

  const cancelStart = useCallback(() => {
    if (isStarting) return
    setStartTarget(null)
  }, [isStarting])

  const confirmStart = useCallback(async (difficulty, targetDays) => {
    if (!startTarget || isStarting) return null
    setIsStarting(true)
    try {
      const updated = await startChallenge(startTarget.id, {
        difficulty,
        target_days: targetDays,
      })
      setStartTarget(null)
      return updated
    } finally {
      setIsStarting(false)
    }
  }, [startTarget, isStarting, startChallenge])

  return { startTarget, isStarting, requestStart, cancelStart, confirmStart }
}

/**
 * "오늘 완료 체크" 단일 정책 — challenge 객체 받아 PATCH /challenges/{id} 호출.
 *
 * 호출 가드 / 토스트 메시지(완료 시 축하, 중복 시 안내, 실패 시 에러) 까지 hook 이
 * 책임진다. 호출자는 await checkToday(c) 한 줄로 끝.
 *
 * 사용:
 *   const { checkingId, checkToday } = useChallengeCheck()
 *   <button onClick={() => checkToday(challenge)} disabled={checkingId === challenge.id} />
 */
export function useChallengeCheck() {
  const { updateChallenge } = useChallenge()
  const [checkingId, setCheckingId] = useState(null)

  const checkToday = useCallback(async (challenge) => {
    if (checkingId) return null
    const today = new Date().toISOString().split('T')[0]
    const alreadyChecked = challenge.completed_dates?.some(
      (d) => (typeof d === 'string' ? d : d.toISOString?.().split('T')[0]) === today,
    )
    if (alreadyChecked) {
      showError('오늘은 이미 체크했습니다!')
      return null
    }
    setCheckingId(challenge.id)
    try {
      const newDates = [...(challenge.completed_dates || []), today]
      const isCompleted = newDates.length >= challenge.target_days
      const updated = await updateChallenge(challenge.id, {
        completed_dates: newDates,
        challenge_status: isCompleted ? 'COMPLETED' : 'IN_PROGRESS',
      })
      if (updated.challenge_status === 'COMPLETED') {
        toast.success('챌린지를 완료했습니다! 수고하셨어요.')
      }
      return updated
    } catch {
      showError('체크에 실패했습니다.')
      return null
    } finally {
      setCheckingId(null)
    }
  }, [checkingId, updateChallenge])

  return { checkingId, checkToday }
}
