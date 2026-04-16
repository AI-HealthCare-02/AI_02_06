'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Home, User, Camera, Trophy, ClipboardList, MessageCircle, X, Send } from 'lucide-react'
import api from '@/lib/api'
import ChatModal from '@/components/ChatModal'

// 챗봇 로딩 점 3개
function TypingDots() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-100 shadow-sm px-4 py-4 rounded-2xl rounded-bl-none">
        <div className="flex gap-1.5 items-center">
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'bounce 1.2s infinite', animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'bounce 1.2s infinite', animationDelay: '200ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'bounce 1.2s infinite', animationDelay: '400ms' }} />
          <style>{`@keyframes bounce { 0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)} }`}</style>
        </div>
      </div>
    </div>
  )
}

function ChatModal({ onClose }) {
  const [sessionId, setSessionId] = useState(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const [initError, setInitError] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading, isInitializing])

  // 채팅 세션 생성
  useEffect(() => {
    const initSession = async () => {
      setIsInitializing(true)
      setInitError(false)
      try {
        const profileRes = await api.get('/api/v1/profiles/')
        const self = profileRes.data?.find(p => p.relation_type === 'SELF') || profileRes.data?.[0]
        if (!self) throw new Error('프로필 없음')
        const res = await api.post('/api/v1/chat-sessions/', {
          account_id: '00000000-0000-0000-0000-000000000000',
          profile_id: self.id,
          title: 'AI 상담',
        })
        setSessionId(res.data.id)
        setMessages([{ role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요.' }])
      } catch (err) {
        console.error('세션 생성 실패:', err)
        setInitError(true)
      } finally {
        setIsInitializing(false)
      }
    }
    initSession()
  }, [])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isLoading || isInitializing || !sessionId) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)
    try {
      const res = await api.post('/api/v1/messages/ask', {
        session_id: sessionId,
        content: message,
      })
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.assistant_message.content }])
    } catch (err) {
      console.error(err)
      setMessages(prev => [...prev, { role: 'assistant', content: '오류가 발생했습니다. 잠시 후 다시 시도해주세요.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const isBlocked = isLoading || isInitializing || !sessionId

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-end p-6">
      <div className="bg-white rounded-3xl w-full max-w-xl h-[700px] flex flex-col shadow-2xl overflow-hidden">
        {/* 헤더 */}
        <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-white">
          <div>
            <h2 className="font-bold text-xl text-gray-900">복약 AI 상담</h2>
            <p className="text-xs text-gray-400 mt-1">
              {isInitializing ? 'AI 상담사 연결 중...' : initError ? '연결 실패' : '약 복용 방법, 부작용 등 무엇이든 물어보세요'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer p-2 transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* 채팅 영역 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50">
          {initError && (
            <div className="flex justify-start">
              <div className="max-w-[80%] px-4 py-3 rounded-2xl text-sm bg-red-50 text-red-500 border border-red-100 rounded-bl-none">
                서버 연결에 실패했습니다. 잠시 후 다시 시도해주세요.
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user'
                  ? 'bg-gray-900 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-100'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}

          {/* 점 바운스: 세션 초기화 중 또는 AI 응답 대기 중 */}
          {(isInitializing || isLoading) && <TypingDots />}
        </div>

        {/* 입력창 */}
        <div className="p-5 border-t border-gray-100 bg-white flex gap-3 items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder={isInitializing ? '연결 중...' : '메시지를 입력하세요'}
            disabled={isBlocked}
            className="flex-1 bg-gray-50 border border-gray-100 rounded-2xl px-5 py-3 text-sm outline-none focus:border-gray-300 focus:bg-white transition-all disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={isBlocked || !input.trim()}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all shadow-md active:scale-90
              ${isBlocked || !input.trim()
                ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                : 'bg-gray-900 text-white hover:bg-gray-700'
              }`}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Navigation() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [profileId, setProfileId] = useState(null)

  // 프로필 ID 가져오기
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/api/v1/profiles')
        if (res.data?.length > 0) {
          const self = res.data.find(p => p.relation_type === 'SELF') || res.data[0]
          setProfileId(self.id)
        }
      } catch (err) {
        console.error('프로필 조회 실패:', err)
      }
    }
    fetchProfile()
  }, [])

  const menus = [
    { icon: <Home size={18} />, label: '홈', path: '/main' },
    { icon: <User size={18} />, label: '마이페이지', path: '/mypage' },
    { icon: <Camera size={18} />, label: '처방전 등록', path: '/ocr' },
    { icon: <Trophy size={18} />, label: '챌린지', path: '/challenge' },
    { icon: <ClipboardList size={18} />, label: '용법/주의사항', path: '/medication' },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={profileId} />}

      {/* 햄버거 버튼 */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-6 left-6 z-40 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center cursor-pointer hover:shadow-xl transition-all active:scale-90 border border-gray-100"
      >
        <div className="flex flex-col gap-1">
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
        </div>
      </button>

      {/* 챗봇 플로팅 버튼 */}
      <button
        onClick={() => setShowChat(true)}
        className="fixed bottom-8 right-8 z-40 w-16 h-16 bg-blue-600 rounded-full shadow-2xl flex items-center justify-center text-white cursor-pointer hover:bg-blue-700 hover:scale-110 transition-all active:scale-95"
      >
        <MessageCircle size={28} />
      </button>

      {/* 어두운 배경 */}
      {isOpen && (
        <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-all" />
      )}

      {/* 사이드바 */}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white z-50 shadow-2xl transform transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center px-8 py-8 border-b border-gray-50">
          <h2 className="font-black text-2xl text-blue-600 tracking-tighter">Downforce</h2>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-black transition-colors">
            <X size={24} />
          </button>
        </div>
        <div className="py-6 px-4">
          {menus.map((menu, i) => (
            <button key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className="flex items-center gap-4 w-full px-6 py-4 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all group"
            >
              <span className="group-hover:scale-110 transition-transform">{menu.icon}</span>
              <span className="font-bold">{menu.label}</span>
            </button>
          ))}
        </div>
        <div className="absolute bottom-0 w-full border-t border-gray-50 p-8">
          <button className="text-gray-400 font-bold hover:text-red-500 transition-colors">로그아웃</button>
        </div>
      </div>
    </>
  )
}
