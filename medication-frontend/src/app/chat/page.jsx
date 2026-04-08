'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Home, User, Camera, Trophy, ClipboardList, MessageCircle, X, Send } from 'lucide-react'

// 동훈 님의 예쁜 스타일이 이식된 ChatModal
function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // 메시지 추가 시 자동 스크롤
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

    // 테스트용 mock 응답
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '지금은 테스트 중이에요. 곧 실제 AI와 연결될 거예요!'
      }])
      setIsLoading(false)
    }, 1500)
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