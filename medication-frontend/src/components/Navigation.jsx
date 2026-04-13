'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, FileText, Trophy, Pill, User, MessageCircle, X, Menu, LogOut, Send } from 'lucide-react'
import LogoutModal, { useLogout } from '@/components/LogoutModal'
import api from '@/lib/api'
import { showError } from '@/lib/errors'

// 실제 AI와 연동된 ChatModal
function ChatModal({ onClose }) {
  const router = useRouter()
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [profileId, setProfileId] = useState(null)
  const [hasNoProfile, setHasNoProfile] = useState(false)
  const scrollRef = useRef(null)

  // 초기 프로필 로드
  useEffect(() => {
    const initChat = async () => {
      try {
        const profileRes = await api.get('/api/v1/profiles/')
        if (profileRes.data && profileRes.data.length > 0) {
          setProfileId(profileRes.data[0].id)
          setHasNoProfile(false)
        } else {
          setHasNoProfile(true)
          setMessages([
            { 
              role: 'assistant', 
              content: '상담을 시작하기 전에 건강 정보를 먼저 등록해 주세요. 맞춤형 복약 가이드를 제공해 드릴 수 있습니다! 😊' 
            }
          ])
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
    if (!messageContent || isLoading || hasNoProfile) return
    
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: messageContent }])
    setIsLoading(true)

    try {
      let currentSessionId = sessionId

      if (!currentSessionId) {
        if (!profileId) {
          throw new Error('프로필 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
        }

        const sessionRes = await api.post('/api/v1/chat-sessions/', {
          profile_id: profileId,
          title: messageContent.substring(0, 20) + (messageContent.length > 20 ? '...' : '')
        })
        currentSessionId = sessionRes.data.id
        setSessionId(currentSessionId)
      }

      const askRes = await api.post('/api/v1/messages/ask', {
        session_id: currentSessionId,
        content: messageContent
      })

      const aiReply = askRes.data.assistant_message.content
      setMessages(prev => [...prev, { role: 'assistant', content: aiReply }])
    } catch (err) {
      console.error('채팅 전송 에러:', err)
      setMessages(prev => [...prev, { role: 'assistant', content: '죄송합니다. 서비스 연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.' }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-end justify-end p-6 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md h-[600px] flex flex-col shadow-2xl border border-gray-100 overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
        <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-white">
          <div>
            <h2 className="font-bold text-lg text-gray-900">복약 AI 상담</h2>
            <p className="text-xs text-gray-400">약 복용 방법 등 무엇이든 물어보세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer p-2 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm whitespace-pre-wrap
                ${msg.role === 'user'
                  ? 'bg-gray-900 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.content}
                
                {/* 프로필 등록 유도 버튼 */}
                {hasNoProfile && msg.role === 'assistant' && i === 0 && (
                  <button 
                    onClick={() => { onClose(); router.push('/survey') }}
                    className="mt-3 w-full bg-blue-600 text-white py-2 rounded-xl font-bold text-xs hover:bg-blue-700 transition-all active:scale-95"
                  >
                    건강 정보 등록하러 가기 →
                  </button>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
              </div>
            </div>
          )}
        </div>

        <div className="p-4 bg-white border-t border-gray-100 flex gap-2 items-center">
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder={hasNoProfile ? "정보를 먼저 등록해주세요" : "메시지를 입력하세요"}
            disabled={hasNoProfile || isLoading}
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-gray-400 transition-all disabled:cursor-not-allowed" />
          <button onClick={handleSend}
            disabled={isLoading || !input.trim() || hasNoProfile}
            className="w-10 h-10 rounded-xl flex items-center justify-center bg-gray-900 text-white hover:bg-gray-700 disabled:bg-gray-100 disabled:text-gray-300 active:scale-95 transition-all cursor-pointer">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Navigation() {
  const router = useRouter()
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  const isLanding = pathname === '/'

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  const { showLogoutModal, setShowLogoutModal, handleLogout } = useLogout()

  const menus = [
    { label: '홈',         path: '/main',       icon: <Home size={18} /> },
    { label: '처방전 등록', path: '/ocr',        icon: <FileText size={18} /> },
    { label: '챌린지',     path: '/challenge',  icon: <Trophy size={18} /> },
    { label: '복약 가이드', path: '/medication', icon: <Pill size={18} /> },
    { label: '마이페이지', path: '/mypage',     icon: <User size={18} /> },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}
      {showLogoutModal && <LogoutModal onClose={() => setShowLogoutModal(false)} onConfirm={handleLogout} />}

      <nav className={`fixed top-0 w-full z-50 transition-all duration-200 border-b
        ${scrolled
          ? 'bg-white/90 backdrop-blur-xl border-gray-200/80'
          : 'bg-white border-gray-200'}`}>
        <div className="max-w-[1400px] mx-auto px-6 flex justify-between items-center h-14">

          <div className="flex items-center gap-10">
            {/* 로고 */}
            <Link href={isLanding ? '/' : '/main'} className="flex items-center gap-2 flex-shrink-0">
              <div className="w-7 h-7 bg-gray-900 rounded-md flex items-center justify-center text-white">
                <Pill size={14} />
              </div>
              <span className="font-semibold text-[15px] tracking-tight text-gray-900">Downforce</span>
            </Link>

            {/* 앱 내부 페이지 데스크탑 네비게이션 */}
            {!isLanding && (
              <div className="hidden md:flex items-center gap-1">
                {menus.map((menu) => (
                  <Link
                    key={menu.path}
                    href={menu.path}
                    className={`px-4 py-1.5 text-[13px] rounded-lg transition-all
                      ${pathname === menu.path
                        ? 'text-gray-900 font-bold bg-gray-50'
                        : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50/50'}`}
                  >
                    {menu.label}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* 오른쪽 버튼 영역 */}
          <div className="hidden md:flex items-center gap-2">
            {isLanding ? (
              <>
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md">
                  로그인
                </button>
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm bg-gray-900 text-white font-medium cursor-pointer px-4 py-1.5 rounded-lg hover:bg-gray-700 transition-colors">
                  시작하기
                </button>
              </>
            ) : (
              <button onClick={() => setShowLogoutModal(true)}
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md flex items-center gap-1.5">
                <LogOut size={15} />
                로그아웃
              </button>
            )}
          </div>

          {/* 모바일: 랜딩은 로그인 버튼, 앱 페이지는 표시 없음 (하단 네비게이션 사용) */}
          {isLanding && (
            <button
              onClick={() => router.push('/login')}
              className="md:hidden text-sm bg-gray-900 text-white font-medium cursor-pointer px-4 py-1.5 rounded-lg">
              로그인
            </button>
          )}
        </div>
      </nav>

      {/* 플로팅 챗 버튼 - 앱 내부 페이지에서만 */}
      {!isLanding && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed bottom-24 right-6 z-[60] w-12 h-12 bg-gray-900 rounded-2xl shadow-lg flex items-center justify-center text-white cursor-pointer hover:bg-gray-700 hover:scale-105 transition-all active:scale-95">
          <MessageCircle size={20} />
        </button>
      )}

      <div className="h-14" />
    </>
  )
}
