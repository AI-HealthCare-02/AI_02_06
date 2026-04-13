'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Home, User, Camera, Trophy, ClipboardList, MessageCircle, X, Send } from 'lucide-react'
import api from '@/lib/api'
import { showError } from '@/lib/errors'

// 실제 AI와 연동된 ChatModal
function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [profileId, setProfileId] = useState(null)
  const scrollRef = useRef(null)

  // 초기 프로필 로드 및 세션 준비
  useEffect(() => {
    const initChat = async () => {
      try {
        // 1. 프로필 목록 조회 (첫 번째 프로필 사용)
        const profileRes = await api.get('/api/v1/profiles/')
        if (profileRes.data && profileRes.data.length > 0) {
          const pId = profileRes.data[0].id
          setProfileId(pId)

          // 2. 해당 프로필의 최근 세션이 있는지 확인 (선택 사항)
          // 여기서는 간단하게 매번 새 세션을 생성하거나, 
          // 첫 메시지 전송 시 생성하도록 구현합니다.
        } else {
          // 프로필이 없는 경우 처리 (필요 시 설문 페이지로 유도)
          console.warn('사용 가능한 프로필이 없습니다.')
        }
      } catch (err) {
        console.error('채팅 초기화 실패:', err)
      }
    }
    initChat()
  }, [])

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = async () => {
    const messageContent = input.trim()
    if (!messageContent || isLoading) return
    
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: messageContent }])
    setIsLoading(true)

    try {
      let currentSessionId = sessionId

      // 1. 세션이 없으면 먼저 생성
      if (!currentSessionId) {
        if (!profileId) {
          // 프로필이 아직 로드되지 않았거나 없는 경우 임시 처리
          throw new Error('프로필 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
        }

        const sessionRes = await api.post('/api/v1/chat-sessions/', {
          profile_id: profileId,
          title: messageContent.substring(0, 20) + (messageContent.length > 20 ? '...' : '')
        })
        currentSessionId = sessionRes.data.id
        setSessionId(currentSessionId)
      }

      // 2. AI에게 질문 전송
      const askRes = await api.post('/api/v1/messages/ask', {
        session_id: currentSessionId,
        content: messageContent
      })

      // 3. AI 응답 추가
      const aiReply = askRes.data.assistant_message.content
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: aiReply
      }])
    } catch (err) {
      showError(err)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 메시지를 처리하는 중에 오류가 발생했습니다. 다시 시도해 주세요.'
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-end p-6">
      <div className="bg-white rounded-3xl w-full max-w-xl h-[700px] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* 헤더 */}
        <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-white">
          <div>
            <h2 className="font-bold text-xl text-gray-900">복약 AI 상담</h2>
            <p className="text-xs text-gray-400 mt-1">약 복용 방법, 부작용 등 무엇이든 물어보세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer p-2 transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* 채팅 영역 - 동훈 님 스타일 적용 */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-1`}>
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-100'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}

          {/* 로딩 애니메이션 - 동훈 님 버전 */}
          {isLoading && (
            <div className="flex justify-start animate-in fade-in">
              <div className="bg-white border border-gray-100 shadow-sm px-4 py-4 rounded-2xl rounded-bl-none">
                <div className="flex gap-1.5">
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                  <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 입력창 */}
        <div className="p-5 border-t border-gray-100 bg-white flex gap-3 items-center">
          <button className="w-10 h-10 bg-gray-50 text-gray-400 rounded-full flex items-center justify-center shrink-0 hover:bg-gray-100 border border-gray-100 transition-all active:scale-95">
            +
          </button>
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder="메시지를 입력하세요"
            className="flex-1 bg-gray-50 border border-gray-100 rounded-2xl px-5 py-3 text-sm outline-none focus:border-blue-300 focus:bg-white transition-all" 
          />
          <button 
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all shadow-md active:scale-90
              ${isLoading || !input.trim()
                ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
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

  const menus = [
    { icon: <Home size={18} />, label: '홈', path: '/main' },
    { icon: <User size={18} />, label: '마이페이지', path: '/mypage' },
    { icon: <Camera size={18} />, label: '처방전 등록', path: '/ocr' },
    { icon: <Trophy size={18} />, label: '챌린지', path: '/challenge' },
    { icon: <ClipboardList size={18} />, label: '용법/주의사항', path: '/medication' },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}

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