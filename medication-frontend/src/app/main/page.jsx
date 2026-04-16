'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import api, { showError } from '@/lib/api'
import { Pill, Flame, X, Plus, MessageCircle } from 'lucide-react'
import ChatModal from '@/components/ChatModal'

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

  // 기존 프로필 데이터 로드
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/api/v1/profiles')
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
        await api.post('/api/v1/profiles', { relation_type: 'SELF', name: userName || '나', health_survey: null })
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
      weight: parseFloat(form.weight) || null,
      is_smoking: form.is_smoking,
      is_drinking: form.is_drinking,
      conditions: form.conditions.length > 0 ? form.conditions : null,
      allergies: form.allergies.length > 0 ? form.allergies : null
    }
    try {
      if (existingProfile) {
        await api.patch(`/api/v1/profiles/${existingProfile.id}`, { health_survey: healthSurvey })
      } else {
        await api.post('/api/v1/profiles', { relation_type: 'SELF', name: userName || '나', health_survey: healthSurvey })
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
                <input type="number" placeholder="세" min={1} max={120}
                  value={form.age}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 1 && parseInt(val) <= 120)) setForm({...form, age: val})
                  }}
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
                <input type="number" placeholder="cm" min={50} max={250}
                  value={form.height}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 50 && parseInt(val) <= 250)) setForm({...form, height: val})
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">몸무게 (kg)</label>
                <input type="number" placeholder="kg" min={1} max={300} step={0.1}
                  value={form.weight}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseFloat(val) >= 1 && parseFloat(val) <= 300)) setForm({...form, weight: val})
                  }}
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

function MainPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [userName, setUserName] = useState('사용자')
  const [profileId, setProfileId] = useState(null)
  const [medications, setMedications] = useState([])
  const [activeChallenge, setActiveChallenge] = useState(null)
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
        const profileRes = await api.get('/api/v1/profiles')
        if (profileRes.data?.length > 0) {
          const self = profileRes.data.find(p => p.relation_type === 'SELF') || profileRes.data[0]
          setUserName(self.name.split('(')[0])
          setProfileId(self.id)

          const [medRes, challengeRes] = await Promise.all([
            api.get(`/api/v1/medications?profile_id=${self.id}&active_only=true`),
            api.get('/api/v1/challenges').catch(() => ({ data: [] })),
          ])
          setMedications(medRes.data || [])
          const inProgress = (challengeRes.data || []).filter(c => c.challenge_status === 'IN_PROGRESS')
          if (inProgress.length > 0) {
            const random = inProgress[Math.floor(Math.random() * inProgress.length)]
            setActiveChallenge(random)
          }
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
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} userName={userName} />}
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={profileId} />}

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
                <h2 className="text-xl font-bold text-gray-900">복용 중인 약</h2>
              </div>
              <button onClick={() => router.push('/medication')} className="text-sm font-bold text-gray-400 hover:text-gray-900 transition-colors cursor-pointer">
                전체보기 →
              </button>
            </div>
            {medications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
                  <Pill size={28} className="text-gray-300" />
                </div>
                <p className="text-gray-400 font-bold mb-1">등록된 약이 없어요</p>
                <p className="text-gray-300 text-sm mb-6">처방전을 촬영해서 약을 등록해보세요</p>
                <button onClick={() => router.push('/ocr')} className="px-6 py-3 bg-gray-900 text-white text-sm font-bold rounded-full cursor-pointer hover:bg-gray-800 transition-colors">
                  처방전 등록하기
                </button>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {medications.slice(0, 6).map((med) => (
                  <div
                    key={med.id}
                    onClick={() => router.push(`/medication/${med.id}`)}
                    className="p-5 rounded-2xl border border-gray-100 bg-white shadow-sm hover:border-gray-300 hover:shadow-md transition-all cursor-pointer"
                  >
                    <div className="flex justify-between items-start mb-3">
                      {med.category && (
                        <span className="text-[10px] font-bold text-blue-500 bg-blue-50 px-2 py-1 rounded-full">{med.category}</span>
                      )}
                      <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center ml-auto">
                        <Plus size={12} className="text-gray-400" />
                      </div>
                    </div>
                    <h3 className="font-bold text-gray-900 text-sm mb-2 leading-snug">{med.medicine_name}</h3>
                    <p className="text-xs text-gray-400">
                      {[med.dose_per_intake, med.intake_instruction].filter(Boolean).join(' · ') || '복용 정보 없음'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 사이드바 */}
          <div className="md:col-span-4 space-y-6">
            <div onClick={() => router.push('/challenge')} className="bg-gray-900 rounded-[32px] p-8 text-white cursor-pointer hover:-translate-y-1 transition-all min-h-[220px] flex flex-col justify-end relative overflow-hidden group">
              <Flame size={120} className="absolute -right-4 -top-4 opacity-[0.05] group-hover:scale-110 transition-transform" />
              <p className="text-gray-500 font-bold text-xs mb-2 tracking-widest">CHALLENGE</p>
              {activeChallenge ? (
                <>
                  <h2 className="text-2xl font-black mb-3">{activeChallenge.title}</h2>
                  <p className="text-orange-500 text-sm font-bold">
                    {activeChallenge.completed_dates?.length || 0}일째 성공 중! →
                  </p>
                </>
              ) : (
                <>
                  <h2 className="text-2xl font-black mb-3">챌린지 시작하기</h2>
                  <p className="text-gray-400 text-sm font-bold">건강한 습관을 만들어보세요 →</p>
                </>
              )}
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