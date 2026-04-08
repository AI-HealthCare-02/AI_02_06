'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'

function MainSkeleton() {
  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 animate-pulse">
      <div className="flex justify-between items-end mb-10 bg-white p-8 rounded-[32px]">
        <div className="h-12 w-80 bg-gray-200 rounded-xl" />
        <div className="flex gap-8">
          <div className="h-6 w-20 bg-gray-200 rounded" />
          <div className="h-6 w-20 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-8 bg-white rounded-[32px] h-[500px] w-full" />
        <div className="md:col-span-4 space-y-6">
          <div className="bg-white rounded-[32px] h-56 w-full" />
          <div className="bg-white rounded-[32px] h-56 w-full" />
        </div>
      </div>
    </main>
  )
}

// 설문 모달
function SurveyModal({ onClose }) {
  const [form, setForm] = useState({
    age: '', gender: '', height: '', weight: '',
    is_smoking: null, is_drinking: null, conditions: [], allergies: [],
  })

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl w-full max-w-sm max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b border-gray-100 sticky top-0 bg-white">
          <div>
            <h2 className="font-bold text-lg text-gray-900">건강 정보 입력</h2>
            <p className="text-gray-400 text-xs mt-0.5">맞춤 안내를 위해 입력해주세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer text-xl">✕</button>
        </div>
        <div className="p-6 space-y-6">
          {/* 기본 정보 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm text-gray-700">기본 정보</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-[10px] mb-1 block px-1">나이</label>
                <input type="number" placeholder="나이"
                  value={form.age} onChange={(e) => setForm({...form, age: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:border-blue-300 outline-none" />
              </div>
              <div>
                <label className="text-gray-400 text-[10px] mb-1 block px-1">성별</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map(g => (
                    <button key={g} onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-2 rounded-xl text-[10px] font-bold cursor-pointer border transition-all
                        ${form.gender === g ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200 hover:border-gray-300'}`}>
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 생활 습관 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm text-gray-700">생활 습관</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-[10px] mb-1 block px-1">흡연</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_smoking: v})}
                      className={`flex-1 py-2 rounded-xl text-[10px] font-bold cursor-pointer border transition-all
                        ${form.is_smoking === v ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200 hover:border-gray-300'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-[10px] mb-1 block px-1">음주</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_drinking: v})}
                      className={`flex-1 py-2 rounded-xl text-[10px] font-bold cursor-pointer border transition-all
                        ${form.is_drinking === v ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200 hover:border-gray-300'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 버튼 */}
        <div className="flex gap-3 p-6 border-t border-gray-100">
          <button onClick={onClose}
            className="flex-1 border border-gray-200 py-3 rounded-xl text-gray-400 text-sm font-bold cursor-pointer hover:bg-gray-50">
            건너뛰기
          </button>
          <button onClick={onClose}
            className="flex-1 bg-blue-500 text-white py-3 rounded-xl text-sm font-bold cursor-pointer hover:bg-blue-600 shadow-sm">
            완료
          </button>
        </div>
      </div>
    </div>
  )
}

