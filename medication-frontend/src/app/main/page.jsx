'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

function MainSkeleton() {
  return (
    <main className="min-h-screen bg-gray-50 pb-20 animate-pulse">
      <div className="bg-white border-b border-gray-200 px-10 py-5">
        <div className="h-3 w-40 bg-gray-200 rounded mb-2" />
        <div className="h-5 w-32 bg-gray-200 rounded" />
      </div>
      <div className="px-10 py-6 grid grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-6 col-span-2 row-span-2 h-64" />
        <div className="bg-gray-200 rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
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
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b border-gray-100 sticky top-0 bg-white">
          <div>
            <h2 className="font-bold text-lg">건강 정보 입력</h2>
            <p className="text-gray-400 text-xs">맞춤 복약 안내를 위해 건강 정보를 입력해주세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer text-xl">✕</button>
        </div>
        <div className="p-6 space-y-6">
          {/* 기본 정보 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm">기본 정보</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs mb-1 block">나이</label>
                <input type="number" placeholder="나이"
                  value={form.age} onChange={(e) => setForm({...form, age: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">성별</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map(g => (
                    <button key={g} onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-2 rounded-xl text-xs font-semibold cursor-pointer border
                        ${form.gender === g ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200'}`}>
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">키 (cm)</label>
                <input type="number" placeholder="키"
                  value={form.height} onChange={(e) => setForm({...form, height: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">몸무게 (kg)</label>
                <input type="number" placeholder="몸무게"
                  value={form.weight} onChange={(e) => setForm({...form, weight: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm" />
              </div>
            </div>
          </div>

          {/* 생활 습관 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm">생활 습관</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs mb-1 block">흡연</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_smoking: v})}
                      className={`flex-1 py-2 rounded-xl text-xs font-semibold cursor-pointer border
                        ${form.is_smoking === v ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">음주</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setForm({...form, is_drinking: v})}
                      className={`flex-1 py-2 rounded-xl text-xs font-semibold cursor-pointer border
                        ${form.is_drinking === v ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200'}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 기저질환 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm">기저질환</h3>
            <div className="flex flex-wrap gap-2">
              {['고혈압', '당뇨', '고지혈증', '심장질환', '천식', '신장질환', '없음'].map(item => (
                <button key={item}
                  onClick={() => {
                    const updated = form.conditions.includes(item)
                      ? form.conditions.filter(c => c !== item)
                      : [...form.conditions, item]
                    setForm({...form, conditions: updated})
                  }}
                  className={`px-3 py-1.5 rounded-full text-xs cursor-pointer border
                    ${form.conditions.includes(item) ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200'}`}>
                  {item}
                </button>
              ))}
            </div>
          </div>

          {/* 알레르기 */}
          <div>
            <h3 className="font-semibold mb-3 text-sm">알레르기</h3>
            <div className="flex flex-wrap gap-2">
              {['페니실린', '아스피린', '항생제', '소염제', '없음'].map(item => (
                <button key={item}
                  onClick={() => {
                    const updated = form.allergies.includes(item)
                      ? form.allergies.filter(a => a !== item)
                      : [...form.allergies, item]
                    setForm({...form, allergies: updated})
                  }}
                  className={`px-3 py-1.5 rounded-full text-xs cursor-pointer border
                    ${form.allergies.includes(item) ? 'bg-blue-500 text-white border-blue-500' : 'text-gray-400 border-gray-200'}`}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 버튼 */}
        <div className="flex gap-3 p-6 border-t border-gray-100">
          <button onClick={onClose}
            className="flex-1 border border-gray-200 py-3 rounded-xl text-gray-400 text-sm cursor-pointer hover:bg-gray-50">
            건너뛰기
          </button>
          <button onClick={onClose}
            className="flex-1 bg-blue-500 text-white py-3 rounded-xl font-semibold text-sm cursor-pointer hover:bg-blue-600">
            완료
          </button>
        </div>
      </div>
    </div>
  )
}

// 챗봇 모달
function ChatModal({ onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요! 복약 관련 궁금한 것을 물어보세요 💊' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = () => {
    const message = input.trim()
    if (!message || isLoading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: message }])
    setIsLoading(true)
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: '지금은 테스트 중이에요. 곧 실제 AI와 연결될 거예요!' }])
      setIsLoading(false)
    }, 1500)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-2xl w-full max-w-lg h-[600px] flex flex-col">
        <div className="flex justify-between items-center p-4 border-b border-gray-100">
          <div>
            <h2 className="font-bold">복약 AI 상담</h2>
            <p className="text-xs text-gray-400">약 복용 방법, 부작용 등 무엇이든 물어보세요</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-black cursor-pointer text-xl">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs px-4 py-3 rounded-2xl text-sm
                ${msg.role === 'user' ? 'bg-blue-500 text-white rounded-br-sm' : 'bg-gray-100 text-gray-800 rounded-bl-sm'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 px-4 py-3 rounded-2xl">
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
          <button className="w-9 h-9 bg-gray-100 rounded-full text-gray-400 text-xl cursor-pointer hover:bg-gray-200 flex items-center justify-center shrink-0">
            +
          </button>
          <input type="text" value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyUp={(e) => { if (e.key === 'Enter') handleSend() }}
            placeholder="메시지를 입력하세요"
            className="flex-1 border border-gray-200 rounded-xl px-4 py-2 text-sm outline-none" />
          <button onClick={handleSend}
            className="bg-blue-500 text-white px-4 py-2 rounded-xl text-sm cursor-pointer hover:bg-blue-600">
            전송
          </button>
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

  useEffect(() => {
    setTimeout(() => {
      setIsLoading(false)
      setShowSurvey(true) // 로그인 후 자동으로 설문 팝업
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

      <main className="min-h-screen bg-gray-50 pb-20">
        <div className="bg-white border-b border-gray-200 px-10 py-5">
          <p className="text-gray-400 text-sm mb-1">{greeting.sub}</p>
          <h1 className="text-xl font-bold">{greeting.msg} 홍길동님</h1>
        </div>
        <div className="px-10 py-6 grid grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl shadow-sm p-6 col-span-2 row-span-2">
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-gray-100">
              <h2 className="font-bold">오늘 복약 현황</h2>
              <span className="text-blue-500 text-sm font-semibold">2/3 완료</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2 mb-6">
              <div className="bg-blue-500 h-2 rounded-full" style={{width: '66%'}} />
            </div>
            <div className="space-y-3">
              {todayMeds.map((med, i) => (
                <div key={i} className="flex items-center justify-between py-3 border-b border-gray-50">
                  <div className="flex items-center gap-4">
                    <span className="text-gray-400 text-sm w-12">{med.time}</span>
                    <span onClick={() => router.push('/medication')}
                      className={`text-sm font-semibold cursor-pointer hover:text-blue-500 ${med.done ? 'text-gray-400 line-through' : 'text-black'}`}>
                      💊 {med.name}
                    </span>
                  </div>
                  <span className={`text-xs px-3 py-1 rounded-full ${med.done ? 'bg-green-50 text-green-500' : 'bg-blue-50 text-blue-500'}`}>
                    {med.done ? '완료' : '예정'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 챗봇 버튼 → 모달로 */}
          <div onClick={() => setShowChat(true)}
            className="bg-blue-500 rounded-2xl p-6 text-white cursor-pointer hover:bg-blue-600">
            <p className="text-xs mb-2 opacity-80">궁금한 게 있으신가요?</p>
            <h2 className="font-bold">💊 복약 AI 상담하기</h2>
            <p className="text-xs mt-3 opacity-60">약 복용 방법, 부작용 등</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-6">
            <h2 className="font-bold mb-2">처방전 등록</h2>
            <button onClick={() => router.push('/ocr')}
              className="w-full border-2 border-dashed border-gray-200 py-3 rounded-xl text-gray-400 text-sm cursor-pointer hover:border-blue-300 mt-2">
              + 업로드
            </button>
          </div>

          <div onClick={() => router.push('/challenge')}
            className="bg-white rounded-2xl shadow-sm p-6 cursor-pointer hover:shadow-md">
            <h2 className="font-bold mb-3">챌린지 현황</h2>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">🏆</span>
              <span className="font-semibold text-sm">{challenge.title}</span>
            </div>
            <p className="text-gray-400 text-xs mb-2">{challenge.days}일째 진행 중!</p>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div className="bg-yellow-400 h-1.5 rounded-full" style={{width: `${(challenge.days/challenge.target)*100}%`}} />
            </div>
            <p className="text-xs text-gray-400 mt-1">{challenge.days}/{challenge.target}일</p>
          </div>

          <div className="bg-white rounded-2xl shadow-sm p-6">
            <h2 className="font-bold mb-3">최근 처방전</h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold">{recentPrescription.hospital}</p>
                <p className="text-xs text-gray-400 mt-1">{recentPrescription.date}</p>
              </div>
              <span className="text-xs text-blue-500 cursor-pointer">보기</span>
            </div>
          </div>
        </div>

        <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
          <button onClick={() => router.push('/main')} className="flex-1 py-4 text-blue-500 text-sm font-semibold">홈</button>
          <button onClick={() => router.push('/mypage')} className="flex-1 py-4 text-gray-400 text-sm">마이페이지</button>
        </div>
      </main>
    </>
  )
}