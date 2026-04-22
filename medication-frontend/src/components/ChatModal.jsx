'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { X, Send, RefreshCw } from 'lucide-react'
import api, { showError } from '@/lib/api'

/**
 * 공통 챗봇 모달 컴포넌트
 *
 * 내부 상태는 다중 세션 구조로 정규화되어 있다.
 * - sessions: 프로필에 속한 모든 세션 목록 (updated_at DESC)
 * - activeSessionId: 현재 활성화된 세션 ID
 * - messages: 활성 세션의 메시지 리스트
 *
 * 사이드바 UI는 별도 커밋에서 붙이며, 현재 동작은 기존과 동일하다
 * (가장 최근 세션 1개만 활성화, 없으면 자동 생성).
 *
 * @param {Object} props
 * @param {Function} props.onClose - 모달 닫기 콜백
 * @param {string} props.profileId - 프로필 ID (필수)
 */
export default function ChatModal({ onClose, profileId }) {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)
  const [initError, setInitError] = useState(false)
  const scrollRef = useRef(null)

  // 특정 세션의 메시지를 불러온다 (신규 세션이면 환영 메시지)
  const loadMessagesForSession = useCallback(async (sessionId) => {
    const res = await api.get(`/api/v1/messages/session/${sessionId}`)
    if (res.data?.length > 0) {
      setMessages(res.data.map(m => ({
        role: m.sender_type === 'USER' ? 'user' : 'assistant',
        content: m.content,
      })))
    } else {
      setMessages([{ role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요.' }])
    }
  }, [])

  // 세션 초기화: 리스트 조회 → 없으면 신규 생성 → 가장 최근 세션 활성화
  const initSession = useCallback(async () => {
    if (!profileId) {
      setMessages([{ role: 'assistant', content: '프로필 정보를 불러올 수 없습니다.' }])
      setIsInitializing(false)
      return
    }

    setIsInitializing(true)
    setInitError(false)

    try {
      const sessionsRes = await api.get('/api/v1/chat-sessions', {
        params: { profile_id: profileId },
      })

      let sessionList = sessionsRes.data || []

      if (sessionList.length === 0) {
        // 세션이 없으면 신규 생성
        const newSessionRes = await api.post('/api/v1/chat-sessions', {
          profile_id: profileId,
          title: '복약 상담',
        })
        sessionList = [newSessionRes.data]
      }

      const currentSessionId = sessionList[0].id
      setSessions(sessionList)
      setActiveSessionId(currentSessionId)
      await loadMessagesForSession(currentSessionId)
    } catch (err) {
      console.error('세션 초기화 실패:', err)
      showError('채팅 세션을 시작할 수 없습니다.')
      setMessages([{ role: 'assistant', content: '채팅 연결에 실패했습니다. 아래 버튼을 눌러 다시 시도해주세요.' }])
      setInitError(true)
    } finally {
      setIsInitializing(false)
    }
  }, [profileId, loadMessagesForSession])

  // 모달 열릴 때: 세션 초기화
  useEffect(() => {
    initSession()
  }, [initSession])

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isLoading || !activeSessionId) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)

    try {
      const res = await api.post('/api/v1/messages/ask', {
        session_id: activeSessionId,
        content: message,
      })
      const assistantContent = res.data.assistant_message?.content || '응답을 받지 못했습니다.'
      setMessages(prev => [...prev, { role: 'assistant', content: assistantContent }])
    } catch (err) {
      console.error('메시지 전송 실패:', err)
      setMessages(prev => [...prev, { role: 'assistant', content: '죄송합니다. 응답을 처리하는 중 오류가 발생했습니다.' }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-end justify-end p-6 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md h-[600px] flex flex-col shadow-2xl border border-gray-100 overflow-hidden">
        {/* 헤더 */}
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-lg text-gray-900">복약 AI 상담</h2>
            <p className="text-xs text-gray-400">약 복용 방법 등 무엇이든 물어보세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer p-2 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* 채팅 영역 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user'
                  ? 'bg-gray-900 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}

          {/* 점 바운스: 세션 초기화 중 또는 AI 응답 대기 중 */}
          {(isInitializing || isLoading) && (
            <div className="flex justify-start">
                <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex gap-1.5">
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                  <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                </div>
            </div>)}
        </div>

        {/* 입력창 */}
        <div className="p-4 bg-white border-t border-gray-100 flex gap-2 items-center">
          {initError ? (
            /* 재시도 버튼 (초기화 실패 시) */
            <button
              onClick={initSession}
              disabled={isInitializing}
              className="flex-1 flex items-center justify-center gap-2 bg-gray-900 text-white rounded-xl px-4 py-2.5 text-sm hover:bg-gray-700 disabled:bg-gray-400 active:scale-95 transition-all cursor-pointer"
            >
              <RefreshCw size={16} className={isInitializing ? 'animate-spin' : ''} />
              {isInitializing ? '연결 중...' : '다시 연결하기'}
            </button>
          ) : (
            /* 일반 입력창 */
            <>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
                disabled={isInitializing || !activeSessionId}
                placeholder={isInitializing ? '연결 중...' : (!activeSessionId ? '연결 실패' : '메시지를 입력하세요')}
                className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-gray-400 transition-all disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim() || isInitializing || !activeSessionId}
                className="w-10 h-10 rounded-xl flex items-center justify-center bg-gray-900 text-white hover:bg-gray-700 disabled:bg-gray-100 disabled:text-gray-300 active:scale-95 transition-all cursor-pointer"
              >
                <Send size={16} />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