// 챗봇 모달
function ChatModal({ onClose }) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    const initSession = async () => {
      try {
        const saved = sessionStorage.getItem('chatSessionId')
        if (saved) {
          setSessionId(saved)
          const res = await api.get(`/api/v1/messages/session/${saved}`)
          if (res.data.length > 0) {
            const history = res.data.map(m => ({
              role: m.sender_type === 'USER' ? 'user' : 'assistant',
              content: m.content,
            }))
            setMessages(prev => [prev[0], ...history])
          }
          return
        }
        const accountId = localStorage.getItem('accountId')
        const profileId = localStorage.getItem('profileId')
        if (!accountId || !profileId) return
        const res = await api.post('/api/v1/chat-sessions/', {
          account_id: accountId,
          profile_id: profileId,
          title: '복약 상담',
        })
        sessionStorage.setItem('chatSessionId', res.data.id)
        setSessionId(res.data.id)
      } catch (e) {
        console.error('세션 초기화 실패', e)
      }
    }
    initSession()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSend = async () => {
    const message = input.trim()
    if (!message || isLoading || !sessionId) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)
    try {
      const res = await api.post('/api/v1/messages/ask', {
        session_id: sessionId,
        content: message,
      })
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.data.assistant_message.content,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요.',
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl w-full max-w-sm h-[600px] flex flex-col shadow-2xl overflow-hidden">
        <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-white">
          <div>
            <h2 className="font-bold text-gray-900">복약 AI 상담</h2>
            <p className="text-[10px] text-gray-400 mt-0.5">실시간 AI 가이드</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer text-xl p-1">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm shadow-sm
                ${msg.role === 'user' ? 'bg-blue-500 text-white rounded-tr-none' : 'bg-white text-gray-800 rounded-tl-none border border-gray-100'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-100 shadow-sm px-4 py-3 rounded-2xl rounded-tl-none">
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
        
        <div className="p-4 border-t border-gray-100 flex gap-2 items-center bg-white">
  <input type="text" value={input}
    onChange={(e) => setInput(e.target.value)}
    onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
    placeholder={sessionId ? '궁금한 것을 물어보세요' : '세션을 초기화하는 중...'}
    disabled={!sessionId}
    className="flex-1 bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3 text-sm outline-none focus:border-blue-300 transition-all" />
  <button onClick={handleSend}
    disabled={!input.trim() || isLoading || !sessionId}
    className="bg-blue-500 text-white w-10 h-10 rounded-full flex items-center justify-center shadow-md disabled:bg-gray-200 disabled:shadow-none transition-all active:scale-90">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 14-7-3 7 3 7-14-7Z"/><path d="M5 12h11"/></svg>
  </button>
</div>
  )
}

