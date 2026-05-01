'use client'

// Profile 도메인 — TanStack Query adapter (PR-B 마이그레이션).
//
// 외부 API 시그니처 100% 호환:
//   profiles, selectedProfile, selectedProfileId, isLoading,
//   updateProfile, createProfile, deleteProfile,
//   setSelectedProfileId, refetchProfiles, RELATION_LABELS, RELATION_GENDER_DEFAULT.
//
// 변경 핵심:
// - list GET 을 useQuery 로 교체 (staleTime 5분 — 거의 안 바뀜).
// - mutation 은 useMutation, onSuccess 에서 list cache 직접 patch.
// - profile 삭제 시 그 profile 의 prescription-groups / lifestyle-guides /
//   challenges 캐시 invalidate (BE cascade 와 동기화).

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import api from '@/lib/api'
import { qk, STALE } from '@/queries/keys'

const ProfileContext = createContext(null)

const STORAGE_KEY = 'selectedProfileId'

const PUBLIC_PATHS = ['/', '/login']

// 가족 관계 enum 8종 단일 매핑 — relation_type 만으로 라벨 결정 (gender 합성 없음)
const RELATION_LABELS = {
  SELF: '본인',
  FATHER: '아버지',
  MOTHER: '어머니',
  SON: '아들',
  DAUGHTER: '딸',
  HUSBAND: '남편',
  WIFE: '아내',
  OTHER: '가족',
}

// relation_type → 기본 gender 매핑 (FE form 의 자동 채움 UX)
// SELF / OTHER 는 사용자 직접 입력. BE 도 동일 default 정책 (RELATION_DEFAULT_GENDER).
export const RELATION_GENDER_DEFAULT = {
  FATHER: 'MALE',
  MOTHER: 'FEMALE',
  SON: 'MALE',
  DAUGHTER: 'FEMALE',
  HUSBAND: 'MALE',
  WIFE: 'FEMALE',
}

export function ProfileProvider({ children }) {
  const pathname = usePathname()
  const isPublic = PUBLIC_PATHS.includes(pathname) || pathname.startsWith('/auth/')
  const qc = useQueryClient()

  const [selectedProfileId, setSelectedProfileIdState] = useState(null)

  // ── 1) list query ─────────────────────────────────────────────────
  // public path 에서는 enabled=false → fetch 0회 (인증 없는 라우트에서 401 노이즈 방지).
  const listQuery = useQuery({
    queryKey: qk.profile.list(),
    enabled: !isPublic,
    staleTime: STALE.profile,
    queryFn: async () => {
      const { data } = await api.get('/api/v1/profiles')
      return data || []
    },
  })
  const profiles = listQuery.data || []
  // 첫 로드 + public path 모두에서 일관된 isLoading.
  const isLoading = isPublic ? false : listQuery.isLoading

  // ── selectedProfileId 정합성 자동 검증 ────────────────────────────
  useEffect(() => {
    if (profiles.length === 0) {
      if (selectedProfileId !== null) {
        setSelectedProfileIdState(null)
        if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY)
      }
      return
    }
    if (selectedProfileId && profiles.find((p) => p.id === selectedProfileId)) return
    const saved = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
    if (saved && profiles.find((p) => p.id === saved)) {
      setSelectedProfileIdState(saved)
      return
    }
    const fallback = profiles.find((p) => p.relation_type === 'SELF') || profiles[0]
    setSelectedProfileIdState(fallback.id)
    if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, fallback.id)
  }, [profiles, selectedProfileId])

  // ── 2) mutations — 응답으로 cache 직접 patch ──────────────────────
  const updateMutation = useMutation({
    mutationFn: async ({ id, patch }) => {
      const { data } = await api.patch(`/api/v1/profiles/${id}`, patch)
      return data
    },
    onSuccess: (updated) => {
      qc.setQueryData(qk.profile.list(), (prev = []) =>
        prev.map((p) => (p.id === updated.id ? updated : p)),
      )
      qc.setQueryData(qk.profile.detail(updated.id), updated)
    },
  })

  const createMutation = useMutation({
    mutationFn: async (input) => {
      const { data } = await api.post('/api/v1/profiles', input)
      return data
    },
    onSuccess: (created) => {
      qc.setQueryData(qk.profile.list(), (prev = []) => [...prev, created])
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const target = profiles.find((p) => p.id === id)
      if (target?.relation_type === 'SELF') {
        throw new Error('본인 프로필은 삭제할 수 없습니다. 계정 탈퇴 메뉴를 이용해주세요.')
      }
      await api.delete(`/api/v1/profiles/${id}`)
      return id
    },
    onSuccess: (id) => {
      qc.setQueryData(qk.profile.list(), (prev = []) => prev.filter((p) => p.id !== id))
      qc.removeQueries({ queryKey: qk.profile.detail(id) })
      // BE cascade — 그 profile 의 처방전 / medication / 가이드 / 챌린지 / 챗 / OCR 까지 정리됨.
      qc.invalidateQueries({ queryKey: qk.prescriptionGroups.all() })
      qc.invalidateQueries({ queryKey: qk.medications.all() })
      qc.invalidateQueries({ queryKey: qk.lifestyleGuides.all() })
      qc.invalidateQueries({ queryKey: qk.challenges.all() })
      qc.invalidateQueries({ queryKey: qk.chatSessions.all() })
      qc.invalidateQueries({ queryKey: qk.ocrDraft.all() })
      qc.invalidateQueries({ queryKey: qk.dailyLogs.all() })
    },
  })

  // 외부 호환 API.
  const updateProfile = useCallback(
    (id, patch) => updateMutation.mutateAsync({ id, patch }),
    [updateMutation],
  )
  const createProfile = useCallback((input) => createMutation.mutateAsync(input), [createMutation])
  const deleteProfile = useCallback((id) => deleteMutation.mutateAsync(id), [deleteMutation])
  const refetchProfiles = useCallback(() => listQuery.refetch(), [listQuery])

  const setSelectedProfileId = useCallback((id) => {
    setSelectedProfileIdState(id)
    if (typeof window !== 'undefined') localStorage.setItem(STORAGE_KEY, id)
  }, [])

  // ── computed ───────────────────────────────────────────────
  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) || null

  return (
    <ProfileContext.Provider
      value={{
        profiles,
        selectedProfile,
        selectedProfileId,
        isLoading,
        updateProfile,
        createProfile,
        deleteProfile,
        setSelectedProfileId,
        refetchProfiles,
        RELATION_LABELS,
      }}
    >
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within ProfileProvider')
  return ctx
}
