'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { useMedication } from '@/contexts/MedicationContext'

function EditSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-32 animate-pulse">
      <div className="max-w-2xl mx-auto">
        <div className="h-14 bg-white border-b border-gray-100" />
        <div className="px-6 py-8 space-y-4">
          <div className="h-16 bg-white rounded-2xl border border-gray-100" />
          {[1, 2].map((i) => (
            <div key={i} className="h-48 bg-white rounded-2xl border border-gray-100" />
          ))}
        </div>
      </div>
    </div>
  )
}

function MedicationEditContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  // URL 쿼리 ?ids=id1,id2,... 로 처방전 그룹 내 약품 ID 목록 전달받음
  // medication/page.jsx의 onEditGroup에서 ids=items.map(m=>m.id).join(',') 형태로 생성
  const ids = searchParams.get('ids')?.split(',').filter(Boolean) ?? []
  const { medications, updateMedication } = useMedication()

  const [isLoading, setIsLoading] = useState(true)
  const [meds, setMeds] = useState([])
  // prescriptionDate: 그룹 내 모든 약품에 공통 적용되는 처방일 (dispensed_date)
  const [prescriptionDate, setPrescriptionDate] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (ids.length === 0) {
      router.push('/medication')
      return
    }

    // MedicationContext 의 store 에서 ids 매칭 우선 (페이지 이동 시 즉시 반영)
    const cached = ids.map(id => medications.find(m => m.id === id)).filter(Boolean)
    if (cached.length === ids.length) {
      setMeds(cached)
      setPrescriptionDate(cached[0]?.dispensed_date || cached[0]?.start_date || '')
      setIsLoading(false)
      return
    }
    if (medications.length === 0) {
      // Context 의 첫 fetch 가 아직 진행 중일 수 있어 다음 effect 까지 대기
      return
    }
    // 일부 매칭 누락 (직접 URL 진입 등) → fallback 으로 bulk fetch
    const fetchMedications = async () => {
      try {
        const results = await Promise.all(ids.map(id => api.get(`/api/v1/medications/${id}`)))
        const fetched = results.map(r => r.data)
        setMeds(fetched)
        setPrescriptionDate(fetched[0]?.dispensed_date || fetched[0]?.start_date || '')
      } catch {
        alert('약품 정보를 불러올 수 없습니다.')
        router.push('/medication')
      } finally {
        setIsLoading(false)
      }
    }
    fetchMedications()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medications])

  const handleInputChange = (index, field, value) => {
    setMeds(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const handleDelete = (index) => {
    setMeds(prev => prev.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    if (isSubmitting) return
    if (meds.length === 0) {
      alert('저장할 약품이 없습니다.')
      return
    }

    setIsSubmitting(true)
    try {
      // Context 의 updateMedication 이 응답으로 store in-place 갱신 → list 자동 반영
      await Promise.all(
        meds.map(med =>
          updateMedication(med.id, {
            medicine_name: med.medicine_name,
            department: med.department || null,
            category: med.category || null,
            dose_per_intake: med.dose_per_intake || null,
            daily_intake_count: med.daily_intake_count || null,
            total_intake_days: med.total_intake_days || null,
            intake_instruction: med.intake_instruction || null,
            dispensed_date: prescriptionDate || null,
          })
        )
      )
      alert('수정이 완료되었습니다.')
      router.push('/medication')
    } catch {
      alert('저장 중 오류가 발생했습니다.')
      setIsSubmitting(false)
    }
  }

  if (isLoading) return <EditSkeleton />

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <div className="max-w-2xl mx-auto">
        {/* 헤더 */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
          <button onClick={() => router.back()} className="text-gray-400 hover:text-black cursor-pointer text-xl">←</button>
          <div>
            <h1 className="font-bold text-gray-900">처방전 수정</h1>
            <p className="text-xs text-gray-400">내용을 터치해서 수정할 수 있어요</p>
          </div>
        </div>

        <div className="px-6 py-6 space-y-4">
          {/* 안내 배너 */}
          <div className="bg-blue-50 rounded-2xl p-4 flex items-center gap-3">
            <span className="text-lg font-bold text-blue-400">!</span>
            <p className="text-blue-600 text-xs">등록된 약품 정보를 수정합니다. 처방일은 전체 약품에 공통 적용됩니다.</p>
          </div>

          {/* 처방일 */}
          <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-gray-900">처방일</p>
              <p className="text-xs text-gray-400 mt-0.5">처방전에 적힌 날짜를 확인해주세요</p>
            </div>
            <input
              type="date"
              value={prescriptionDate}
              onChange={(e) => setPrescriptionDate(e.target.value)}
              className="text-sm font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50"
            />
          </div>

          {/* 약품 카드 목록 */}
          <div className="space-y-4">
            {meds.map((med, i) => (
              <div
                key={med.id}
                className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200"
              >
                <div className="flex justify-between items-start mb-4 gap-4">
                  <input
                    type="text"
                    value={med.medicine_name || ''}
                    onChange={(e) => handleInputChange(i, 'medicine_name', e.target.value)}
                    className="font-bold text-lg text-gray-900 border-b-2 border-transparent hover:border-blue-200 focus:border-blue-500 focus:outline-none bg-transparent w-full transition-colors"
                    placeholder="약품명 입력"
                  />
                  <button onClick={() => handleDelete(i)} className="text-gray-300 hover:text-red-400 mt-1 cursor-pointer shrink-0">
                    <Trash2 size={20} />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">1회 복용량</p>
                    <input
                      type="text"
                      value={med.dose_per_intake || ''}
                      onChange={(e) => handleInputChange(i, 'dose_per_intake', e.target.value)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 1정"
                    />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">1일 복용 횟수</p>
                    <input
                      type="number"
                      value={med.daily_intake_count || ''}
                      onChange={(e) => handleInputChange(i, 'daily_intake_count', Number(e.target.value) || null)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 3"
                    />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">총 복용 일수</p>
                    <input
                      type="number"
                      value={med.total_intake_days || ''}
                      onChange={(e) => handleInputChange(i, 'total_intake_days', Number(e.target.value) || null)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 5"
                    />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">복용 방법</p>
                    <input
                      type="text"
                      value={med.intake_instruction || ''}
                      onChange={(e) => handleInputChange(i, 'intake_instruction', e.target.value)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 식후 30분"
                    />
                  </div>
                </div>

                {med.category && (
                  <div className="mt-3 bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">약품 분류</p>
                    <input
                      type="text"
                      value={med.category || ''}
                      onChange={(e) => handleInputChange(i, 'category', e.target.value)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 해열진통제"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* 하단 버튼 */}
          <div className="flex gap-3 pb-10">
            <button
              onClick={() => router.back()}
              className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
            <button
              onClick={handleSave}
              disabled={isSubmitting}
              className="flex-1 bg-gray-900 text-white py-4 rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:bg-gray-800 enabled:cursor-pointer"
            >
              {isSubmitting ? '저장 중...' : '수정 완료'}
            </button>
          </div>
        </div>
      </div>

      <BottomNav />
    </main>
  )
}

export default function MedicationEditPage() {
  return (
    <Suspense fallback={<EditSkeleton />}>
      <MedicationEditContent />
    </Suspense>
  )
}
