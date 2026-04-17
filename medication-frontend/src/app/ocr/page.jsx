'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Info, Camera } from 'lucide-react'
import Header from '@/components/layout/Header'

function OCRSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-32 animate-pulse">
      <div className="h-48 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="h-40 bg-gray-100 rounded-3xl mb-12 shadow-sm border border-gray-50" />
        <div className="h-[400px] bg-white rounded-[40px] border border-gray-100 shadow-sm" />
        <div className="mt-12 flex gap-4">
          <div className="flex-1 h-16 bg-gray-100 rounded-2xl" />
          <div className="flex-1 h-16 bg-gray-200 rounded-2xl" />
        </div>
      </div>
    </div>
  )
}

export default function OcrPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800)
  }, [])

  if (isLoading) return <OCRSkeleton />

  const handleCancel = () => {
    if (window.confirm('작성 중인 내용이 사라집니다. 정말 나가시겠습니까?')) {
      router.push('/main')
    }
  }

  const handleFileChange = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
      setPreview(URL.createObjectURL(selected))
    }
  }

  const handleAnalyze = () => {
    if (!file) return
    sessionStorage.setItem('ocrFileName', file.name)
    sessionStorage.setItem('ocrFileType', file.type)
    const reader = new FileReader()
    reader.onload = (e) => {
      sessionStorage.setItem('ocrFileData', e.target.result)
      router.push('/ocr/loading')
    }
    reader.readAsDataURL(file)
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

        {/* 안내 카드 */}
        <div className="bg-gray-50 rounded-2xl p-6 mb-8 border border-gray-200">
          <h2 className="font-bold text-gray-800 text-sm mb-4 flex items-center gap-2">
            <Info size={14} className="text-gray-600" />
            처방전 등록 방법
          </h2>
          <div className="space-y-4">
            {[
              '처방전 사진을 업로드하세요',
              'AI가 약품 정보를 자동으로 인식해요',
              '인식된 정보를 확인하고 저장하세요',
            ].map((text, i) => (
              <div key={i} className="flex gap-3">
                <span className="bg-gray-900 text-white w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0">
                  {i + 1}
                </span>
                <p className="text-sm text-gray-600">{text}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 업로드 영역 */}
        <div className="bg-white rounded-3xl shadow-sm p-4 border border-gray-100">
          <label className="block w-full border-2 border-dashed border-gray-200 rounded-2xl py-20 text-center cursor-pointer hover:border-gray-400 hover:bg-gray-50/50 transition-all">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
            />
            {preview ? (
              <div className="px-4">
                <img src={preview} alt="미리보기" className="w-full rounded-xl shadow-md" />
                <p className="text-gray-500 text-xs font-bold mt-4">클릭하여 사진 교체</p>
              </div>
            ) : (
              <div className="animate-in fade-in zoom-in duration-300">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Camera size={28} className="text-gray-400" />
                </div>
                <p className="text-gray-900 font-bold mb-1">처방전 사진 찍기</p>
                <p className="text-gray-400 text-xs">JPG, PNG 파일 지원</p>
              </div>
            )}
          </label>
        </div>

        {/* 하단 버튼 */}
        <div className="mt-8 flex gap-3">
          <button
            onClick={handleCancel}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-all active:scale-[0.98]"
          >
            취소
          </button>
          <button
            onClick={handleAnalyze}
            disabled={!preview}
            className={`flex-1 py-4 rounded-xl text-sm font-bold transition-all active:scale-[0.98] cursor-pointer
              ${preview
                ? 'bg-gray-900 text-white hover:bg-gray-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
          >
            분석 시작하기
          </button>
        </div>
      </div>
    </main>
  )
}
