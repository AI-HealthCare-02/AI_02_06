'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { usePathname } from 'next/navigation'
import api from '@/lib/api'

const ProfileContext = createContext(null)

const STORAGE_KEY = 'selectedProfileId'

const PUBLIC_PATHS = ['/', '/login']

const RELATION_LABELS = {
  SELF: '본인',
  PARENT: '부모님',
  CHILD: '자녀',
  SPOUSE: '배우자',
  OTHER: '가족',
}

/**
 * Profile 단일 진실 (single source of truth).
 *
 * 두 갱신 경로:
 *  1) BE 응답 기반 — updateProfile / createProfile / deleteProfile
 *     mutation 함수가 응답을 받자마자 setProfiles 로 in-place 갱신.
 *     별도 refetch 없음.
 *  2) FE 동작 기반 — setSelectedProfileId
 *     사용자 UI 조작 (드롭다운 선택 등) 시 네트워크 호출 없이 바로 변경.
 *
 * selectedProfileId 정합성은 profiles 변경 시 useEffect 가 자동 처리.
 * (삭제된 프로필이 selected 였다면 SELF 로 fallback)
 */
export function ProfileProvider({ children }) {
  const pathname = usePathname()
  const isPublic = PUBLIC_PATHS.includes(pathname) || pathname.startsWith('/auth/')

  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileIdState] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // ── 초기 로드 (첫 mount 1회) ─────────────────────────────────
  const fetchProfiles = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/profiles')
      setProfiles(res.data || [])
    } catch (err) {
      console.error('프로필 조회 실패:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isPublic) {
      setIsLoading(false)
      return
    }
    fetchProfiles()
  }, [isPublic, fetchProfiles])

  // ── selectedProfileId 정합성 자동 검증 ──────────────────────────
  // profiles 가 바뀔 때마다 (fetch / 추가 / 삭제 등) 자동으로 검증·정리.
  useEffect(() => {
    if (profiles.length === 0) {
      if (selectedProfileId !== null) {
        setSelectedProfileIdState(null)
        localStorage.removeItem(STORAGE_KEY)
      }
      return
    }
    // 현재 selected 가 유효하면 유지
    if (selectedProfileId && profiles.find(p => p.id === selectedProfileId)) return
    // localStorage 의 saved 가 유효하면 복원
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && profiles.find(p => p.id === saved)) {
      setSelectedProfileIdState(saved)
      return
    }
    // fallback: SELF 또는 첫 프로필
    const fallback = profiles.find(p => p.relation_type === 'SELF') || profiles[0]
    setSelectedProfileIdState(fallback.id)
    localStorage.setItem(STORAGE_KEY, fallback.id)
  }, [profiles, selectedProfileId])

  // ── 경로 1: BE 응답 기반 mutation ────────────────────────────
  // 모두 응답 데이터로 setProfiles 직접 갱신 — refetch 없음.

  const updateProfile = useCallback(async (id, patch) => {
    const { data: updated } = await api.patch(`/api/v1/profiles/${id}`, patch)
    setProfiles(prev => prev.map(p => (p.id === id ? updated : p)))
    return updated
  }, [])

  const createProfile = useCallback(async (input) => {
    const { data: created } = await api.post('/api/v1/profiles', input)
    setProfiles(prev => [...prev, created])
    return created
  }, [])

  const deleteProfile = useCallback(async (id) => {
    await api.delete(`/api/v1/profiles/${id}`)
    setProfiles(prev => prev.filter(p => p.id !== id))
    // selectedId 정합성은 위 useEffect 가 자동 처리
  }, [])

  // ── 경로 2: FE 동작 기반 ─────────────────────────────────────

  const setSelectedProfileId = useCallback((id) => {
    setSelectedProfileIdState(id)
    localStorage.setItem(STORAGE_KEY, id)
  }, [])

  // ── computed ───────────────────────────────────────────────
  const selectedProfile = profiles.find(p => p.id === selectedProfileId) || null

  return (
    <ProfileContext.Provider value={{
      // 읽기
      profiles,
      selectedProfile,
      selectedProfileId,
      isLoading,
      // 경로 1 (BE 응답 기반 mutation — 응답 후 자동 state 갱신)
      updateProfile,
      createProfile,
      deleteProfile,
      // 경로 2 (FE 동작 기반)
      setSelectedProfileId,
      // 비상용 (full refetch)
      refetchProfiles: fetchProfiles,
      // 라벨
      RELATION_LABELS,
    }}>
      {children}
    </ProfileContext.Provider>
  )
}

export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within ProfileProvider')
  return ctx
}
