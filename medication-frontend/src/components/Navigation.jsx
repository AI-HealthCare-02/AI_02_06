'use client'
import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, FileText, Trophy, Pill, User, MessageCircle, X, LogOut } from 'lucide-react'
import LogoutModal, { useLogout } from '@/components/LogoutModal'

import ChatModal from '@/components/ChatModal'
import api from '@/lib/api'

function TypingDots() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-200 shadow-sm px-4 py-3 rounded-2xl rounded-bl-none">
        <div className="flex gap-1.5 items-center">
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'chatDotBounce 1.2s infinite', animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'chatDotBounce 1.2s infinite', animationDelay: '200ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full inline-block" style={{ animation: 'chatDotBounce 1.2s infinite', animationDelay: '400ms' }} />
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
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-end justify-end p-6 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md h-[600px] flex flex-col shadow-2xl border border-gray-100 overflow-hidden">
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-lg text-gray-900">복약 AI 상담</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {isInitializing ? 'AI 상담사 연결 중...' : initError ? '연결 실패' : '약 복용 방법 등 무엇이든 물어보세요'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer p-2 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
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
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {(isInitializing || isLoading) && <TypingDots />}
        </div>

        <div className="p-4 bg-white border-t border-gray-100 flex gap-2 items-center">
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder={isInitializing ? '연결 중...' : '메시지를 입력하세요'}
            disabled={isBlocked}
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-gray-400 transition-all disabled:opacity-50" />
          <button onClick={handleSend}
            disabled={isBlocked || !input.trim()}
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
  const [profileId, setProfileId] = useState(null)

  const isLanding = pathname === '/'
  const isAuthPage = pathname === '/login' || pathname.startsWith('/auth/')

  // 프로필 ID 가져오기 (랜딩/로그인 페이지에서는 호출 안함)
  useEffect(() => {
    if (isLanding || isAuthPage) return
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
  }, [isLanding, isAuthPage])

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
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={profileId} />}
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
            ) : (isAuthPage ? (<></>) : (
              <button onClick={() => setShowLogoutModal(true)}
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md flex items-center gap-1.5">
                <LogOut size={15} />
                로그아웃
              </button>
            ))}
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

      {/* 플로팅 챗 버튼 - 앱 내부 페이지에서만 (로그인/인증 페이지 제외) */}
      {!isLanding && !isAuthPage && (
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
