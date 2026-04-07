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
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-white text-gray-800 rounded-bl-none border border-gray-200'
                }`}>
                {msg.content}
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
            placeholder="메시지를 입력하세요"
            className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-blue-500 transition-all" />
          <button onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="w-10 h-10 rounded-xl flex items-center justify-center bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-100 disabled:text-gray-300 shadow-md active:scale-95 transition-all cursor-pointer">
            <Send size={18} />
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

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  const menus = [
    { label: '홈',         path: '/main',       icon: <Home size={20} /> },
    { label: '처방전 등록', path: '/ocr',        icon: <FileText size={20} /> },
    { label: '챌린지',     path: '/challenge',  icon: <Trophy size={20} /> },
    { label: '복약 가이드', path: '/medication', icon: <Pill size={20} /> },
    { label: '마이페이지', path: '/mypage',     icon: <User size={20} /> },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}

      <nav className={`fixed top-0 w-full z-50 transition-all duration-300 border-b
        ${scrolled 
          ? 'bg-white/80 backdrop-blur-md border-gray-100 py-3 shadow-sm' 
          : 'bg-white border-transparent py-5'}`}>
        <div className="max-w-7xl mx-auto px-6 flex justify-between items-center">
          <Link href="/main" className="flex items-center gap-2 group">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-100 group-hover:rotate-6 transition-transform">
              <Pill size={20} />
            </div>
            <span className="font-black text-xl tracking-tight text-gray-900">Downforce</span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {menus.map((menu) => (
              <Link
                key={menu.path}
                href={menu.path}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all
                  ${pathname === menu.path 
                    ? 'text-blue-600 bg-blue-50' 
                    : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50'}`}
              >
                {menu.icon}
                {menu.label}
              </Link>
            ))}
            <div className="h-4 w-[1px] bg-gray-200 mx-4" />
            <button className="text-sm font-bold text-gray-400 hover:text-red-500 transition-colors cursor-pointer flex items-center gap-2 px-3">
              <LogOut size={18} />
              로그아웃
            </button>
          </div>

          <button
            onClick={() => setIsOpen(true)}
            className="md:hidden w-10 h-10 flex items-center justify-center rounded-xl bg-gray-50 text-gray-600 cursor-pointer">
            <Menu size={24} />
          </button>
        </div>
      </nav>

      <button
        onClick={() => setShowChat(true)}
        className="fixed bottom-8 right-8 z-[60] w-14 h-14 bg-blue-600 rounded-2xl shadow-xl shadow-blue-200 flex items-center justify-center text-white cursor-pointer hover:bg-blue-700 hover:scale-110 transition-all active:scale-95 group">
        <MessageCircle size={28} className="group-hover:rotate-12 transition-transform" />
      </button>

      {isOpen && (
        <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[70] md:hidden" />
      )}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white z-[80] shadow-2xl transform transition-transform duration-300 md:hidden
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center px-6 py-6 border-b border-gray-50">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white">
              <Pill size={16} />
            </div>
            <span className="font-black text-lg text-gray-900">Downforce</span>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-black cursor-pointer p-1">
            <X size={24} />
          </button>
        </div>
        <div className="py-4 px-3">
          {menus.map((menu, i) => (
            <button key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className={`flex items-center gap-4 w-full px-4 py-4 rounded-2xl transition-all cursor-pointer
                ${pathname === menu.path ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}>
              <div className={pathname === menu.path ? 'text-blue-600' : 'text-gray-400'}>
                {menu.icon}
              </div>
              <span className="font-bold">{menu.label}</span>
            </button>
          ))}
        </div>
        <div className="absolute bottom-0 w-full p-6 border-t border-gray-50">
          <button className="flex items-center gap-3 text-gray-400 font-bold hover:text-red-500 transition-colors cursor-pointer w-full">
            <LogOut size={20} />
            로그아웃
          </button>
        </div>
      </div>

      <div className="h-[72px] md:h-[84px]" />
    </>
  )
}