export default function MainPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)

  useEffect(() => {
    setTimeout(() => {
      setIsLoading(false)
      setShowSurvey(true)
    }, 1000)
  }, [])

  if (isLoading) return <MainSkeleton />

  const todayMeds = [
    { time: '08:00', name: '혈압약', done: true },
    { time: '13:00', name: '당뇨약', done: true },
    { time: '19:00', name: '비타민', done: false },
  ]
  const challenge = { title: '금연 챌린지', days: 3, target: 30 }
  const recentPrescription = { date: '2024.03.31', hospital: '내과' }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 12) return { msg: '좋은 아침이에요! ☀️', sub: '오늘 하루도 건강하게 시작해봐요' }
    if (hour >= 12 && hour < 17) return { msg: '좋은 오후예요! 🌤️', sub: '점심 식사 후 약 챙기셨나요?' }
    if (hour >= 17 && hour < 21) return { msg: '좋은 저녁이에요! 🌇', sub: '저녁 복약 시간을 확인해보세요' }
    return { msg: '잠들기 전 확인해요! 🌙', sub: '오늘 복약을 모두 완료했나요?' }
  }
  const greeting = getGreeting()

  return (
    <>
      {/* 설문 모달 */}
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} />}

      {/* 챗봇 모달 */}
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}

      <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative overflow-x-hidden">
        
        {/* 상단 인사말 헤더 (와이드 레이아웃 적용) */}
        <div className="w-full flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-white">
          <div>
            <p className="text-gray-400 text-sm font-bold mb-2 px-1">{greeting.sub}</p>
            <h1 className="text-4xl font-black text-gray-900 leading-tight">
              {greeting.msg.split('!')[0]}! <span className="text-blue-500">홍길동님</span> 반가워요
            </h1>
          </div>
          
          {/* PC용 네비게이션 메뉴 (간격 대확장) */}
          <div className="hidden md:flex items-center gap-12 mb-2">
            <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-blue-500 font-black text-lg hover:opacity-80 transition-all">
              <span className="text-2xl">🏠</span> 홈
            </button>
            <button onClick={() => router.push('/mypage')} className="flex items-center gap-2 text-gray-400 font-bold text-lg hover:text-gray-600 transition-all">
              <span className="text-2xl">👤</span> 마이페이지
            </button>
          </div>
        </div>

        {/* 메인 콘텐츠 대시보드 그리드 */}
        <div className="grid md:grid-cols-12 gap-8">
          
          {/* 좌측 메인 (8칸): 오늘 복약 현황 (너비 봉인 해제) */}
          <div className="md:col-span-8 w-full h-full">
            <div className="bg-white rounded-[40px] shadow-sm p-10 border border-white/50 w-full h-full animate-in fade-in slide-in-from-left-3 duration-500">
              <div className="flex justify-between items-center mb-10">
                <div className="flex items-center gap-4">
                  <span className="text-3xl">💊</span>
                  <h2 className="text-2xl font-black text-gray-900">오늘 복약 현황</h2>
                </div>
                <span className="bg-blue-50 text-blue-600 text-sm font-black px-5 py-2 rounded-2xl">2/3 완료</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-4 mb-12 overflow-hidden shadow-inner">
                <div className="bg-gradient-to-r from-blue-400 to-blue-600 h-4 rounded-full shadow-[0_0_15px_rgba(59,130,246,0.4)] transition-all duration-1000" style={{width: '66%'}} />
              </div>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {todayMeds.map((med, i) => (
                  <div key={i} 
                    onClick={() => router.push('/medication')}
                    className="flex flex-col justify-between p-6 rounded-[32px] bg-slate-50/50 hover:bg-white hover:shadow-xl hover:shadow-blue-50 transition-all border border-transparent hover:border-blue-100 cursor-pointer group active:scale-[0.98] min-h-[140px]">
                    <div className="flex justify-between items-start w-full">
                      <span className="text-gray-400 text-xs font-black">{med.time}</span>
                      {med.done ? (
                        <span className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm shadow-md">✓</span>
                      ) : (
                        <span className="w-8 h-8 bg-white text-blue-500 rounded-full flex items-center justify-center text-xs font-black border-2 border-blue-100 shadow-sm">...</span>
                      )}
                    </div>
                    <span className={`text-lg font-black mt-4 transition-all ${med.done ? 'text-gray-300 line-through' : 'text-gray-800 group-hover:text-blue-600'}`}>
                      {med.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 우측 사이드 (4칸): AI 상담 & 처방전 등록 (너비 봉인 해제) */}
          <div className="md:col-span-4 flex flex-col space-y-8 w-full h-full">
            <div onClick={() => setShowChat(true)}
              className="flex-1 bg-blue-500 rounded-[40px] p-10 text-white shadow-2xl shadow-blue-100 cursor-pointer active:scale-[0.96] transition-all duration-200 relative overflow-hidden group min-h-[220px]">
              <div className="absolute -right-4 -bottom-4 opacity-20 group-hover:scale-110 transition-transform duration-500">
                <svg width="140" height="140" viewBox="0 0 24 24" fill="white"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <p className="text-sm font-black opacity-80 mb-3">복약 궁금증 해소</p>
              <h2 className="text-3xl font-black leading-tight">AI 상담사와<br/>대화하기 💬</h2>
            </div>

            <div onClick={() => router.push('/ocr')}
              className="flex-1 bg-white rounded-[40px] p-10 border border-gray-100 shadow-sm cursor-pointer active:scale-[0.96] transition-all duration-200 relative overflow-hidden group min-h-[220px] flex flex-col justify-center">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-black text-gray-400 mb-3">스마트한 등록</p>
                  <h2 className="text-3xl font-black text-gray-800 leading-tight">처방전<br/>등록하기</h2>
                </div>
                <span className="text-6xl group-hover:rotate-12 transition-transform duration-300">📄</span>
              </div>
            </div>
          </div>

          {/* 하단 영역 (각 6칸): 챌린지 & 최근 처방전 (너비 봉인 해제) */}
          <div className="md:col-span-6 w-full h-full">
            <div onClick={() => router.push('/challenge')}
              className="bg-white rounded-[40px] shadow-sm p-10 border border-gray-100 cursor-pointer active:scale-[0.98] transition-all group h-full">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-black text-gray-900 flex items-center gap-3">
                  <span className="text-2xl">🏆</span> 챌린지 현황
                </h2>
                <div className="w-10 h-10 bg-slate-50 rounded-full flex items-center justify-center text-gray-400 group-hover:bg-blue-500 group-hover:text-white transition-all duration-300 shadow-sm">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="group-hover:translate-x-0.5 transition-transform">
                    <path d="m9 18 6-6-6-6"/>
                  </svg>
                </div>
              </div>
              <div className="flex items-center gap-6 mb-8">
                <div className="bg-orange-50 w-20 h-20 rounded-[28px] flex items-center justify-center text-4xl shadow-md border border-orange-100 animate-bounce-subtle">🔥</div>
                <div className="flex-1">
                  <span className="font-black text-xl text-gray-800">{challenge.title}</span>
                  <p className="text-orange-500 text-sm font-black mt-1.5">{challenge.days}일째 연속 성공!</p>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden shadow-inner">
                <div className="bg-gradient-to-r from-orange-400 to-orange-500 h-3 rounded-full shadow-[0_0_10px_rgba(251,146,60,0.4)] transition-all duration-1000" style={{width: `${(challenge.days/challenge.target)*100}%`}} />
              </div>
            </div>
          </div>

          <div className="md:col-span-6 w-full h-full">
            <div className="bg-white rounded-[40px] shadow-sm p-10 border border-gray-100 h-full w-full">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-black text-gray-900 flex items-center gap-3">
                  <span className="text-2xl">📄</span> 최근 처방전
                </h2>
                <button className="text-xs font-black text-blue-500 hover:bg-blue-50 px-4 py-2 rounded-2xl transition-all border border-blue-100">전체보기</button>
              </div>
              <div className="bg-slate-50/80 rounded-[32px] p-6 flex items-center justify-between border border-gray-100 hover:bg-white hover:shadow-2xl hover:shadow-slate-200 transition-all cursor-pointer group">
                <div className="flex items-center gap-5">
                  <div className="bg-white w-16 h-16 rounded-[24px] flex items-center justify-center text-3xl shadow-sm group-hover:bg-blue-50 transition-colors">📄</div>
                  <div>
                    <p className="text-lg font-black text-gray-800">{recentPrescription.hospital} 처방</p>
                    <p className="text-sm text-gray-400 font-bold mt-1">{recentPrescription.date}</p>
                  </div>
                </div>
                <span className="text-sm font-black text-gray-300 group-hover:text-blue-500 transition-colors">자세히 보기</span>
              </div>
            </div>
          </div>

        </div>

        {/* 하단 네비게이션 (모바일에서만 표시) */}
        <div className="md:hidden fixed bottom-0 left-0 w-full bg-white/90 backdrop-blur-lg border-t border-gray-100 flex py-5 px-8 z-40 shadow-[0_-5px_30px_rgba(0,0,0,0.08)] rounded-t-[40px]">
          <button 
            onClick={() => router.push('/main')} 
            className="flex-1 flex flex-col items-center gap-2 group">
            <span className="text-2xl group-active:scale-90 transition-transform">🏠</span>
            <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">Home</span>
          </button>
          <button 
            onClick={() => router.push('/mypage')} 
            className="flex-1 flex flex-col items-center gap-2 group">
            <span className="text-2xl group-active:scale-90 transition-transform opacity-40 group-hover:opacity-100">👤</span>
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">My</span>
          </button>
        </div>
      </main>
    </>
  )
}
