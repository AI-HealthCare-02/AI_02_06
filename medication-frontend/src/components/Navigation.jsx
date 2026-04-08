'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, FileText, Trophy, Pill, User, MessageCircle, X, Menu, LogOut, Send } from 'lucide-react'

function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요.' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = () => {
    const message = input.trim()
    if (!message || isLoading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '지금은 테스트 중이에요. 곧 실제 AI와 연결될 거예요!'
      }])
      setIsLoading(false)
    }, 1500)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-end justify-end p-6 backdrop-blur-sm">
      <div className="bg-white rounded-2xl w-full max-w-md h-[600px] flex flex-col shadow-2xl border border-gray-100 overflow-hidden">
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
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
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user'
                  ? 'bg-gray-900 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-none shadow-sm flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
              </div>
            </div>
          )}
        </div>

        <div className="p-4 bg-white border-t border-gray-100 flex gap-2 items-center">
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder="메시지를 입력하세요"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-gray-400 transition-all" />
          <button onClick={handleSend}
            disabled={isLoading || !input.trim()}
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

      <nav className={`fixed top-0 w-full z-50 transition-all duration-200 border-b
        ${scrolled
          ? 'bg-white/90 backdrop-blur-xl border-gray-200/80'
          : 'bg-white border-gray-200'}`}>
        <div className="max-w-[1400px] mx-auto px-6 flex justify-between items-center h-14">

          {/* 로고 */}
          <Link href={isLanding ? '/' : '/main'} className="flex items-center gap-2 flex-shrink-0">
            <div className="w-7 h-7 bg-gray-900 rounded-md flex items-center justify-center text-white">
              <Pill size={14} />
            </div>
            <span className="font-semibold text-[15px] tracking-tight text-gray-900">Downforce</span>
          </Link>

          {/* 앱 내부 페이지 데스크탑 네비게이션 */}
          {!isLanding && (
            <div className="hidden md:flex items-center">
              {menus.map((menu) => (
                <Link
                  key={menu.path}
                  href={menu.path}
                  className={`px-3.5 py-1.5 text-sm rounded-md transition-colors
                    ${pathname === menu.path
                      ? 'text-gray-900 font-medium'
                      : 'text-gray-500 hover:text-gray-900'}`}
                >
                  {menu.label}
                </Link>
              ))}
            </div>
          )}

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
              <button className="text-sm text-gray-500 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md flex items-center gap-1.5">
                <LogOut size={15} />
                로그아웃
              </button>
            )}
          </div>

          {/* 모바일: 랜딩은 로그인 버튼, 앱 페이지는 햄버거 */}
          {isLanding ? (
            <button
              onClick={() => router.push('/login')}
              className="md:hidden text-sm bg-gray-900 text-white font-medium cursor-pointer px-4 py-1.5 rounded-lg">
              로그인
            </button>
          ) : (
            <button
              onClick={() => setIsOpen(true)}
              className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg text-gray-600 hover:bg-gray-100 cursor-pointer transition-colors">
              <Menu size={20} />
            </button>
          )}
        </div>
      </nav>

      {/* 플로팅 챗 버튼 - 앱 내부 페이지에서만 */}
      {!isLanding && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed bottom-6 right-6 z-[60] w-12 h-12 bg-gray-900 rounded-2xl shadow-lg flex items-center justify-center text-white cursor-pointer hover:bg-gray-700 hover:scale-105 transition-all active:scale-95">
          <MessageCircle size={20} />
        </button>
      )}

      {/* 모바일 오버레이 */}
      {isOpen && (
        <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-black/30 backdrop-blur-[2px] z-[70] md:hidden" />
      )}

      {/* 모바일 드로어 */}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white z-[80] shadow-2xl transform transition-transform duration-300 md:hidden
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-900 rounded-md flex items-center justify-center text-white">
              <Pill size={14} />
            </div>
            <span className="font-semibold text-[15px] text-gray-900">Downforce</span>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-black cursor-pointer p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="py-3 px-3">
          {menus.map((menu, i) => (
            <button key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className={`flex items-center gap-3 w-full px-4 py-3.5 rounded-xl transition-all cursor-pointer text-sm
                ${pathname === menu.path ? 'bg-gray-100 text-gray-900 font-medium' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'}`}>
              <div className={pathname === menu.path ? 'text-gray-900' : 'text-gray-400'}>
                {menu.icon}
              </div>
              <span>{menu.label}</span>
            </button>
          ))}
        </div>
        <div className="absolute bottom-0 w-full p-5 border-t border-gray-100">
          <button className="flex items-center gap-3 text-sm text-gray-500 hover:text-red-500 transition-colors cursor-pointer w-full px-4 py-3 rounded-xl hover:bg-red-50">
            <LogOut size={16} />
            로그아웃
          </button>
        </div>
      </div>

      <div className="h-14" />
    </>
  )
}
