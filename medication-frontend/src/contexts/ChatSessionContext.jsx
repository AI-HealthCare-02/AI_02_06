'use client'

// ChatSession 도메인 — TanStack Query adapter (PR-B 마이그레이션).
//
// 외부 API: sessions, activeSessionId, setActiveSessionId, isLoading,
// createSession, renameSession, deleteSession, refetchSessions.

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'
import { qk, STALE } from '@/queries/keys'

const ChatSessionContext = createContext(null)

export function ChatSessionProvider({ children }) {
  const { selectedProfileId } = useProfile()
  const qc = useQueryClient()
  const [activeSessionId, setActiveSessionId] = useState(null)

  // ── 1) list query ─────────────────────────────────────────────────
  const listQuery = useQuery({
    queryKey: qk.chatSessions.list(selectedProfileId),
    enabled: !!selectedProfileId,
    staleTime: STALE.chatSessions,
    queryFn: async () => {
      const res = await api.get('/api/v1/chat-sessions', {
        params: { profile_id: selectedProfileId },
      })
      return res.data || []
    },
  })
  const sessions = listQuery.data || []
  const isLoading = listQuery.isLoading

  // profile 전환 시 active reset.
  useEffect(() => {
    setActiveSessionId(null)
  }, [selectedProfileId])

  // ── 2) mutations ──────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: async ({ profileId, title }) => {
      const { data } = await api.post('/api/v1/chat-sessions', {
        profile_id: profileId,
        title,
      })
      return data
    },
    onSuccess: (created) => {
      qc.setQueryData(qk.chatSessions.list(selectedProfileId), (prev = []) => [created, ...prev])
    },
  })

  const renameMutation = useMutation({
    mutationFn: async ({ id, title }) => {
      const { data } = await api.patch(`/api/v1/chat-sessions/${id}`, { title })
      return data
    },
    onSuccess: (updated, { id }) => {
      qc.setQueryData(qk.chatSessions.list(selectedProfileId), (prev = []) =>
        prev.map((s) => (s.id === id ? { ...s, ...updated } : s)),
      )
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      await api.delete(`/api/v1/chat-sessions/${id}`)
      return id
    },
    onSuccess: (id) => {
      qc.setQueryData(qk.chatSessions.list(selectedProfileId), (prev = []) =>
        prev.filter((s) => s.id !== id),
      )
      qc.removeQueries({ queryKey: qk.chatSessions.detail(id) })
      qc.removeQueries({ queryKey: qk.chatSessions.messages(id) })
      setActiveSessionId((prev) => (prev === id ? null : prev))
    },
  })

  // 외부 호환 API.
  const createSession = useCallback(
    (profileId, title) => createMutation.mutateAsync({ profileId, title }),
    [createMutation],
  )
  const renameSession = useCallback(
    (id, title) => renameMutation.mutateAsync({ id, title }),
    [renameMutation],
  )
  const deleteSession = useCallback((id) => deleteMutation.mutateAsync(id), [deleteMutation])
  const refetchSessions = useCallback(() => listQuery.refetch(), [listQuery])

  return (
    <ChatSessionContext.Provider
      value={{
        sessions,
        activeSessionId,
        setActiveSessionId,
        isLoading,
        createSession,
        renameSession,
        deleteSession,
        refetchSessions,
      }}
    >
      {children}
    </ChatSessionContext.Provider>
  )
}

export function useChatSession() {
  const ctx = useContext(ChatSessionContext)
  if (!ctx) throw new Error('useChatSession must be used within ChatSessionProvider')
  return ctx
}
