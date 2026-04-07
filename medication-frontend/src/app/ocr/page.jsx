'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Info, Camera } from 'lucide-react'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'

export default function OcrPage() {
  const router = useRouter()
  const [preview, setPreview] = useState(null)

  const handleCancel = () => {
    if (window.confirm('작성 중인 내용이 사라집니다. 정말 나가시겠습니까?')) {
      router.push('/main')
    }
  }

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      const url = URL.createObjectURL(file)
      setPreview(url)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-32">
      <Header 
        title="처방전 등록" 
        subtitle="사진을 찍어 약을 등록하세요" 
        showBack={true} 
        onBack={handleCancel}
      />

      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* 설명 카드 */}
        <div className="bg-blue-50 rounded-2xl p-6 mb-8 border border-blue-100">
          <h2 className="font-bold text-blue-900 text-sm mb-4 flex items-center gap-2">
            <Info size={14} className="text-blue-900" />
            처방전 등록 방법
          </h2>
          <div className="space-y-4">
            <div className="flex gap-3">
              <span className="bg-blue-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">1</span>
              <p className="text-sm text-blue-800 opacity-80">처방전 사진을 업로드하세요</p>
            </div>
            <div className="flex gap-3">
              <span className="bg-blue-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">2</span>
              <p className="text-sm text-blue-800 opacity-80">AI가 약품 정보를 자동으로 인식해요</p>
            </div>
            <div className="flex gap-3">
              <span className="bg-blue-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">3</span>
              <p className="text-sm text-blue-800 opacity-80">인식된 정보를 확인하고 저장하세요</p>
            </div>
          </div>
        </div>

        {/* 업로드 영역 */}
        <div className="bg-white rounded-3xl shadow-sm p-4 border border-gray-100">
          <label className="block w-full border-2 border-dashed border-gray-200 rounded-2xl py-20 text-center cursor-pointer hover:border-blue-300 hover:bg-blue-50/30 transition-all">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            {preview ? (
              <div className="px-4">
                <img src={preview} alt="미리보기" className="w-full rounded-xl shadow-md" />
                <p className="text-blue-500 text-xs font-bold mt-4">클릭하여 사진 교체</p>
              </div>
            ) : (
              <div className="animate-in fade-in zoom-in duration-300">
                <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Camera size={28} className="text-gray-400" />
                </div>
                <p className="text-gray-900 font-bold mb-1">처방전 사진 찍기</p>
                <p className="text-gray-400 text-xs">JPG, PNG 파일 지원</p>
              </div>
            )}
          </label>
        </div>

        {/* 버튼 - 하단 영역 */}
        <div className="mt-8 flex gap-3">
          <button
            onClick={handleCancel}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-all active:scale-[0.98] duration-150"
          >
            취소
          </button>
          <button
            onClick={() => router.push('/ocr/loading')}
            disabled={!preview}
            className={`flex-1 py-4 rounded-xl text-sm font-bold shadow-sm transition-all active:scale-[0.98] duration-150
              ${preview 
                ? 'bg-blue-500 text-white hover:bg-blue-600 active:scale-95' 
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
          >
            분석 시작하기
          </button>
        </div>
      </div>

      <BottomNav />
    </main>
  )
}
