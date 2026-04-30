'use client'

/**
 * PrescriptionGroupContext — /medication 카드 list + drill-down detail 의 단일 진실.
 *
 * - 정렬 / 검색 / 탭은 서로 독립적으로 동시 결합 가능 (사용자 합의).
 * - **search 만 BE 처리** (medication 테이블 join 필요) — selectedProfileId / search
 *   변경 시 list refetch.
 * - **sort / statusFilter 는 클라이언트 측 derived** — 이미 받은 _groupsRaw 를
 *   client memo 로 정렬·필터. 탭/정렬 변경 시 GET 호출 0회.
 * - 병원 정렬에선 ``hospital_name`` NULL 그룹을 정렬 방향과 무관하게 list 맨 위로
 *   partition (사용자가 입력해야 할 action item).
 * - drill-down 페이지가 자체 useState 로 fetch 하지 않도록 ``groupsById`` cache + mutation API 노출.
 * - mutation (update/markCompleted/delete) 은 응답으로 cache + list 직접 갱신.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import api from '@/lib/api'
import { useMedication } from '@/contexts/MedicationContext'
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
  // MedicationContext 의 active 약 수 변화를 listen — 약 복용 처리/마감 시
  // 그룹의 has_active_medication 이 stale 해지므로 list refetch trigger.
  const { medications } = useMedication()
  // _groupsRaw: BE 응답 그대로. 외부엔 statusFilter 필터된 ``groups`` 만 노출.
  const [_groupsRaw, setGroupsRaw] = useState([])
  const [groupsById, setGroupsById] = useState({})
  // fetchGroupDetail 이 stable callback 이 되도록 cache 는 ref 로 접근.
  // (deps 에 groupsById 두면 cache 갱신마다 callback reference 가 변해
  //  소비 페이지의 useEffect 가 무한 재실행 → 무한 GET 호출.)
  const groupsByIdRef = useRef(groupsById)
  useEffect(() => {
    groupsByIdRef.current = groupsById
  }, [groupsById])
  const [isLoading, setIsLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(PRESCRIPTION_STATUS.ALL)
  // 탭별 sort 분리 — 사용자가 "복용 중" 은 최신순으로, "복용 완료" 는 병원순
  // 으로 보고 싶다는 흐름에 맞춤. 탭 전환 시 그 탭의 마지막 sort 가 복원.
  const [sortByTab, setSortByTab] = useState({
    [PRESCRIPTION_STATUS.ALL]: PRESCRIPTION_SORT.DATE_DESC,
    [PRESCRIPTION_STATUS.ACTIVE]: PRESCRIPTION_SORT.DATE_DESC,
    [PRESCRIPTION_STATUS.COMPLETED]: PRESCRIPTION_SORT.DATE_DESC,
  })
  const sort = sortByTab[statusFilter]
  const setSort = useCallback(
    (next) => setSortByTab((prev) => ({ ...prev, [statusFilter]: next })),
    [statusFilter],
  )

  // ── list fetch (BE: search 만, sort/statusFilter 는 클라이언트 derived) ──
  const fetchGroups = useCallback(
    async (profileId, opts = {}) => {
      if (!profileId) return
      setIsLoading(true)
      try {
        const params = new URLSearchParams({ profile_id: profileId })
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
    [search],
  )

  useEffect(() => {
    if (!selectedProfileId) {
      setGroupsRaw([])
      setGroupsById({})
      return
    }
    fetchGroups(selectedProfileId)
  }, [selectedProfileId, search, fetchGroups])

  // 클라이언트 sort — 병원 정렬에선 NULL 그룹을 항상 맨 위로 partition.
  const sortedRaw = useMemo(() => {
    const result = [..._groupsRaw]
    const sortByDate = (asc) =>
      result.sort((a, b) => {
        const av = a.dispensed_date || ''
        const bv = b.dispensed_date || ''
        return asc ? av.localeCompare(bv) : bv.localeCompare(av)
      })
    const sortByHospital = (asc) =>
      result.sort((a, b) => {
        // NULL (미상) 은 정렬 방향과 무관하게 항상 상단 (action item 시선 유도)
        if (!a.hospital_name && !b.hospital_name) return 0
        if (!a.hospital_name) return -1
        if (!b.hospital_name) return 1
        const cmp = a.hospital_name.localeCompare(b.hospital_name, 'ko')
        return asc ? cmp : -cmp
      })
    if (sort === PRESCRIPTION_SORT.DATE_DESC) sortByDate(false)
    else if (sort === PRESCRIPTION_SORT.DATE_ASC) sortByDate(true)
    else if (sort === PRESCRIPTION_SORT.HOSPITAL_ASC) sortByHospital(true)
    else if (sort === PRESCRIPTION_SORT.HOSPITAL_DESC) sortByHospital(false)
    return result
  }, [_groupsRaw, sort])

  // statusFilter 변경 시 BE 호출 없음 — 클라이언트 derived (이미 sort 적용된 sortedRaw 사용).
  const groups = useMemo(() => {
    if (statusFilter === PRESCRIPTION_STATUS.ALL) return sortedRaw
    if (statusFilter === PRESCRIPTION_STATUS.ACTIVE) {
      return sortedRaw.filter((g) => g.has_active_medication)
    }
    return sortedRaw.filter((g) => !g.has_active_medication)
  }, [sortedRaw, statusFilter])

  const refetchGroups = useCallback(
    () => fetchGroups(selectedProfileId),
    [fetchGroups, selectedProfileId],
  )

  // medication active count 변화 감지 — 약 복용 mark / deactivate 시 자동 refetch.
  // 그룹의 has_active_medication 라벨이 즉시 따라가게 한다.
  const activeCountRef = useRef(-1)
  useEffect(() => {
    if (!selectedProfileId) {
      activeCountRef.current = -1
      return
    }
    const activeCount = medications.filter((m) => m.is_active).length
    if (activeCountRef.current === -1) {
      // 초기 mount — 비교 baseline 만 기록, refetch 트리거 X
      activeCountRef.current = activeCount
      return
    }
    if (activeCount !== activeCountRef.current) {
      activeCountRef.current = activeCount
      refetchGroups()
    }
  }, [medications, selectedProfileId, refetchGroups])

  // ── detail fetch / cache ────────────────────────────────────────
  // drill-down 페이지가 자체 useState 로 fetch 하지 않도록 cache 보유.
  // 같은 id 를 두 번째로 열 때는 cache hit + 백그라운드 refresh.
  const fetchGroupDetail = useCallback(async (groupId, { forceRefresh = false } = {}) => {
    if (!groupId) return null
    const cached = groupsByIdRef.current[groupId]
    if (!forceRefresh && cached) {
      // 백그라운드 refresh — cache 즉시 반환 + 응답 도달 시 store 갱신.
      api
        .get(`/api/v1/prescription-groups/${groupId}`)
        .then(({ data }) => setGroupsById((prev) => ({ ...prev, [groupId]: data })))
        .catch(() => undefined)
      return cached
    }
    const { data } = await api.get(`/api/v1/prescription-groups/${groupId}`)
    setGroupsById((prev) => ({ ...prev, [groupId]: data }))
    return data
  }, [])

  // ── mutation (응답 기반) ────────────────────────────────────────
  // 카드 list 의 stale 을 막기 위해 응답으로 list row 도 동기 갱신.
  // ``in`` 으로 명시 set 검사 — partial 에 키가 있으면 NULL 도 그대로 반영
  // (예: 사용자가 진료과를 빈 값으로 수정 = NULL 로 set 되는 케이스).
  const _patchListEntry = useCallback((id, partial) => {
    setGroupsRaw((prev) =>
      prev.map((g) => {
        if (g.id !== id) return g
        const next = { ...g }
        for (const key of [
          'hospital_name',
          'department',
          'dispensed_date',
          'has_active_medication',
          'medications_count',
        ]) {
          if (key in partial) next[key] = partial[key]
        }
        return next
      }),
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
      setSort,
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
