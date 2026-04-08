'use client'
import { useRouter } from 'next/navigation'
import { Camera, Pill, MessageCircle, ArrowRight } from 'lucide-react'

const features = [
  {
    icon: <Camera size={20} />,
    title: '처방전 자동 인식',
    desc: '사진 한 장으로 약품 정보를 AI가 자동 등록해요. 복잡한 입력은 필요 없어요.',
  },
  {
    icon: <Pill size={20} />,
    title: '스마트 복약 알림',
    desc: '복약 시간을 절대 놓치지 않도록 맞춤 알림을 보내드려요.',
  },
  {
    icon: <MessageCircle size={20} />,
    title: 'AI 복약 상담',
    desc: '약에 대한 궁금증을 AI에게 언제든지 물어보세요. 24시간 답변 가능해요.',
  },
]

const useCases = [
  { label: '어르신 복약 관리', desc: '복잡한 복약 일정을 한눈에' },
  { label: '가족 건강 케어', desc: '가족의 복약을 한 곳에서' },
  { label: '만성질환 관리', desc: '꾸준한 복약 습관 형성' },
]

export default function LandingPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-white">

      {/* ── 히어로 섹션 ── full-width 다크 */}
      <section
        className="relative w-full min-h-[620px] flex items-center justify-center overflow-hidden"
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

        {/* 코너 마커 */}
        <div className="absolute top-0 left-[180px] w-px h-7 bg-white/20" />
        <div className="absolute top-0 left-[180px] h-px w-7 bg-white/20" />
        <div className="absolute top-0 right-[180px] w-px h-7 bg-white/20" />
        <div className="absolute top-0 right-[180px] h-px w-7 bg-white/20" />

        {/* 그라디언트 블랍 */}
        <div
          className="absolute bottom-0 left-1/2 pointer-events-none"
          style={{
            transform: 'translateX(-340px)',
            width: '580px',
            height: '400px',
            background: 'radial-gradient(ellipse at center bottom, rgba(249,115,22,0.36) 0%, rgba(239,68,68,0.2) 45%, transparent 70%)',
          }}
        />
        <div
          className="absolute bottom-0 left-1/2 pointer-events-none"
          style={{
            transform: 'translateX(-60px)',
            width: '580px',
            height: '400px',
            background: 'radial-gradient(ellipse at center bottom, rgba(20,184,166,0.36) 0%, rgba(59,130,246,0.2) 45%, transparent 70%)',
          }}
        />

        {/* 중앙 아이콘 */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 pointer-events-none select-none">
          <div
            style={{
              width: '140px',
              height: '140px',
              background: 'linear-gradient(160deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 100%)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '40px',
              transform: 'translateY(44px) rotate(12deg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Pill size={44} style={{ color: 'rgba(255,255,255,0.15)' }} />
          </div>
        </div>

        {/* 콘텐츠 */}
        <div className="relative z-10 text-center px-6 max-w-3xl mx-auto py-28">
          <p className="text-gray-500 text-xs font-medium mb-6 tracking-[0.2em] uppercase">
            AI 기반 복약 관리 서비스
          </p>
          <h1 className="text-5xl md:text-6xl lg:text-[72px] font-black text-white leading-[1.05] tracking-tight mb-6">
            내 약을 더<br />
            <span className="text-gray-400">안전하게</span>
          </h1>
          <p className="text-gray-500 text-base md:text-lg mb-10 leading-relaxed max-w-xl mx-auto">
            처방전을 촬영하면 AI가 자동으로 분석해요.<br />
            복약 시간 알림부터 부작용 안내까지 한 곳에서.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.push('/login')}
              className="px-7 py-3.5 bg-white text-black text-sm font-semibold rounded-full hover:bg-gray-100 transition-all shadow-lg cursor-pointer flex items-center justify-center gap-2"
            >
              지금 시작하기 <ArrowRight size={15} />
            </button>
            <button
              className="px-7 py-3.5 text-white text-sm font-semibold rounded-full transition-all cursor-pointer"
              style={{ border: '1px solid rgba(255,255,255,0.2)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.08)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              더 알아보기
            </button>
          </div>
        </div>
      </section>

      {/* ── 기능 소개 ── */}
      <section className="max-w-5xl mx-auto px-6 py-24">
        <p className="text-center text-[11px] font-semibold text-gray-400 tracking-[0.2em] uppercase mb-3">Features</p>
        <h2 className="text-3xl md:text-4xl font-black text-center text-gray-900 tracking-tight mb-16">
          건강한 복약 습관의<br />모든 것
        </h2>
        <div className="grid md:grid-cols-3 gap-5">
          {features.map((f, i) => (
            <div
              key={i}
              className="p-8 bg-gray-50 rounded-2xl border border-gray-100 hover:border-gray-200 hover:bg-white hover:shadow-sm transition-all"
            >
              <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center text-white mb-5">
                {f.icon}
              </div>
              <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 사용 사례 ── */}
      <section className="border-t border-gray-100 py-20">
        <div className="max-w-5xl mx-auto px-6">
          <p className="text-center text-[11px] font-semibold text-gray-400 tracking-[0.2em] uppercase mb-3">Who it's for</p>
          <h2 className="text-2xl md:text-3xl font-black text-center text-gray-900 mb-12">
            이런 분들께 추천해요
          </h2>
          <div className="grid md:grid-cols-3 gap-4">
            {useCases.map((u, i) => (
              <div key={i} className="flex items-center gap-4 p-6 rounded-2xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all bg-white">
                <div className="w-9 h-9 bg-gray-100 rounded-xl flex items-center justify-center text-sm font-black text-gray-500 shrink-0">
                  {i + 1}
                </div>
                <div>
                  <p className="font-bold text-gray-900 text-sm">{u.label}</p>
                  <p className="text-gray-400 text-xs mt-0.5">{u.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA 섹션 ── */}
      <section className="py-24 text-center" style={{ backgroundColor: '#0a0a0a' }}>
        <p className="text-gray-500 text-xs font-medium mb-5 tracking-[0.2em] uppercase">Get started</p>
        <h2 className="text-3xl md:text-4xl font-black text-white mb-4 tracking-tight">
          지금 바로 시작해보세요
        </h2>
        <p className="text-gray-500 text-base mb-10">카카오 또는 네이버로 3초 만에 시작해요</p>
        <button
          onClick={() => router.push('/login')}
          className="px-8 py-3.5 bg-white text-black font-semibold rounded-full hover:bg-gray-100 transition-all cursor-pointer text-sm shadow-lg"
        >
          무료로 시작하기
        </button>
      </section>

    </div>
  )
}
