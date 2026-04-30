'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { usePathname } from 'next/navigation'
import api from '@/lib/api'

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
    // SELF 프로필은 계정 자체와 묶여 있어 삭제 금지 (가족 관리 카드에서 잘못
    // 호출되어도 사전 차단). 계정 탈퇴는 별도 mypage flow 사용.
    const target = profiles.find(p => p.id === id)
    if (target?.relation_type === 'SELF') {
      throw new Error('본인 프로필은 삭제할 수 없습니다. 계정 탈퇴 메뉴를 이용해주세요.')
    }
    await api.delete(`/api/v1/profiles/${id}`)
    setProfiles(prev => prev.filter(p => p.id !== id))
    // selectedId 정합성은 위 useEffect 가 자동 처리
  }, [profiles])

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
