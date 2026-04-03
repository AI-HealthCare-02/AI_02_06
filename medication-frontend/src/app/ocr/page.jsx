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
    <main className="max-w-lg mx-auto p-6 mt-10">

      {/* 헤더 */}
      <h1 className="text-2xl font-bold mb-2">처방전 등록</h1>
      <p className="text-gray-400 text-sm mb-8">
        처방전을 촬영하거나 업로드해주세요
      </p>

      {/* 업로드 영역 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <label className="block w-full border-2 border-dashed border-gray-200 rounded-xl p-10 text-center cursor-pointer hover:border-blue-300">
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
              <p className="text-4xl mb-3">📷</p>
              <p className="text-gray-400 text-sm">사진을 업로드하세요</p>
              <p className="text-gray-300 text-xs mt-1">JPG, PNG 파일 지원</p>
            </div>
          )}
        </label>
      </div>

      {/* 버튼 */}
      <div className="flex gap-3">
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

    </main>
  )
}