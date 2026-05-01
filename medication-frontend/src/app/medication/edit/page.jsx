'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'

import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { useMedication } from '@/contexts/MedicationContext'
import { medicationEditPatchSchema } from '@/schemas'
import FormError from '@/components/form/FormError'

// 여러 medication 을 한 화면에서 검증하기 위해 array 로 wrap.
const editFormSchema = z.object({
  prescription_date: z.string().optional(),
  meds: z.array(medicationEditPatchSchema).min(1, '저장할 약품이 없어요'),
})

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
  const ids = searchParams.get('ids')?.split(',').filter(Boolean) ?? []
  const { medications, updateMedication } = useMedication()

  const [isLoading, setIsLoading] = useState(true)

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(editFormSchema),
    mode: 'onChange',
    defaultValues: {
      prescription_date: '',
      meds: [],
    },
  })
  const { fields, remove } = useFieldArray({ control, name: 'meds' })

  useEffect(() => {
    if (ids.length === 0) {
      router.push('/medication')
      return
    }

    const fillForm = (rows) => {
      reset({
        prescription_date: rows[0]?.dispensed_date || rows[0]?.start_date || '',
        meds: rows.map((m) => ({
          id: m.id,
          medicine_name: m.medicine_name || '',
          dose_per_intake: m.dose_per_intake || '',
          intake_instruction: m.intake_instruction || '',
          category: m.category || '',
          daily_intake_count: m.daily_intake_count ?? '',
          total_intake_days: m.total_intake_days ?? '',
        })),
      })
      setIsLoading(false)
    }

    const cached = ids.map((id) => medications.find((m) => m.id === id)).filter(Boolean)
    if (cached.length === ids.length) {
      fillForm(cached)
      return
    }
    if (medications.length === 0) return // 첫 fetch 대기.

    const fetchAll = async () => {
      try {
        const results = await Promise.all(ids.map((id) => api.get(`/api/v1/medications/${id}`)))
        fillForm(results.map((r) => r.data))
      } catch {
        toast.error('약품 정보를 불러올 수 없습니다.')
        router.push('/medication')
      }
    }
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medications])

  const onSubmit = async (values) => {
    if (values.meds.length === 0) {
      toast.error('저장할 약품이 없어요.')
      return
    }
    try {
      await Promise.all(
        values.meds.map((med) =>
          updateMedication(med.id, {
            medicine_name: med.medicine_name,
            category: med.category || null,
            dose_per_intake: med.dose_per_intake || null,
            daily_intake_count: med.daily_intake_count || null,
            total_intake_days: med.total_intake_days || null,
            intake_instruction: med.intake_instruction || null,
            dispensed_date: values.prescription_date || null,
          }),
        ),
      )
      toast.success('수정이 완료되었습니다.')
      router.push('/medication')
    } catch {
      toast.error('저장 중 오류가 발생했습니다.')
    }
  }

  const onInvalid = (formErrors) => {
    // 첫 에러 메시지만 toast — 어느 row 든 한 번에 1개 안내.
    const dig = (obj) => {
      if (!obj) return null
      if (typeof obj === 'object' && 'message' in obj && obj.message) return obj.message
      for (const v of Object.values(obj)) {
        const r = dig(v)
        if (r) return r
      }
      return null
    }
    toast.error(dig(formErrors) || '입력값을 다시 확인해주세요.')
  }

  if (isLoading) return <EditSkeleton />

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="max-w-2xl mx-auto">
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
          <button
            type="button"
            onClick={() => router.back()}
            className="text-gray-400 hover:text-black cursor-pointer text-xl"
          >
            ←
          </button>
          <div>
            <h1 className="font-bold text-gray-900">처방전 수정</h1>
            <p className="text-xs text-gray-400">내용을 터치해서 수정할 수 있어요</p>
          </div>
        </div>

        <div className="px-6 py-6 space-y-4">
          <div className="bg-blue-50 rounded-2xl p-4 flex items-center gap-3">
            <span className="text-lg font-bold text-blue-400">!</span>
            <p className="text-blue-600 text-xs">
              등록된 약품 정보를 수정합니다. 처방일은 전체 약품에 공통 적용됩니다.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-gray-900">처방일</p>
              <p className="text-xs text-gray-400 mt-0.5">처방전에 적힌 날짜를 확인해주세요</p>
            </div>
            <input
              type="date"
              {...register('prescription_date')}
              className="text-sm font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50"
            />
          </div>

          <div className="space-y-4">
            {fields.map((field, i) => (
              <div
                key={field.id}
                className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200"
              >
                <div className="flex justify-between items-start mb-4 gap-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      {...register(`meds.${i}.medicine_name`)}
                      className="font-bold text-lg text-gray-900 border-b-2 border-transparent hover:border-blue-200 focus:border-blue-500 focus:outline-none bg-transparent w-full transition-colors"
                      placeholder="약품명 입력"
                    />
                    <FormError name={`meds.${i}.medicine_name`} errors={errors} />
                  </div>
                  <button
                    type="button"
                    onClick={() => remove(i)}
                    className="text-gray-300 hover:text-red-400 mt-1 cursor-pointer shrink-0"
                  >
                    <Trash2 size={20} />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">1회 복용량</p>
                    <input
                      type="text"
                      {...register(`meds.${i}.dose_per_intake`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 1정"
                    />
                    <FormError name={`meds.${i}.dose_per_intake`} errors={errors} />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">1일 복용 횟수</p>
                    <input
                      type="number"
                      inputMode="numeric"
                      {...register(`meds.${i}.daily_intake_count`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 3"
                    />
                    <FormError name={`meds.${i}.daily_intake_count`} errors={errors} />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">총 복용 일수</p>
                    <input
                      type="number"
                      inputMode="numeric"
                      {...register(`meds.${i}.total_intake_days`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 5"
                    />
                    <FormError name={`meds.${i}.total_intake_days`} errors={errors} />
                  </div>
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">복용 방법</p>
                    <input
                      type="text"
                      {...register(`meds.${i}.intake_instruction`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 식후 30분"
                    />
                    <FormError name={`meds.${i}.intake_instruction`} errors={errors} />
                  </div>
                </div>

                {field.category && (
                  <div className="mt-3 bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">약품 분류</p>
                    <input
                      type="text"
                      {...register(`meds.${i}.category`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 해열진통제"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-3 pb-10">
            <button
              type="button"
              onClick={() => router.back()}
              className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 bg-gray-900 text-white py-4 rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:bg-gray-800 enabled:cursor-pointer"
            >
              {isSubmitting ? '저장 중...' : '수정 완료'}
            </button>
          </div>
        </div>
      </form>

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
