'use client'

/**
 * PrescriptionGroupContext — /medication 카드 list + drill-down detail 의 단일 진실.
 *
 * - 정렬 / 검색 / 탭은 서로 독립적으로 동시 결합 가능 (사용자 합의).
 * - selectedProfileId, sort, search 변경 시 자동 list refetch (BE filter / sort).
 * - statusFilter 는 **클라이언트 측 derived** — BE 응답의 ``has_active_medication``
 *   필드로 즉시 필터. 탭 전환 시마다 추가 GET 호출 없음.
 * - drill-down 페이지가 자체 useState 로 fetch 하지 않도록 ``groupsById`` cache + mutation API 노출.
 * - mutation (update/markCompleted/delete) 은 응답으로 cache + list 직접 갱신.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

export const PRESCRIPTION_SORT = Object.freeze({
  DATE_DESC: 'date_desc',
  DATE_ASC: 'date_asc',
  HOSPITAL_ASC: 'hospital_asc',
  HOSPITAL_DESC: 'hospital_desc',
})

export const PRESCRIPTION_STATUS = Object.freeze({
  ALL: 'all',
  ACTIVE: 'active',
  COMPLETED: 'completed',
})

const PrescriptionGroupContext = createContext(null)

export function PrescriptionGroupProvider({ children }) {
  const { selectedProfileId } = useProfile()
  // _groupsRaw: BE 응답 그대로. 외부엔 statusFilter 필터된 ``groups`` 만 노출.
  const [_groupsRaw, setGroupsRaw] = useState([])
  const [groupsById, setGroupsById] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [sort, setSort] = useState(PRESCRIPTION_SORT.DATE_DESC)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(PRESCRIPTION_STATUS.ALL)

  // ── list fetch (BE: sort + search 만, statusFilter 는 클라이언트 derived) ──
  const fetchGroups = useCallback(
    async (profileId, opts = {}) => {
      if (!profileId) return
      setIsLoading(true)
      try {
        const params = new URLSearchParams({
          profile_id: profileId,
          sort: opts.sort ?? sort,
        })
        const effectiveSearch = (opts.search ?? search).trim()
        if (effectiveSearch) params.set('search', effectiveSearch)
        const { data } = await api.get(`/api/v1/prescription-groups?${params.toString()}`)
        setGroupsRaw(data || [])
      } catch (err) {
        if (err.response?.status !== 401) console.error('처방전 그룹 조회 실패:', err)
        setGroupsRaw([])
      } finally {
        setIsLoading(false)
      }
    },
    [sort, search],
  )

  useEffect(() => {
    if (!selectedProfileId) {
      setGroupsRaw([])
      setGroupsById({})
      return
    }
    fetchGroups(selectedProfileId)
  }, [selectedProfileId, sort, search, fetchGroups])

  // statusFilter 변경 시 BE 호출 없음 — 클라이언트 derived
  const groups = useMemo(() => {
    if (statusFilter === PRESCRIPTION_STATUS.ALL) return _groupsRaw
    if (statusFilter === PRESCRIPTION_STATUS.ACTIVE) {
      return _groupsRaw.filter((g) => g.has_active_medication)
    }
    return _groupsRaw.filter((g) => !g.has_active_medication)
  }, [_groupsRaw, statusFilter])

  const refetchGroups = useCallback(
    () => fetchGroups(selectedProfileId),
    [fetchGroups, selectedProfileId],
  )

  // ── detail fetch / cache ────────────────────────────────────────
  // drill-down 페이지가 자체 useState 로 fetch 하지 않도록 cache 보유.
  // 같은 id 를 두 번째로 열 때는 cache hit + 백그라운드 refresh.
  const fetchGroupDetail = useCallback(
    async (groupId, { forceRefresh = false } = {}) => {
      if (!groupId) return null
      if (!forceRefresh && groupsById[groupId]) {
        // 백그라운드 refresh (응답 도달 시 cache 갱신)
        api
          .get(`/api/v1/prescription-groups/${groupId}`)
          .then(({ data }) => setGroupsById((prev) => ({ ...prev, [groupId]: data })))
          .catch(() => undefined)
        return groupsById[groupId]
      }
      const { data } = await api.get(`/api/v1/prescription-groups/${groupId}`)
      setGroupsById((prev) => ({ ...prev, [groupId]: data }))
      return data
    },
    [groupsById],
  )

  // ── mutation (응답 기반) ────────────────────────────────────────
  // 카드 list 의 stale 을 막기 위해 응답으로 list row 도 동기 갱신.
  const _patchListEntry = useCallback((id, partial) => {
    setGroupsRaw((prev) =>
      prev.map((g) =>
        g.id === id
          ? {
              ...g,
              hospital_name: partial.hospital_name ?? g.hospital_name,
              department: partial.department ?? g.department,
              dispensed_date: partial.dispensed_date ?? g.dispensed_date,
              has_active_medication:
                partial.has_active_medication !== undefined
                  ? partial.has_active_medication
                  : g.has_active_medication,
              medications_count:
                partial.medications_count !== undefined
                  ? partial.medications_count
                  : g.medications_count,
            }
          : g,
      ),
    )
  }, [])

  const updateGroup = useCallback(
    async (groupId, patch) => {
      const { data } = await api.patch(`/api/v1/prescription-groups/${groupId}`, patch)
      setGroupsById((prev) => ({ ...prev, [groupId]: data }))
      _patchListEntry(groupId, data)
      return data
    },
    [_patchListEntry],
  )

  const markGroupCompleted = useCallback(
    async (groupId) => {
      const { data } = await api.patch(`/api/v1/prescription-groups/${groupId}/complete`)
      setGroupsById((prev) => ({ ...prev, [groupId]: data }))
      // 그룹 안 모든 medication 비활성 → list 의 has_active_medication=false
      _patchListEntry(groupId, { has_active_medication: false })
      return data
    },
    [_patchListEntry],
  )

  const deleteGroup = useCallback(async (groupId) => {
    await api.delete(`/api/v1/prescription-groups/${groupId}`)
    setGroupsById((prev) => {
      const next = { ...prev }
      delete next[groupId]
      return next
    })
    setGroupsRaw((prev) => prev.filter((g) => g.id !== groupId))
  }, [])

  const value = useMemo(
    () => ({
      // 읽기
      groups,
      groupsById,
      isLoading,
      sort,
      search,
      statusFilter,
      // 컨트롤
      setSort,
      setSearch,
      setStatusFilter,
      // detail / mutation
      fetchGroupDetail,
      updateGroup,
      markGroupCompleted,
      deleteGroup,
      // 비상
      refetchGroups,
    }),
    [
      groups,
      groupsById,
      isLoading,
      sort,
      search,
      statusFilter,
      fetchGroupDetail,
      updateGroup,
      markGroupCompleted,
      deleteGroup,
      refetchGroups,
    ],
  )

  return <PrescriptionGroupContext.Provider value={value}>{children}</PrescriptionGroupContext.Provider>
}

export function usePrescriptionGroup() {
  const ctx = useContext(PrescriptionGroupContext)
  if (!ctx) throw new Error('usePrescriptionGroup must be used within PrescriptionGroupProvider')
  return ctx
}
