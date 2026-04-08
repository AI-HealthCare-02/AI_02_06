'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Pill, FileText, Flame, Ban, X, Check, Plus } from 'lucide-react'


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

function SurveyModal({ onClose }) {
  const [form, setForm] = useState({ gender: '' })

  return (
    <div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex justify-between items-center p-8 border-b border-gray-50 sticky top-0 bg-white z-10">
          <div>
            <h2 className="font-black text-2xl text-gray-900 leading-tight">건강 정보 입력</h2>
            <p className="text-gray-400 text-sm mt-1">맞춤 복약 가이드를 제공해 드릴게요</p>
          </div>
          <button onClick={onClose} className="text-gray-300 hover:text-black cursor-pointer p-2 transition-colors"><X size={20} /></button>
        </div>
        <div className="p-8 space-y-8">
          <div>
            <h3 className="font-bold mb-4 text-gray-800">기본 정보</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-gray-400 text-xs font-bold px-1 uppercase tracking-wider">나이</label>
                <input type="number" placeholder="만 나이"
                  className="w-full bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-all" />
              </div>
              <div className="space-y-2">
                <label className="text-gray-400 text-xs font-bold px-1 uppercase tracking-wider">성별</label>
                <div className="flex gap-2">
                  {['M', 'F'].map(g => (
                    <button key={g} onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-3 rounded-2xl text-xs font-black transition-all border cursor-pointer
                        ${form.gender === g ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-400 border-gray-100 hover:border-gray-200'}`}>
                      {g === 'M' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="pt-4 border-t border-gray-50 flex gap-4">
            <button onClick={onClose} className="flex-1 border border-gray-100 py-4 rounded-2xl text-gray-400 font-bold hover:bg-gray-50 transition-all cursor-pointer">다음에 할게요</button>
            <button onClick={onClose} className="flex-1 bg-gray-900 text-white py-4 rounded-2xl font-black hover:bg-gray-700 transition-all cursor-pointer">저장하기</button>
          </div>
        </div>
      </div>
    </div>

  )
}

export default function MainPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)

  useEffect(() => {
    setTimeout(() => {
      setIsLoading(false)
    }, 800)
  }, [])

  if (isLoading) return <MainSkeleton />

  const todayMeds = [
    { time: '08:00', name: '혈압약', done: true },
    { time: '13:00', name: '당뇨약', done: true },
    { time: '19:00', name: '비타민', done: false },
  ]
  const challenge = { title: '금연 챌린지', days: 3, target: 30 }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 12) return { msg: '좋은 아침이에요', sub: '오늘 하루도 건강하게 시작해봐요' }
    if (hour >= 12 && hour < 17) return { msg: '좋은 오후예요', sub: '점심 식사 후 약 챙기셨나요?' }
    if (hour >= 17 && hour < 21) return { msg: '좋은 저녁이에요', sub: '저녁 복약 시간을 확인해보세요' }
    return { msg: '잠들기 전 확인해요', sub: '오늘 복약을 모두 완료했나요?' }
  }
  const greeting = getGreeting()

  return (
    <>
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} />}

      {/* ── 히어로 섹션 ── Vercel 스타일, full-width 다크 */}
      <section
        className="relative w-full min-h-[540px] flex items-center justify-center overflow-hidden"
        style={{ backgroundColor: '#000' }}
      >
        {/* 그리드 패턴 */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(255,255,255,0.07) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(255,255,255,0.07) 1px, transparent 1px)
            `,
            backgroundSize: '72px 72px',
          }}
        />

        {/* 상단 코너 마커 (Vercel 스타일) */}
        <div className="absolute top-0 left-[200px] w-px h-8 bg-white/20" />
        <div className="absolute top-0 left-[200px] h-px w-8 bg-white/20" />
        <div className="absolute top-0 right-[200px] w-px h-8 bg-white/20" />
        <div className="absolute top-0 right-[200px] h-px w-8 bg-white/20" />

        {/* 컬러 그라디언트 블랍 (좌: 웜, 우: 쿨) */}
        <div
          className="absolute bottom-0 left-1/2 pointer-events-none"
          style={{
            transform: 'translateX(-320px)',
            width: '560px',
            height: '380px',
            background: 'radial-gradient(ellipse at center bottom, rgba(249,115,22,0.38) 0%, rgba(239,68,68,0.22) 45%, transparent 70%)',
          }}
        />
        <div
          className="absolute bottom-0 left-1/2 pointer-events-none"
          style={{
            transform: 'translateX(-60px)',
            width: '560px',
            height: '380px',
            background: 'radial-gradient(ellipse at center bottom, rgba(20,184,166,0.38) 0%, rgba(59,130,246,0.22) 45%, transparent 70%)',
          }}
        />

        {/* 중앙 아이콘 (Vercel 삼각형 대응) */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 pointer-events-none select-none">
          <div
            className="w-36 h-36 flex items-center justify-center"
            style={{
              background: 'linear-gradient(160deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.03) 100%)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '40px',
              transform: 'translateY(40px) rotate(12deg)',
            }}
          >
            <Pill size={40} className="text-white/20" />
          </div>
        </div>

        {/* 콘텐츠 */}
        <div className="relative z-10 text-center px-6 max-w-3xl mx-auto py-24">
          <p className="text-gray-500 text-xs font-medium mb-5 tracking-[0.2em] uppercase">
            {greeting.sub}
          </p>
          <h1 className="text-5xl md:text-6xl lg:text-[72px] font-black text-white leading-[1.05] tracking-tight mb-5">
            {greeting.msg},<br />
            <span className="text-gray-500">홍길동님</span>
          </h1>
          <p className="text-gray-500 text-base md:text-lg mb-10 leading-relaxed">
            오늘 복약 <span className="text-white font-semibold">2/3 완료</span>. 저녁 약 복용을 잊지 마세요.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.push('/ocr')}
              className="px-7 py-3 bg-white text-black text-sm font-semibold rounded-full hover:bg-gray-100 transition-all shadow-lg cursor-pointer"
            >
              처방전 등록하기
            </button>
            <button
              onClick={() => router.push('/medication')}
              className="px-7 py-3 text-white text-sm font-semibold rounded-full transition-all cursor-pointer"
              style={{ border: '1px solid rgba(255,255,255,0.2)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              복약 가이드 보기
            </button>
          </div>
        </div>
      </section>

      {/* ── 대시보드 ── */}
      <main className="max-w-7xl mx-auto w-full px-6 py-14">

        <div className="grid md:grid-cols-12 gap-6 items-start">

          {/* 복약 현황 */}
          <section className="md:col-span-8 bg-white rounded-[32px] p-8 border border-gray-100 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-100 rounded-2xl flex items-center justify-center">
                  <Pill size={20} className="text-gray-700" />
                </div>
                <h2 className="text-xl font-bold text-gray-900">오늘 복약 현황</h2>
              </div>
              <div className="flex flex-col items-end">
                <span className="text-sm font-bold text-gray-900">66%</span>
                <span className="text-xs text-gray-400">2/3 완료</span>
              </div>
            </div>

            {/* 프로그레스 바 */}
            <div className="w-full bg-gray-100 rounded-full h-1.5 mb-10">
              <div className="bg-gray-900 h-full rounded-full transition-all duration-1000" style={{ width: '66%' }} />
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {todayMeds.map((med, i) => (
                <div
                  key={i}
                  onClick={() => router.push('/medication')}
                  className={`group relative p-6 rounded-2xl transition-all border cursor-pointer active:scale-[0.98]
                    ${med.done
                      ? 'bg-gray-50 border-gray-100'
                      : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-md'}`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-xs font-medium text-gray-400">{med.time}</span>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center transition-all
                      ${med.done ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-400 group-hover:bg-gray-200'}`}>
                      {med.done ? <Check size={12} /> : <Plus size={12} />}
                    </div>
                  </div>
                  <h3 className={`text-base font-bold ${med.done ? 'text-gray-400 line-through' : 'text-gray-900'}`}>
                    {med.name}
                  </h3>
                </div>
              ))}
            </div>
          </section>

          {/* 사이드 섹션 */}
          <div className="md:col-span-4 space-y-6">

            {/* 처방전 등록 */}
            <div
              onClick={() => router.push('/ocr')}
              className="group bg-gray-900 rounded-[32px] p-8 text-white cursor-pointer hover:-translate-y-1 transition-all duration-200 relative overflow-hidden min-h-[220px] flex flex-col justify-end"
            >
              <div className="absolute -right-4 -top-4 opacity-[0.04] group-hover:rotate-6 transition-transform duration-300">
                <FileText size={120} className="text-white" />
              </div>
              <div>
                <p className="text-gray-500 font-medium text-xs mb-3 uppercase tracking-widest">Prescription</p>
                <h2 className="text-2xl font-black leading-snug mb-3">처방전<br />간편 등록</h2>
                <div className="flex items-center gap-1.5 text-sm text-gray-500 group-hover:text-white transition-colors">
                  카메라로 찍어보세요 <span>→</span>
                </div>
              </div>
            </div>

            {/* 챌린지 */}
            <div
              onClick={() => router.push('/challenge')}
              className="bg-white rounded-[32px] p-8 border border-gray-100 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-base font-bold text-gray-900">진행 중 챌린지</h2>
                <div className="w-9 h-9 bg-orange-50 rounded-xl flex items-center justify-center group-hover:animate-bounce">
                  <Flame size={16} className="text-orange-500" />
                </div>
              </div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-gray-50 rounded-2xl flex items-center justify-center">
                  <Ban size={20} className="text-gray-400" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-gray-900">{challenge.title}</h3>
                  <p className="text-xs text-orange-500 font-medium mt-0.5">{challenge.days}일째 성공 중!</p>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div className="bg-orange-500 h-full rounded-full transition-all duration-1000" style={{ width: '15%' }} />
              </div>
            </div>
          </div>

        </div>
      </main>
    </>
  )
}
