'use client'

// Medication 도메인 — TanStack Query adapter (PR-B 마이그레이션).
//
// 외부 API 시그니처 100% 호환:
//   medications, activeMedications, completedMedications, isLoading,
//   updateMedication, deleteMedication, deleteMedications, deactivateMedication,
//   getDrugInfo, refetchMedications.
//
// 변경 핵심:
// - list GET 을 useQuery (staleTime 30초, profile 전환 시 새 key 로 자동 refetch).
// - drug-info 는 useQuery 캐시 (medication 별 query key) — 마운트 후 lazy fetch.
// - mutation onSuccess 에서 list cache patch + prescription-groups 키 invalidate
//   (active count 변화 → 그룹의 has_active_medication 라벨 동기화).

import { createContext, useCallback, useContext } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'
import { qk, STALE } from '@/queries/keys'

const MedicationContext = createContext(null)

export function MedicationProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const qc = useQueryClient()

  // ── 1) list query ─────────────────────────────────────────────────
  const listQuery = useQuery({
    queryKey: qk.medications.list(selectedProfileId),
    enabled: !!selectedProfileId,
    staleTime: STALE.medications,
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/medications?profile_id=${selectedProfileId}`)
      return data || []
    },
  })
  const medications = listQuery.data || []
  const isLoading = listQuery.isLoading

  // ── 처방전 그룹 detail cache 의 medications 배열을 직접 patch ────────
  // PrescriptionGroupContext 의 groupsById 는 useQueries(enabled: false) 로
  // cache 만 읽기 때문에 invalidate 만으로는 즉시 갱신되지 않는다. 약 개별
  // mutation 직후 상세 페이지에서 즉시 반영되도록 detail cache 를 직접
  // setQueryData 한다.
  const patchPrescriptionGroupDetails = useCallback(
    (mutator) => {
      const entries = qc.getQueriesData({ queryKey: ['prescription-groups', 'detail'] })
      for (const [key, group] of entries) {
        if (!group?.medications) continue
        const next = mutator(group)
        if (next !== group) qc.setQueryData(key, next)
      }
    },
    [qc],
  )

  // ── 2) mutations ──────────────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: async ({ id, patch }) => {
      const { data } = await api.patch(`/api/v1/medications/${id}`, patch)
      return data
    },
    onSuccess: (updated, { id }) => {
      qc.setQueryData(qk.medications.list(selectedProfileId), (prev = []) =>
        prev.map((m) => (m.id === id ? updated : m)),
      )
      patchPrescriptionGroupDetails((group) => {
        const idx = group.medications.findIndex((m) => m.id === id)
        if (idx === -1) return group
        const nextMeds = [...group.medications]
        nextMeds[idx] = updated
        return { ...group, medications: nextMeds }
      })
      // medicine_name 변경 시 drug-info 도 stale → invalidate.
      qc.invalidateQueries({ queryKey: qk.medications.detail(id) })
      // active 변화 가능성 → prescription-groups 라벨 동기화.
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      await api.delete(`/api/v1/medications/${id}`)
      return id
    },
    onSuccess: (id) => {
      qc.setQueryData(qk.medications.list(selectedProfileId), (prev = []) =>
        prev.filter((m) => m.id !== id),
      )
      patchPrescriptionGroupDetails((group) => {
        const filtered = group.medications.filter((m) => m.id !== id)
        if (filtered.length === group.medications.length) return group
        return { ...group, medications: filtered }
      })
      qc.removeQueries({ queryKey: qk.medications.detail(id) })
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
    },
  })

  const bulkDeleteMutation = useMutation({
    mutationFn: async (ids) => {
      await Promise.all(ids.map((id) => api.delete(`/api/v1/medications/${id}`)))
      return ids
    },
    onSuccess: (ids) => {
      const idSet = new Set(ids)
      qc.setQueryData(qk.medications.list(selectedProfileId), (prev = []) =>
        prev.filter((m) => !idSet.has(m.id)),
      )
      patchPrescriptionGroupDetails((group) => {
        const filtered = group.medications.filter((m) => !idSet.has(m.id))
        if (filtered.length === group.medications.length) return group
        return { ...group, medications: filtered }
      })
      ids.forEach((id) => qc.removeQueries({ queryKey: qk.medications.detail(id) }))
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
    },
  })

  // 외부 호환 API.
  const updateMedication = useCallback(
    (id, patch) => updateMutation.mutateAsync({ id, patch }),
    [updateMutation],
  )
  const deleteMedication = useCallback((id) => deleteMutation.mutateAsync(id), [deleteMutation])
  const deleteMedications = useCallback(
    (ids) => bulkDeleteMutation.mutateAsync(ids),
    [bulkDeleteMutation],
  )
  const deactivateMedication = useCallback(
    (id) => updateMutation.mutateAsync({ id, patch: { is_active: false } }),
    [updateMutation],
  )

  // ── drug-info lazy cache (medication 별 query key) ────────────────
  // 호출자가 promise 를 직접 await — fetchQuery 로 dedupe + cache 보장.
  const getDrugInfo = useCallback(
    async (medId) => {
      return qc.fetchQuery({
        queryKey: qk.medications.detail(medId),
        // drug-info 는 LLM 결과라 변동 거의 없음 → 5분 staleTime.
        staleTime: 5 * 60 * 1000,
        queryFn: async () => {
          const { data } = await api.get(`/api/v1/medications/${medId}/drug-info`)
          return data
        },
      })
    },
    [qc],
  )

  // ── computed selectors ──────────────────────────────
  const activeMedications = medications.filter((m) => m.is_active)
  const completedMedications = medications.filter((m) => !m.is_active)

  const refetchMedications = useCallback(() => listQuery.refetch(), [listQuery])

  return (
    <MedicationContext.Provider
      value={{
        medications,
        activeMedications,
        completedMedications,
        isLoading,
        updateMedication,
        deleteMedication,
        deleteMedications,
        deactivateMedication,
        getDrugInfo,
        refetchMedications,
      }}
    >
      {children}
    </MedicationContext.Provider>
  )
}

export function useMedication() {
  const ctx = useContext(MedicationContext)
  if (!ctx) throw new Error('useMedication must be used within MedicationProvider')
  return ctx
}
