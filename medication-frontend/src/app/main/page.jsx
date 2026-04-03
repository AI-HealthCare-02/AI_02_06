'use client'

import { useRouter } from 'next/navigation'
export default function MainPage() {
  const router = useRouter()

  return (
    <main className="min-h-screen bg-gray-50">

      {/* 상단 헤더 */}
      <div className="bg-white px-10 py-4 shadow-sm">
        <p className="text-gray-400 text-sm">안녕하세요 👋</p>
        <h1 className="text-xl font-bold">홍길동님</h1>
      </div>

      <div className="p-10 grid grid-cols-2 gap-4">

        {/* 오늘 복약 현황 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 col-span-2">
          <h2 className="font-bold mb-4">오늘 복약 현황</h2>
          <p className="text-gray-400 text-sm">아직 복약 기록이 없어요</p>
        </div>

        {/* 챗봇 버튼 */}
        <div className="bg-blue-500 rounded-2xl p-6 text-white cursor-pointer hover:bg-blue-600">
          <p className="text-sm mb-1">궁금한 게 있으신가요?</p>
          <h2 className="font-bold text-lg">💊 복약 AI 상담하기</h2>
        </div>

        {/* 처방전 업로드 */}
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="font-bold mb-2">처방전 등록</h2>
          <p className="text-gray-400 text-sm mb-4">처방전을 업로드하세요</p>
          <button
          onClick = {() => router.push('/ocr')}
          className="w-full border-2 border-dashed border-gray-200 py-4 rounded-xl text-gray-400 text-sm cursor-pointer hover:border-blue-300">
            + 업로드
          </button>
        </div>

      </div>

      {/* 하단 네비게이션 */}
      {/* 하단 네비게이션 */}
<div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
  <button
    onClick={() => router.push('/main')}
    className="flex-1 py-4 text-blue-500 text-sm font-semibold">
    홈
  </button>
  <button
    onClick={() => router.push('/mypage')}
    className="flex-1 py-4 text-gray-400 text-sm">
    마이페이지
  </button>
</div>

    </main>
  )
}