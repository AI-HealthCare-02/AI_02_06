'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function OcrPage() {
  const router = useRouter()
  const [preview, setPreview] = useState(null)

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const url = URL.createObjectURL(file)
      setPreview(url)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">

      {/* 상단 헤더 */}
      <div className="bg-white border-b border-gray-200 px-10 py-4">
        <h1 className="text-lg font-bold">처방전 등록</h1>
      </div>

      <div className="max-w-5xl mx-auto px-10 py-10 flex gap-10">

        {/* 왼쪽 설명 */}
        <div className="w-64 shrink-0">
          <h2 className="font-bold text-sm mb-4">처방전 등록 방법</h2>
          <div className="space-y-4 text-sm text-gray-400">
            <div className="flex gap-3">
              <span className="text-blue-500 font-bold">1</span>
              <p>처방전 사진을 업로드하세요</p>
            </div>
            <div className="flex gap-3">
              <span className="text-blue-500 font-bold">2</span>
              <p>AI가 약품 정보를 자동으로 인식해요</p>
            </div>
            <div className="flex gap-3">
              <span className="text-blue-500 font-bold">3</span>
              <p>인식된 정보를 확인하고 저장하세요</p>
            </div>
          </div>

          <div className="mt-8 p-4 bg-blue-50 rounded-xl">
            <p className="text-xs text-blue-500 font-semibold mb-1">💡 팁</p>
            <p className="text-xs text-gray-400">처방전 전체가 잘 보이도록 밝은 곳에서 촬영해주세요</p>
          </div>
        </div>

        {/* 오른쪽 업로드 */}
        <div className="flex-1">
          <div className="bg-white rounded-2xl shadow-sm p-8">
            <label className="block w-full border-2 border-dashed border-gray-200 rounded-xl p-28 text-center cursor-pointer hover:border-blue-300">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              {preview ? (
                <img src={preview} alt="미리보기" className="w-full rounded-xl" />
              ) : (
                <div>
                  <p className="text-5xl mb-4">📷</p>
                  <p className="text-gray-500 font-semibold mb-1">사진을 업로드하세요</p>
                  <p className="text-gray-300 text-sm">JPG, PNG 파일 지원</p>
                  <p className="text-gray-300 text-xs mt-1">또는 클릭해서 파일 선택</p>
                </div>
              )}
            </label>
          </div>

          {/* 버튼 - 하단 고정 */}
            <div className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-100 flex gap-3 px-10 py-4">
            <button
              onClick={() => router.push('/main')}
              className="flex-1 border border-gray-200 py-4 rounded-xl text-gray-400 text-sm cursor-pointer hover:bg-gray-50"
            >
              취소
            </button>
            <button
              className="flex-1 bg-blue-500 text-white py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600"
            >
              분석하기
            </button>
          </div>
        </div>

      </div>
    </main>
  )
}