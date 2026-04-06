'use client'
import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ChatPage() {
  const router = useRouter()
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
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
    <main className="min-h-screen bg-gray-50 flex flex-col">

      {/* 상단 헤더 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push('/main')}
          className="text-gray-400 hover:text-black cursor-pointer text-xl">
          ←
        </button>
        <div>
          <h1 className="font-bold">복약 AI 상담</h1>
          <p className="text-xs text-gray-400">약 복용 방법, 부작용 등 무엇이든 물어보세요</p>
        </div>
      </div>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 pb-32">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs px-4 py-3 rounded-2xl text-sm
              ${msg.role === 'user'
                ? 'bg-blue-500 text-white rounded-br-sm'
                : 'bg-white shadow-sm text-gray-800 rounded-bl-sm'
              }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* 로딩 점 애니메이션 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white shadow-sm px-4 py-3 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 입력창 - 하단 고정 */}
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 px-6 py-4">
        <div className="flex gap-2 items-center">
          <button className="w-10 h-10 bg-gray-100 rounded-full text-gray-400 text-xl cursor-pointer hover:bg-gray-200 flex items-center justify-center shrink-0">
            +
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleSend() } }}
            placeholder="메시지를 입력하세요"
            className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-300"
          />
          <button
            onClick={handleSend}
            disabled={isLoading}
            className="bg-blue-500 text-white px-5 py-3 rounded-xl text-sm font-semibold cursor-pointer hover:bg-blue-600 shrink-0 disabled:opacity-50">
            전송
          </button>
        </div>
      </div>

    </main>
  )
}