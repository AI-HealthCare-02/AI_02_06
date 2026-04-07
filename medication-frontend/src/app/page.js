'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

function SlideShow({ router }) {
  const [current, setCurrent] = useState(0)

  const slides = [
    { icon: '👴', title: '어르신 복약 관리', desc: '복잡한 복약 일정을 쉽게 관리해요', bg: 'bg-blue-50' },
    { icon: '👨‍👩‍👧', title: '가족 건강 케어', desc: '가족의 복약을 한 곳에서 관리해요', bg: 'bg-green-50' },
    { icon: '💊', title: '만성질환 관리', desc: '꾸준한 복약 습관을 만들어드려요', bg: 'bg-purple-50' },
    { icon: '🚀', title: '지금 바로 시작해보세요!', desc: '카카오 또는 네이버로 간편하게 시작해요', bg: 'bg-yellow-50', cta: true },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent(prev => (prev + 1) % slides.length)
    }, 1500)
    return () => clearInterval(timer)
  }, [])

  const slide = slides[current]

  return (
    <div className="text-center">
      <div className={`${slide.bg} rounded-2xl p-16 transition-all duration-500`}>
        <p className="text-6xl mb-6">{slide.icon}</p>
        <h3 className="text-2xl font-bold mb-3">{slide.title}</h3>
        <p className="text-gray-400 mb-6">{slide.desc}</p>
        {slide.cta && (
          <button
            onClick={() => router.push('/login')}
            className="bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold cursor-pointer hover:bg-blue-600 active:scale-[0.98] transition-transform duration-150">
            시작하기 →
          </button>
        )}
      </div>
      <div className="flex justify-center gap-2 mt-6">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`h-2 rounded-full cursor-pointer transition-all duration-300
              ${current === i ? 'bg-blue-500 w-6' : 'bg-gray-300 w-2'}`}
          />
        ))}
      </div>
    </div>
  )
}

export default function LandingPage() {
  const router = useRouter()

  return (
    <main className="min-h-screen bg-white">

      {/* 상단 네비게이션 */}
      <div className="flex justify-between items-center px-10 py-4 border-b border-gray-100">
        <h1 className="text-xl font-bold">💊 Downforce</h1>
        <button
          onClick={() => router.push('/login')}
          className="bg-blue-500 text-white px-6 py-2 rounded-xl text-sm font-semibold cursor-pointer hover:bg-blue-600">
          로그인
        </button>
      </div>

      {/* 히어로 섹션 */}
      <div className="max-w-5xl mx-auto px-10 py-20 flex items-center gap-16">
        <div className="flex-1">
          <p className="text-blue-500 text-sm font-semibold mb-4">AI 기반 복약 관리 서비스</p>
          <h2 className="text-4xl font-bold leading-tight mb-6">
            내 약을 더 안전하게<br />
            <span className="text-blue-500">AI가 도와드릴게요</span>
          </h2>
          <p className="text-gray-400 text-lg mb-10 leading-relaxed">
            처방전을 촬영하면 AI가 자동으로 분석해요.<br />
            복약 시간 알림부터 부작용 안내까지<br />
            건강한 복약 습관을 만들어드려요.
          </p>
          <div className="flex gap-4">
            <button
              onClick={() => router.push('/login')}
              className="bg-blue-500 text-white px-8 py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600">
              시작하기 →
            </button>
            <button className="border border-gray-200 px-8 py-4 rounded-xl text-gray-500 font-semibold cursor-pointer hover:bg-gray-50">
              더 알아보기
            </button>
          </div>
        </div>

        {/* 오른쪽 카드 */}
        <div className="flex-1 space-y-3">
          <div className="bg-blue-50 rounded-2xl p-6">
            <p className="text-2xl mb-2">📷</p>
            <h3 className="font-bold mb-1">처방전 자동 인식</h3>
            <p className="text-gray-400 text-sm">사진 한 장으로 약품 정보를 자동 등록</p>
          </div>
          <div className="bg-green-50 rounded-2xl p-6">
            <p className="text-2xl mb-2">💊</p>
            <h3 className="font-bold mb-1">복약 알림</h3>
            <p className="text-gray-400 text-sm">복약 시간을 놓치지 않도록 알려드려요</p>
          </div>
          <div className="bg-purple-50 rounded-2xl p-6">
            <p className="text-2xl mb-2">🤖</p>
            <h3 className="font-bold mb-1">AI 복약 상담</h3>
            <p className="text-gray-400 text-sm">약에 대한 궁금증을 AI에게 물어보세요</p>
          </div>
        </div>
      </div>

      {/* 슬라이드 섹션 */}
      <div className="bg-gray-50 py-20">
        <div className="max-w-3xl mx-auto px-10">
          <h2 className="text-2xl font-bold text-center mb-12">이런 분들에게 추천해요</h2>
          <SlideShow router={router} />
        </div>
      </div>

    </main>
  )
}