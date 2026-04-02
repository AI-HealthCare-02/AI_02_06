'use client'

export default function LoginPage() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-gray-50">

      <div className="bg-white p-10 rounded-2xl shadow-sm w-96 text-center">

        {/* 로고 */}
        <div className="text-5xl mb-4">💊</div>
        <h1 className="text-2xl font-bold mb-1">복약 안내</h1>
        <p className="text-gray-400 text-sm mb-8">내 약을 안전하게 관리하세요</p>

        {/* 카카오 버튼 */}
        <button className="w-full bg-yellow-400 py-3 rounded-xl font-semibold text-sm mb-3 cursor-pointer hover:bg-yellow-500 flex items-center justify-center gap-2">
          카카오로 로그인
        </button>

        {/* 구분선 */}
        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-gray-400 text-xs">또는</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>

        {/* 네이버 버튼 */}
        <button className="w-full bg-green-500 text-white py-3 rounded-xl font-semibold text-sm cursor-pointer hover:bg-green-600">
          네이버로 로그인
        </button>

        {/* 하단 약관 */}
        <p className="text-gray-300 text-xs mt-8">
          로그인 시 서비스 이용약관에 동의하게 됩니다
        </p>

      </div>

    </main>
  )
}