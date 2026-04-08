'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'

export default function ChatPage() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    const initSession = async () => {
      try {
        const saved = sessionStorage.getItem('chatSessionId')
        if (saved) {
          setSessionId(saved)
          const res = await api.get(`/api/v1/messages/session/${saved}`)
          if (res.data.length > 0) {
            const history = res.data.map(m => ({
              role: m.sender_type === 'USER' ? 'user' : 'assistant',
              content: m.content,
            }))
            setMessages([messages[0], ...history])
          }
          return
        }

        // 세션 생성 - account_id, profile_id는 쿠키 기반 인증이므로 임시 UUID 사용
        // 실제 서비스에서는 로그인 후 저장된 값으로 교체 필요
        const accountId = localStorage.getItem('accountId')
        const profileId = localStorage.getItem('profileId')
        if (!accountId || !profileId) return

        const res = await api.post('/api/v1/chat-sessions/', {
          account_id: accountId,
          profile_id: profileId,
          title: '복약 상담',
        })
        sessionStorage.setItem('chatSessionId', res.data.id)
        setSessionId(res.data.id)
      } catch (e) {
        console.error('세션 초기화 실패', e)
      }
    }
    initSession()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isLoading || !sessionId) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)

    try {
      const res = await api.post('/api/v1/messages/ask', {
        session_id: sessionId,
        content: message,
      })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.assistant_message.content,
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.',
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => router.push('/main')} className="text-gray-400 hover:text-black cursor-pointer text-xl">←</button>
        <div>
          <h1 className="font-bold">복약 AI 상담</h1>
          <p className="text-xs text-gray-400">약 복용 방법, 부작용 등 무엇이든 물어보세요</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 pb-32">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap
              ${msg.role === 'user'
                ? 'bg-blue-500 text-white rounded-br-sm'
                : 'bg-white shadow-sm text-gray-800 rounded-bl-sm'
              }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white shadow-sm px-4 py-3 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 px-6 py-4">
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSend() } }}
            placeholder={sessionId ? '메시지를 입력하세요' : '세션을 초기화하는 중...'}
            disabled={!sessionId}
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-300 disabled:bg-gray-50"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !sessionId}
            className="bg-blue-500 text-white px-5 py-3 rounded-xl text-sm font-semibold cursor-pointer hover:bg-blue-600 shrink-0 disabled:opacity-50">
            전송
          </button>
        </div>
      </div>
    </main>
  )
}
