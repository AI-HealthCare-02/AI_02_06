// 처방전 그룹 도메인 — list / detail / mutations.
// cross-cascade: 그룹 삭제 시 BE 가 medication + 그 프로필 active 가이드 + 미시작
// 챌린지를 함께 정리한다. 따라서 mutation.onSuccess 에서 lifestyle-guides /
// challenges 키도 invalidate 한다.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import api from '@/lib/api'
import { qk } from '@/queries/keys'

export function usePrescriptionGroups(profileId, { search = '' } = {}) {
  return useQuery({
    queryKey: qk.prescriptionGroups.list(profileId, search),
    enabled: !!profileId,
    queryFn: async () => {
      const params = new URLSearchParams({ profile_id: profileId })
      if (search.trim()) params.set('search', search.trim())
      const { data } = await api.get(`/api/v1/prescription-groups?${params.toString()}`)
      return data || []
    },
  })
}

export function usePrescriptionGroupDetail(groupId) {
  return useQuery({
    queryKey: qk.prescriptionGroups.detail(groupId),
    enabled: !!groupId,
    queryFn: async () => {
      const { data } = await api.get(`/api/v1/prescription-groups/${groupId}`)
      return data
    },
  })
}

// 그룹 부분 수정 (병원/진료과/처방일 등). 응답으로 detail/list 모두 갱신.
export function useUpdatePrescriptionGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ groupId, patch }) => {
      const { data } = await api.patch(`/api/v1/prescription-groups/${groupId}`, patch)
      return data
    },
    onSuccess: (data, { groupId }) => {
      qc.setQueryData(qk.prescriptionGroups.detail(groupId), data)
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
    },
  })
}

// 그룹 단위 복용 완료 처리 — 그룹 안 모든 medication 비활성화.
// 영향: 그룹의 has_active_medication 라벨 + 그 medication 사용처 (Medication store).
export function useMarkPrescriptionGroupCompleted() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (groupId) => {
      const { data } = await api.patch(`/api/v1/prescription-groups/${groupId}/complete`)
      return data
    },
    onSuccess: (data, groupId) => {
      qc.setQueryData(qk.prescriptionGroups.detail(groupId), data)
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
    },
  })
}

// 그룹 삭제 — 단일 진입점에서 cross-cascade 까지 invalidate.
export function useDeletePrescriptionGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (groupId) => {
      await api.delete(`/api/v1/prescription-groups/${groupId}`)
      return groupId
    },
    onSuccess: (groupId) => {
      // 자기 도메인 + cascade 영향 도메인 한 번에 invalidate.
      qc.removeQueries({ queryKey: qk.prescriptionGroups.detail(groupId) })
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
      qc.invalidateQueries({ queryKey: qk.lifestyleGuides.all() })
      qc.invalidateQueries({ queryKey: qk.challenges.all() })
    },
  })
}
