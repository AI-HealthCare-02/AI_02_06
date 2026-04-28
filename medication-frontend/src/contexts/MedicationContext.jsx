'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

const MedicationContext = createContext(null)

/**
 * Medication 단일 진실.
 *
 * - 전체 medications 를 한 번 fetch 후 client-side filter 로 active/completed 분리.
 *   탭 전환 시 추가 GET 없음.
 * - selectedProfileId 변경 시 자동 refetch (Profile 전환 → 약 목록 자동 갱신).
 * - mutation (update / delete / deactivate) 은 응답으로 setMedications 직접 갱신.
 * - drug-info 는 별도 lazy cache. mutation 시 해당 id 의 drug-info 캐시 무효화.
 */
export function MedicationProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const [medications, setMedications] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [drugInfoCache, setDrugInfoCache] = useState({})

  const fetchMedications = useCallback(async (profileId) => {
    if (!profileId) return
    setIsLoading(true)
    try {
      const res = await api.get(`/api/v1/medications?profile_id=${profileId}`)
      setMedications(res.data || [])
    } catch (err) {
      console.error('약품 조회 실패:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // profile 전환 → medications 자동 재로드 + drug-info 캐시 초기화
  useEffect(() => {
    if (!selectedProfileId) {
      setMedications([])
      setDrugInfoCache({})
      return
    }
    fetchMedications(selectedProfileId)
    setDrugInfoCache({})
  }, [selectedProfileId, fetchMedications])

  // ── 응답 기반 mutation ──────────────────────────────
  const updateMedication = useCallback(async (id, patch) => {
    const { data: updated } = await api.patch(`/api/v1/medications/${id}`, patch)
    setMedications(prev => prev.map(m => (m.id === id ? updated : m)))
    // medicine_name 등 변경 시 drug-info 도 stale → 무효화
    setDrugInfoCache(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    return updated
  }, [])

  const deleteMedication = useCallback(async (id) => {
    await api.delete(`/api/v1/medications/${id}`)
    setMedications(prev => prev.filter(m => m.id !== id))
    setDrugInfoCache(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }, [])

  const deleteMedications = useCallback(async (ids) => {
    await Promise.all(ids.map(id => api.delete(`/api/v1/medications/${id}`)))
    const idSet = new Set(ids)
    setMedications(prev => prev.filter(m => !idSet.has(m.id)))
    setDrugInfoCache(prev => {
      const next = { ...prev }
      ids.forEach(id => delete next[id])
      return next
    })
  }, [])

  const deactivateMedication = useCallback(async (id) => {
    return updateMedication(id, { is_active: false })
  }, [updateMedication])

  // ── drug-info lazy cache (LLM 결과, 컴포넌트 생명주기 초월) ────────
  const getDrugInfo = useCallback(async (medId) => {
    if (drugInfoCache[medId]) return drugInfoCache[medId]
    const { data } = await api.get(`/api/v1/medications/${medId}/drug-info`)
    setDrugInfoCache(prev => ({ ...prev, [medId]: data }))
    return data
  }, [drugInfoCache])

  // ── computed selectors ──────────────────────────────
  const activeMedications = medications.filter(m => m.is_active)
  const completedMedications = medications.filter(m => !m.is_active)

  return (
    <MedicationContext.Provider value={{
      // 읽기
      medications,
      activeMedications,
      completedMedications,
      isLoading,
      // mutation (응답 기반)
      updateMedication,
      deleteMedication,
      deleteMedications,
      deactivateMedication,
      // drug-info
      getDrugInfo,
      // 비상
      refetchMedications: () => fetchMedications(selectedProfileId),
    }}>
      {children}
    </MedicationContext.Provider>
  )
}

export function useMedication() {
  const ctx = useContext(MedicationContext)
  if (!ctx) throw new Error('useMedication must be used within MedicationProvider')
  return ctx
}
