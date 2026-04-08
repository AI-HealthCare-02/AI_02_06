'use client'
import { useState, useEffect, useRef } from 'react' // useState, useRef 추가됨
import { useRouter } from 'next/navigation'
import Header from '../../components/Header' // 누락되었을 수 있는 컴포넌트 임포트 확인 필요

export default function ChatPage() {
  const router = useRouter()
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 메시지 추가 시 자동 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = () => {
    const message = input.trim()
    if (!message || isLoading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)

    // 실제 AI 연결 전 테스트용 mock 응답 (1.5초 후 응답)
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '지금은 테스트 중이에요. 곧 실제 AI와 연결될 거예요!'
      }])
      setIsLoading(false)
    }, 1500)
  }

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col">
      <Header title="복약 AI 상담" subtitle="무엇이든 물어보세요" showBack={true} />

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 pb-32">
        {messages.map((msg, i) => (
          <div 
            key={i} 
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-1 duration-300`}
          >
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm shadow-sm
              ${msg.role === 'user'
                ? 'bg-blue-500 text-white rounded-br-none'
                : 'bg-white text-gray-800 rounded-bl-none border border-gray-100'
              }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* 로딩 애니메이션 (말줄임표 바운스) */}
        {isLoading && (
          <div className="flex justify-start animate-in fade-in duration-300">
            <div className="bg-white border border-gray-100 shadow-sm px-4 py-4 rounded-2xl rounded-bl-none">
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 입력창 - 하단 고정 */}
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 px-6 py-5 z-40">
        <div className="max-w-3xl mx-auto flex gap-3 items-center">
          <button className="w-11 h-11 bg-gray-50 text-gray-400 rounded-full flex items-center justify-center shrink-0 hover:bg-gray-100 transition-all border border-gray-100 cursor-pointer active:scale-[0.98]">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14m-7-7v14"/>
            </svg>
          </button>
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyUp={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSend() } }}
              placeholder="메시지를 입력하세요"
              className="w-full bg-gray-50 border border-gray-100 rounded-2xl px-5 py-3 text-sm outline-none focus:border-blue-300 focus:bg-white transition-all"
            />
          </div>
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`w-11 h-11 rounded-full flex items-center justify-center shrink-0 transition-all shadow-sm
              ${isLoading || !input.trim()
                ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600 active:scale-90 cursor-pointer'
              }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="m5 12 14-7-3 7 3 7-14-7Z"/><path d="M5 12h11"/>
            </svg>
          </button>
        </div>
      </div>
    </main>
  )
}