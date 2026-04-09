'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { Pill, FileText, Flame, Ban, X, Check, Plus, MessageCircle } from 'lucide-react'

// 스켈레톤은 main의 레이아웃을 따름
function MainSkeleton() {
  return (
    <>
      <div className="w-full min-h-[540px] bg-gray-950 animate-pulse" />
      <main className="max-w-7xl mx-auto w-full px-6 py-14 animate-pulse">
        <div className="grid md:grid-cols-12 gap-6">
          <div className="md:col-span-8 bg-gray-100 rounded-[32px] h-[420px]" />
          <div className="md:col-span-4 space-y-6">
            <div className="bg-gray-100 rounded-[32px] h-52" />
            <div className="bg-gray-100 rounded-[32px] h-52" />
          </div>
        </div>
      </main>
    </>
  )
}

// 설문 모달 - 디자인은 main, 필드는 donghoon (음주/흡연 포함)
function SurveyModal({ onClose }) {
  const [form, setForm] = useState({ 
    age: '', gender: '', is_smoking: null, is_drinking: null 
  })

  return (
    <div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="p-8 border-b border-gray-50 sticky top-0 bg-white z-10">
          <h2 className="font-black text-2xl text-gray-900">건강 정보 입력</h2>
          <p className="text-gray-400 text-sm mt-1">영빈 님에게 딱 맞는 복약 가이드를 준비할게요</p>
        </div>
        
        <div className="p-8 space-y-8">
          <div>
            <h3 className="font-bold mb-4 text-gray-800">기본 정보</h3>
            <div className="grid grid-cols-2 gap-4">
              <input type="number" placeholder="나이" className="bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3 text-sm focus:border-gray-900 outline-none" />
              <div className="flex gap-2">
                {['M', 'F'].map(g => (
                  <button key={g} onClick={() => setForm({...form, gender: g})}
                    className={`flex-1 py-3 rounded-2xl text-xs font-black border transition-all
                      ${form.gender === g ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-400 border-gray-100'}`}>
                    {g === 'M' ? '남성' : '여성'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-bold mb-4 text-gray-800">생활 습관</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-gray-400 text-[10px] font-bold uppercase tracking-widest px-1">흡연 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_smoking: v})}
                      className={`flex-1 py-3 rounded-2xl text-[10px] font-black border transition-all
                        ${form.is_smoking === v ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-400 border-gray-100'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-gray-400 text-[10px] font-bold uppercase tracking-widest px-1">음주 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_drinking: v})}
                      className={`flex-1 py-3 rounded-2xl text-[10px] font-black border transition-all
                        ${form.is_drinking === v ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-400 border-gray-100'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 flex gap-4">
            <button onClick={onClose} className="flex-1 border border-gray-100 py-4 rounded-2xl text-gray-400 font-bold hover:bg-gray-50 transition-all">다음에</button>
            <button onClick={onClose} className="flex-1 bg-gray-900 text-white py-4 rounded-2xl font-black hover:bg-gray-700 transition-all">저장하기</button>
          </div>
        </div>
      </div>
    </div>
  )
}

// 챗봇 모달 (donghoon 로직 유지)
function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setIsLoading(true)
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: '곧 실제 AI와 연결될 예정입니다!' }])
      setIsLoading(false)
    }, 1000)
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md h-[600px] flex flex-col shadow-2xl overflow-hidden">
        <div className="p-6 border-b border-gray-50 flex justify-between items-center">
          <h2 className="font-bold text-gray-900">AI 상담사</h2>
          <button onClick={onClose} className="text-gray-400"><X size={20}/></button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] p-4 rounded-2xl text-sm ${m.role === 'user' ? 'bg-gray-900 text-white' : 'bg-white border border-gray-100 text-gray-800'}`}>{m.content}</div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="p-4 bg-white border-t border-gray-50 flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} onKeyUp={e => e.key === 'Enter' && handleSend()} className="flex-1 bg-gray-50 px-4 py-3 rounded-xl outline-none text-sm" placeholder="메시지 입력..." />
          <button onClick={handleSend} className="bg-gray-900 text-white p-3 rounded-xl"><Check size={20}/></button>
        </div>
      </div>
    </div>
  )
}

export default function MainPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [userName, setUserName] = useState('사용자')
  const [greeting, setGreeting] = useState({ msg: '반가워요', sub: '오늘 하루도 건강하게 시작해봐요' })

  useEffect(() => {
    const initPage = async () => {
      try {
        setIsLoading(true)
        const profileRes = await api.get('/api/v1/profiles/')
        if (profileRes.data?.length > 0) {
          const self = profileRes.data.find(p => p.relation_type === 'SELF') || profileRes.data[0]
          setUserName(self.name.split('(')[0])
        }
        const hour = new Date().getHours()
        if (hour < 12) setGreeting({ msg: '좋은 아침이에요', sub: '오늘 하루도 건강하게 시작해봐요' })
        else if (hour < 17) setGreeting({ msg: '좋은 오후예요', sub: '점심 식사 후 약 챙기셨나요?' })
        else setGreeting({ msg: '좋은 저녁이에요', sub: '저녁 복약 시간을 확인해보세요' })
      } catch (err) { console.error(err) } finally { setIsLoading(false) }
    }
    initPage()
  }, [])

  if (isLoading) return <MainSkeleton />

  return (
    <>
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} />}
      {showChat && <ChatModal onClose={() => setShowChat(false)} />}

      {/* ── 히어로 섹션 (main의 다크 테마 + donghoon의 이름 데이터) ── */}
      <section className="relative w-full min-h-[540px] flex items-center justify-center overflow-hidden bg-black">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="relative z-10 text-center px-6 max-w-3xl mx-auto py-24">
          <p className="text-gray-500 text-xs font-bold mb-5 tracking-[0.2em] uppercase">{greeting.sub}</p>
          <h1 className="text-5xl md:text-7xl font-black text-white leading-tight mb-8">
            {greeting.msg},<br /><span className="text-gray-600">{userName} 님</span>
          </h1>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button onClick={() => router.push('/ocr')} className="px-8 py-4 bg-white text-black font-bold rounded-full hover:bg-gray-100 transition-all cursor-pointer">처방전 등록하기</button>
            <button onClick={() => setShowChat(true)} className="px-8 py-4 bg-gray-900 text-white font-bold rounded-full border border-gray-800 hover:bg-gray-800 transition-all cursor-pointer flex items-center gap-2 justify-center">
              <MessageCircle size={20}/> AI 상담하기
            </button>
          </div>
        </div>
      </section>

      {/* ── 대시보드 ── */}
      <main className="max-w-7xl mx-auto w-full px-6 py-14">
        <div className="grid md:grid-cols-12 gap-6 items-start">
          {/* 복약 현황 */}
          <section className="md:col-span-8 bg-white rounded-[32px] p-8 border border-gray-100">
            <div className="flex justify-between items-center mb-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-100 rounded-2xl flex items-center justify-center"><Pill size={20} className="text-gray-900" /></div>
                <h2 className="text-xl font-bold text-gray-900">오늘 복약 현황</h2>
              </div>
              <span className="text-sm font-black text-gray-900">2/3 완료</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5 mb-10 overflow-hidden">
              <div className="bg-black h-full transition-all duration-1000" style={{ width: '66%' }} />
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[{time: '08:00', name: '혈압약', done: true}, {time: '13:00', name: '당뇨약', done: true}, {time: '19:00', name: '비타민', done: false}].map((med, i) => (
                <div key={i} className={`p-6 rounded-2xl border transition-all ${med.done ? 'bg-gray-50 border-gray-100' : 'bg-white border-gray-200 shadow-sm'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-xs font-bold text-gray-400">{med.time}</span>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${med.done ? 'bg-black text-white' : 'bg-gray-100 text-gray-400'}`}>
                      {med.done ? <Check size={12} /> : <Plus size={12} />}
                    </div>
                  </div>
                  <h3 className={`font-bold ${med.done ? 'text-gray-400 line-through' : 'text-gray-900'}`}>{med.name}</h3>
                </div>
              ))}
            </div>
          </section>

          {/* 사이드바 */}
          <div className="md:col-span-4 space-y-6">
            <div onClick={() => router.push('/challenge')} className="bg-gray-900 rounded-[32px] p-8 text-white cursor-pointer hover:-translate-y-1 transition-all min-h-[220px] flex flex-col justify-end relative overflow-hidden group">
              <Flame size={120} className="absolute -right-4 -top-4 opacity-[0.05] group-hover:scale-110 transition-transform" />
              <p className="text-gray-500 font-bold text-xs mb-2 tracking-widest">CHALLENGE</p>
              <h2 className="text-2xl font-black mb-3">금연 챌린지</h2>
              <p className="text-orange-500 text-sm font-bold">3일째 성공 중! →</p>
            </div>
          </div>
        </div>
      </main>
    </>
  )
}