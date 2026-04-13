'use client'
import { useState, useEffect, useRef, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api, { showError } from '@/lib/api'
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

// 종합 설문 모달 (survey 페이지 내용 + 팝업 스타일)
function SurveyModal({ onClose, userName }) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [existingProfile, setExistingProfile] = useState(null)
  const [form, setForm] = useState({
    age: '', gender: '', height: '', weight: '',
    is_smoking: null, is_drinking: null,
    conditions: [], allergies: []
  })
  const [isSaving, setIsSaving] = useState(false)

  const btnSelected = 'bg-gray-900 text-white border-gray-900'
  const btnUnselected = 'bg-white text-gray-400 border-gray-100 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  const handleSave = async () => {
    if (!form.age || !form.gender) {
      showError('나이와 성별은 필수입니다.')
      return
    }
    setIsSaving(true)
    await onSave({
      age: parseInt(form.age) || null,
      gender: form.gender || null,
      height: parseInt(form.height) || null,
      weight: parseFloat(form.weight) || null,
      is_smoking: form.is_smoking,
      is_drinking: form.is_drinking,
      conditions: form.conditions.length > 0 ? form.conditions : null,
      allergies: form.allergies.length > 0 ? form.allergies : null,
    })
    setIsSaving(false)
  }

  // 기존 프로필 데이터 로드
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/api/v1/profiles/')
        const selfProfile = res.data?.find(p => p.relation_type === 'SELF')
        if (selfProfile) {
          setExistingProfile(selfProfile)
          if (selfProfile.health_survey) {
            const survey = selfProfile.health_survey
            setForm({
              age: survey.age?.toString() || '',
              gender: survey.gender || '',
              height: survey.height?.toString() || '',
              weight: survey.weight?.toString() || '',
              is_smoking: survey.is_smoking ?? null,
              is_drinking: survey.is_drinking ?? null,
              conditions: survey.conditions || [],
              allergies: survey.allergies || []
            })
          }
        }
      } catch (err) { console.error(err) }
    }
    fetchProfile()
  }, [])

  const handleSkip = async () => {
    if (!existingProfile) {
      setIsSubmitting(true)
      try {
        await api.post('/api/v1/profiles/', { relation_type: 'SELF', name: userName || '나', health_survey: null })
      } catch (err) { console.error(err) }
      setIsSubmitting(false)
    }
    onClose()
  }

  const handleSubmit = async () => {
    if (!form.age || !form.gender) {
      showError('나이와 성별은 필수 입력입니다.')
      return
    }
    setIsSubmitting(true)
    const healthSurvey = {
      age: parseInt(form.age) || null,
      gender: form.gender || null,
      height: parseInt(form.height) || null,
      weight: parseInt(form.weight) || null,
      is_smoking: form.is_smoking,
      is_drinking: form.is_drinking,
      conditions: form.conditions.length > 0 ? form.conditions : null,
      allergies: form.allergies.length > 0 ? form.allergies : null
    }
    try {
      if (existingProfile) {
        await api.patch(`/api/v1/profiles/${existingProfile.id}`, { health_survey: healthSurvey })
      } else {
        await api.post('/api/v1/profiles/', { relation_type: 'SELF', name: userName || '나', health_survey: healthSurvey })
      }
      onClose()
    } catch (err) {
      console.error(err)
      showError(err.parsed?.message || '설문 저장에 실패했습니다.')
    }
    setIsSubmitting(false)
  }

  const selectedClass = 'bg-gray-900 text-white border-gray-900'
  const unselectedClass = 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <div className="bg-white rounded-[32px] w-full max-w-lg max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">
        {/* 헤더 */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center shrink-0">
          <div>
            <h2 className="font-black text-xl text-gray-900">건강 정보 입력</h2>
            <p className="text-gray-400 text-sm mt-1">{userName} 님에게 딱 맞는 복약 가이드를 준비할게요</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X size={24} className="text-gray-400" />
          </button>
        </div>

        {/* 스크롤 영역 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 기본 정보 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              기본 정보 <span className="text-red-400 text-xs">*필수</span>
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">나이 *</label>
                <input type="number" placeholder="세" value={form.age}
                  onChange={(e) => setForm({...form, age: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">성별 *</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map(g => (
                    <button key={g} type="button" onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.gender === g ? selectedClass : unselectedClass}`}>
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">키 (cm)</label>
                <input type="number" placeholder="cm" value={form.height}
                  onChange={(e) => setForm({...form, height: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">몸무게 (kg)</label>
                <input type="number" placeholder="kg" value={form.weight}
                  onChange={(e) => setForm({...form, weight: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
            </div>
          </div>

          {/* 생활 습관 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              생활 습관
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">흡연 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} type="button" onClick={() => setForm({...form, is_smoking: v})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.is_smoking === v ? selectedClass : unselectedClass}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">음주 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} type="button" onClick={() => setForm({...form, is_drinking: v})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.is_drinking === v ? selectedClass : unselectedClass}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 질환 및 알레르기 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              질환 및 알레르기
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-2 block">기저질환 (중복 선택)</label>
                <div className="flex flex-wrap gap-2">
                  {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map(item => (
                    <button key={item} type="button"
                      onClick={() => {
                        let updated
                        if (item === '없음') {
                          updated = form.conditions.includes(item) ? [] : ['없음']
                        } else {
                          const withoutNone = form.conditions.filter(c => c !== '없음')
                          updated = withoutNone.includes(item) ? withoutNone.filter(c => c !== item) : [...withoutNone, item]
                        }
                        setForm({...form, conditions: updated})
                      }}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${form.conditions.includes(item) ? chipSelected : chipUnselected}`}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-2 block">알레르기 (중복 선택)</label>
                <div className="flex flex-wrap gap-2">
                  {['페니실린', '아스피린', '항생제', '소염제', '없음'].map(item => (
                    <button key={item} type="button"
                      onClick={() => {
                        let updated
                        if (item === '없음') {
                          updated = form.allergies.includes(item) ? [] : ['없음']
                        } else {
                          const withoutNone = form.allergies.filter(a => a !== '없음')
                          updated = withoutNone.includes(item) ? withoutNone.filter(a => a !== item) : [...withoutNone, item]
                        }
                        setForm({...form, allergies: updated})
                      }}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${form.allergies.includes(item) ? chipSelected : chipUnselected}`}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 하단 버튼 */}
        <div className="p-6 pt-4 border-t border-gray-100 flex gap-3 shrink-0">
          <button onClick={handleSkip} disabled={isSubmitting}
            className="flex-1 py-4 rounded-2xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition-all disabled:opacity-50">
            건너뛰기
          </button>
          <button onClick={handleSubmit} disabled={isSubmitting}
            className="flex-1 py-4 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all shadow-lg disabled:opacity-50">
            {isSubmitting ? '저장 중...' : '저장하기'}
          </button>
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

function MainPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [userName, setUserName] = useState('사용자')
  const [selfProfileId, setSelfProfileId] = useState(null)
  const [greeting, setGreeting] = useState({ msg: '반가워요', sub: '오늘 하루도 건강하게 시작해봐요' })

  // 설문 팝업 쿼리 파라미터 감지
  useEffect(() => {
    if (searchParams.get('showSurvey') === 'true') {
      setShowSurvey(true)
      // URL 클린업
      router.replace('/main', { scroll: false })
    }
  }, [searchParams, router])

  useEffect(() => {
    const initPage = async () => {
      try {
        setIsLoading(true)
        const profileRes = await api.get('/api/v1/profiles/')
        const profiles = profileRes.data || []
        const self = profiles.find(p => p.relation_type === 'SELF')

        if (self) {
          setUserName(self.name.split('(')[0])
          setSelfProfileId(self.id)
          if (!self.health_survey) setShowSurvey(true)
        } else {
          setShowSurvey(true)
        }

        const hour = new Date().getHours()
        if (hour < 12) setGreeting({ msg: '좋은 아침이에요', sub: '오늘 하루도 건강하게 시작해봐요' })
        else if (hour < 17) setGreeting({ msg: '좋은 오후예요', sub: '점심 식사 후 약 챙기셨나요?' })
        else setGreeting({ msg: '좋은 저녁이에요', sub: '저녁 복약 시간을 확인해보세요' })
      } catch (err) { console.error(err) } finally { setIsLoading(false) }
    }
    initPage()
  }, [])

  const handleSurveySave = async (healthSurvey) => {
    try {
      if (selfProfileId) {
        await api.patch(`/api/v1/profiles/${selfProfileId}`, { health_survey: healthSurvey })
      } else {
        await api.post('/api/v1/profiles/', {
          relation_type: 'SELF',
          name: userName || '나',
          health_survey: healthSurvey,
        })
      }
      setShowSurvey(false)
    } catch (err) {
      showError('건강 정보 저장에 실패했습니다.')
    }
  }

  if (isLoading) return <MainSkeleton />

  return (
    <>
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} userName={userName} />}
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

// Suspense로 감싸서 export (useSearchParams 필수)
export default function MainPage() {
  return (
    <Suspense fallback={<MainSkeleton />}>
      <MainPageContent />
    </Suspense>
  )
}