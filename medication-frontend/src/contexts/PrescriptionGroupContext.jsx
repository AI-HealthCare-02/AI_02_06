'use client'

/**
 * PrescriptionGroupContext — /medication 페이지의 처방전 카드 list / 정렬 / 검색 / 탭 단일 진실.
 *
 * - 정렬 / 검색 / 탭은 서로 독립적으로 동시 결합 가능 (사용자 합의).
 * - selectedProfileId, sort, search, statusFilter 변경 시 자동 fetch.
 * - drill-down 은 페이지 단에서 GET /prescription-groups/{id} 직접 호출 (store 에 안 둠 — URL 마다 분리 데이터).
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

export const PRESCRIPTION_SORT = Object.freeze({
  DATE_DESC: 'date_desc',
  DATE_ASC: 'date_asc',
  DEPARTMENT_ASC: 'department_asc',
  DEPARTMENT_DESC: 'department_desc',
})

export const PRESCRIPTION_STATUS = Object.freeze({
  ALL: 'all',
  ACTIVE: 'active',
  COMPLETED: 'completed',
})

const PrescriptionGroupContext = createContext(null)

export function PrescriptionGroupProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const [groups, setGroups] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [sort, setSort] = useState(PRESCRIPTION_SORT.DATE_DESC)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(PRESCRIPTION_STATUS.ALL)

  const fetchGroups = useCallback(
    async (profileId, opts = {}) => {
      if (!profileId) return
      setIsLoading(true)
      try {
        const params = new URLSearchParams({
          profile_id: profileId,
          sort: opts.sort ?? sort,
          status_filter: opts.statusFilter ?? statusFilter,
        })
        const effectiveSearch = (opts.search ?? search).trim()
        if (effectiveSearch) params.set('search', effectiveSearch)
        const { data } = await api.get(`/api/v1/prescription-groups?${params.toString()}`)
        setGroups(data || [])
      } catch (err) {
        if (err.response?.status !== 401) console.error('처방전 그룹 조회 실패:', err)
        setGroups([])
      } finally {
        setIsLoading(false)
      }
    },
    [sort, statusFilter, search],
  )

  // selectedProfile / sort / statusFilter / search 변경 시 자동 refetch
  useEffect(() => {
    if (!selectedProfileId) {
      setGroups([])
      return
    }
    fetchGroups(selectedProfileId)
  }, [selectedProfileId, sort, statusFilter, search, fetchGroups])

  const refetchGroups = useCallback(
    () => fetchGroups(selectedProfileId),
    [fetchGroups, selectedProfileId],
  )

  const value = useMemo(
    () => ({
      groups,
      isLoading,
      sort,
      search,
      statusFilter,
      setSort,
      setSearch,
      setStatusFilter,
      refetchGroups,
    }),
    [groups, isLoading, sort, search, statusFilter, refetchGroups],
  )

  return <PrescriptionGroupContext.Provider value={value}>{children}</PrescriptionGroupContext.Provider>
}

export function usePrescriptionGroup() {
  const ctx = useContext(PrescriptionGroupContext)
  if (!ctx) throw new Error('usePrescriptionGroup must be used within PrescriptionGroupProvider')
  return ctx
}
