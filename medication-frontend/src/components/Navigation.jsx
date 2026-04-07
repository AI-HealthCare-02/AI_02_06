'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'

function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    }, 100)
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
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-end p-6">
      <div className="bg-white rounded-2xl w-full max-w-xl h-[700px] flex flex-col shadow-xl">
        <div className="flex justify-between items-center p-5 border-b border-gray-100">
          <div>
            <h2 className="font-bold text-lg">복약 AI 상담</h2>
            <p className="text-xs text-gray-400">약 복용 방법, 부작용 등 무엇이든 물어보세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer text-xl">✕</button>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-sm px-4 py-3 rounded-2xl text-sm
                ${msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-800 rounded-bl-none'
                }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-none">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 flex gap-2 items-center">
          <button className="w-9 h-9 bg-gray-100 rounded-full text-gray-400 flex items-center justify-center shrink-0 cursor-pointer hover:bg-gray-200">
            +
          </button>
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder="메시지를 입력하세요"
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm outline-none focus:border-blue-300" />
          <button onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`w-9 h-9 rounded-full flex items-center justify-center text-sm cursor-pointer
              ${isLoading || !input.trim()
                ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}>
            →
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
    { icon: '🏠', label: '홈', path: '/main' },
    { icon: '👤', label: '마이페이지', path: '/mypage' },
    { icon: '📷', label: '처방전 등록', path: '/ocr' },
    { icon: '🏆', label: '챌린지', path: '/challenge' },
    { icon: '📋', label: '용법/주의사항', path: '/medication' },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}

      {/* 햄버거 버튼 */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-4 left-4 z-40 w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center cursor-pointer hover:shadow-lg text-lg">
        ≡
      </button>

      {/* 챗봇 플로팅 버튼 */}
      <button
        onClick={() => setShowChat(true)}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-500 rounded-full shadow-lg flex items-center justify-center text-white text-2xl cursor-pointer hover:bg-blue-600">
        💊
      </button>

      {isOpen && (
        <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-black/50 z-40" />
      )}

      <div className={`fixed top-0 left-0 h-full w-64 bg-white z-50 shadow-xl transform transition-transform duration-300
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center px-6 py-5 border-b border-gray-100">
          <h2 className="font-bold text-lg">💊 Downforce</h2>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-black cursor-pointer text-xl">✕</button>
        </div>
        <div className="py-4">
          {menus.map((menu, i) => (
            <button key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className="flex items-center gap-4 w-full px-6 py-4 text-sm hover:bg-gray-50 cursor-pointer">
              <span className="text-xl">{menu.icon}</span>
              <span className="font-medium">{menu.label}</span>
            </button>
          ))}
        </div>
        <div className="absolute bottom-0 w-full border-t border-gray-100 p-6">
          <button className="text-gray-400 text-sm cursor-pointer hover:text-black">로그아웃</button>
        </div>
      </div>
    </>
  )
}