'use client'
import { useRouter } from 'next/navigation'

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

        {/* 오른쪽 카드 미리보기 */}
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

      {/* 기능 소개 섹션 */}
      <div className="bg-gray-50 py-20">
        <div className="max-w-5xl mx-auto px-10">
          <h2 className="text-2xl font-bold text-center mb-12">이런 분들에게 추천해요</h2>
          <div className="grid grid-cols-3 gap-6">
            {[
              { icon: '👴', title: '어르신 복약 관리', desc: '복잡한 복약 일정을 쉽게 관리해요' },
              { icon: '👨‍👩‍👧', title: '가족 건강 케어', desc: '가족의 복약을 한 곳에서 관리해요' },
              { icon: '💊', title: '만성질환 관리', desc: '꾸준한 복약 습관을 만들어드려요' },
            ].map((item, i) => (
              <div key={i} className="bg-white rounded-2xl p-8 text-center shadow-sm">
                <p className="text-4xl mb-4">{item.icon}</p>
                <h3 className="font-bold mb-2">{item.title}</h3>
                <p className="text-gray-400 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 하단 CTA */}
      <div className="max-w-5xl mx-auto px-10 py-20 text-center">
        <h2 className="text-2xl font-bold mb-4">지금 바로 시작해보세요</h2>
        <p className="text-gray-400 mb-8">카카오 또는 네이버 계정으로 간편하게 시작할 수 있어요</p>
        <button
          onClick={() => router.push('/login')}
          className="bg-blue-500 text-white px-10 py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600">
          무료로 시작하기
        </button>
      </div>

    </main>
  )
}