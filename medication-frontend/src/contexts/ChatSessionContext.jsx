'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

const ChatSessionContext = createContext(null)

/**
 * Chat session 단일 진실.
 *
 * - 프로필별 채팅 세션 list 를 단일 store 에 보유.
 * - selectedProfileId 변경 시 자동 refetch + activeSessionId reset.
 * - mutation (create / rename / delete) 응답으로 in-place 갱신.
 *
 * 메시지 (messages) 는 세션마다 양이 많고 채팅 모달 안에서만 사용하므로
 * 각 세션의 message list 는 ChatModal 컴포넌트에서 자체 보관 (Context 외부).
 */
export function ChatSessionProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const fetchSessions = useCallback(async (profileId) => {
    if (!profileId) return
    setIsLoading(true)
    try {
      const res = await api.get('/api/v1/chat-sessions', {
        params: { profile_id: profileId },
      })
      setSessions(res.data || [])
    } catch (err) {
      if (err.response?.status !== 401) console.error('세션 조회 실패:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // profile 전환 → 세션 목록 자동 재로드 + active reset
  useEffect(() => {
    if (!selectedProfileId) {
      setSessions([])
      setActiveSessionId(null)
      return
    }
    fetchSessions(selectedProfileId)
    setActiveSessionId(null)
  }, [selectedProfileId, fetchSessions])

  // ── 응답 기반 mutation ──────────────────────────────

  const createSession = useCallback(async (profileId, title) => {
    const { data: created } = await api.post('/api/v1/chat-sessions', {
      profile_id: profileId,
      title,
    })
    setSessions(prev => [created, ...prev])
    return created
  }, [])

  const renameSession = useCallback(async (id, title) => {
    const { data: updated } = await api.patch(`/api/v1/chat-sessions/${id}`, { title })
    setSessions(prev => prev.map(s => (s.id === id ? { ...s, ...updated } : s)))
    return updated
  }, [])

  const deleteSession = useCallback(async (id) => {
    await api.delete(`/api/v1/chat-sessions/${id}`)
    setSessions(prev => prev.filter(s => s.id !== id))
    setActiveSessionId(prev => (prev === id ? null : prev))
  }, [])

  // refetchSessions 를 stable ref 로 — 인라인 arrow 면 매 render 마다 새 함수가 되어
  // 이를 deps 로 사용하는 hook 이 무한 루프에 빠질 수 있음 (ChatModal initSession 케이스)
  const refetchSessions = useCallback(
    () => fetchSessions(selectedProfileId),
    [fetchSessions, selectedProfileId],
  )

  return (
    <ChatSessionContext.Provider value={{
      sessions,
      activeSessionId,
      setActiveSessionId,
      isLoading,
      createSession,
      renameSession,
      deleteSession,
      refetchSessions,
    }}>
      {children}
    </ChatSessionContext.Provider>
  )
}

export function useChatSession() {
  const ctx = useContext(ChatSessionContext)
  if (!ctx) throw new Error('useChatSession must be used within ChatSessionProvider')
  return ctx
}
