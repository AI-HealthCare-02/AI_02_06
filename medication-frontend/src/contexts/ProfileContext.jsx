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

export function ProfileProvider({ children }) {
  const pathname = usePathname()
  const isPublic = PUBLIC_PATHS.includes(pathname) || pathname.startsWith('/auth/')

  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileIdState] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const fetchProfiles = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/profiles')
      const data = res.data || []
      setProfiles(data)

      if (data.length === 0) return

      // localStorage에 저장된 프로필이 유효하면 복원
      const saved = localStorage.getItem(STORAGE_KEY)
      const savedValid = saved && data.find(p => p.id === saved)
      if (savedValid) {
        setSelectedProfileIdState(saved)
      } else {
        // 기본값: SELF 프로필
        const self = data.find(p => p.relation_type === 'SELF') || data[0]
        setSelectedProfileIdState(self.id)
        localStorage.setItem(STORAGE_KEY, self.id)
      }
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

  const setSelectedProfileId = useCallback((id) => {
    setSelectedProfileIdState(id)
    localStorage.setItem(STORAGE_KEY, id)
  }, [])

  const selectedProfile = profiles.find(p => p.id === selectedProfileId) || null

  return (
    <ProfileContext.Provider value={{
      profiles,
      selectedProfile,
      selectedProfileId,
      setSelectedProfileId,
      isLoading,
      refetchProfiles: fetchProfiles,
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
