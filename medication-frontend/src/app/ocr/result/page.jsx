'use client'

// /ocr/result — OCR 결과 확인 + 수정 + 저장 (react-hook-form + zod 표준 적용).
//
// 흐름:
//   1) draft_id 로 SSE 연결 → ai-worker 의 status='ready' 까지 폴링
//   2) ready 도달 시 medicines 를 폼에 reset (useFieldArray)
//   3) 사용자 인라인 수정 — 실시간 zod 검증 + 빨간 helper
//   4) 저장 시 BE 의 confirm 또는 manual create 호출 (검증 통과만)

import { useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'

import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { streamSSE } from '@/lib/sseClient'
import { useProfile } from '@/contexts/ProfileContext'
import { useMedication } from '@/contexts/MedicationContext'
import { medicationEditPatchSchema } from '@/schemas'
import FormError from '@/components/form/FormError'

const TERMINAL_ERROR_MESSAGES = {
  no_text: '이미지에서 텍스트를 찾지 못했어요.',
  no_candidates: '약품 정보를 인식하지 못했어요.',
  failed: '처리 중 오류가 발생했어요.',
}

// 처방전 메타 + 약품 배열 통합 schema. medicationEditPatchSchema 재사용.
const ocrConfirmSchema = z.object({
  prescription_date: z.string().optional(),
  prescription_hospital: z.string().trim().max(128, '최대 128자까지 가능해요').optional(),
  prescription_department: z.string().trim().max(64, '최대 64자까지 가능해요').optional(),
  meds: z.array(medicationEditPatchSchema).min(1, '약품을 최소 1개 입력해주세요'),
})

async function* watchDraftStatus(draftId, profileId, signal) {
  const path = profileId
    ? `/api/v1/ocr/draft/${draftId}/stream?profile_id=${profileId}`
    : `/api/v1/ocr/draft/${draftId}/stream`
  while (true) {
    let timedOut = false
    for await (const ev of streamSSE(path, { signal })) {
      if (ev.event === 'update') yield ev.data
      else if (ev.event === 'timeout') {
        timedOut = true
        break
      } else if (ev.event === 'error') throw new Error(ev.data?.detail || 'sse error')
    }
    if (!timedOut) return
  }
}

function ResultSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-32 animate-pulse">
      <div className="h-48 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="flex justify-between items-center mb-8 px-1">
          <div className="h-6 w-32 bg-gray-200 rounded-lg" />
          <div className="h-6 w-20 bg-gray-200 rounded-lg" />
        </div>
        <div className="space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-48 bg-white rounded-3xl border border-gray-100 shadow-sm" />
          ))}
        </div>
        <div className="mt-12 flex gap-4">
          <div className="flex-1 h-16 bg-white border border-gray-200 rounded-2xl" />
          <div className="flex-1 h-16 bg-blue-100 rounded-2xl" />
        </div>
      </div>
    </div>
  )
}

const EMPTY_MED = {
  medicine_name: '',
  dose_per_intake: '',
  daily_intake_count: '',
  total_intake_days: '',
  intake_instruction: '',
  category: '',
}

function OcrResultContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const draftId = searchParams.get('draft_id')
  const { selectedProfileId } = useProfile()
  const { refetchMedications } = useMedication()

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(ocrConfirmSchema),
    mode: 'onChange',
    defaultValues: {
      prescription_date: new Date().toISOString().split('T')[0],
      prescription_hospital: '',
      prescription_department: '',
      meds: [],
    },
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'meds' })

  // 첫 fetch 가 끝났는지 — false 일 때만 ResultSkeleton.
  const initialized = fields.length > 0 || draftId === 'manual'

  useEffect(() => {
    if (!draftId) {
      router.push('/ocr')
      return
    }
    if (draftId === 'manual') {
      reset({
        prescription_date: new Date().toISOString().split('T')[0],
        prescription_hospital: '',
        prescription_department: '',
        meds: [{ ...EMPTY_MED }],
      })
      return
    }

    const abortController = new AbortController()
    const consumeStream = async () => {
      try {
        for await (const payload of watchDraftStatus(draftId, selectedProfileId, abortController.signal)) {
          const { status, medicines } = payload
          if (status === 'ready') {
            const firstDept = medicines?.find?.((m) => m?.department)?.department || ''
            reset({
              prescription_date:
                medicines?.[0]?.dispensed_date || new Date().toISOString().split('T')[0],
              prescription_hospital: '',
              prescription_department: firstDept,
              meds: (medicines || []).map((m) => ({
                medicine_name: m.medicine_name || '',
                dose_per_intake: m.dose_per_intake || '',
                daily_intake_count: m.daily_intake_count ?? '',
                total_intake_days: m.total_intake_days ?? '',
                intake_instruction: m.intake_instruction || '',
                category: m.category || '',
              })),
            })
            return
          }
          if (status in TERMINAL_ERROR_MESSAGES) {
            toast.error(`${TERMINAL_ERROR_MESSAGES[status]} 다시 촬영해주세요.`)
            router.push('/ocr')
            return
          }
        }
      } catch (err) {
        if (abortController.signal.aborted) return
        toast.error('데이터가 만료되었거나 불러올 수 없습니다. 다시 촬영해주세요.')
        router.push('/ocr')
      }
    }
    consumeStream()
    return () => abortController.abort()
  }, [draftId, router, selectedProfileId, reset])

  const handleRetake = async () => {
    if (draftId && draftId !== 'manual') {
      try {
        await api.delete(`/api/v1/ocr/draft/${draftId}`, {
          params: selectedProfileId ? { profile_id: selectedProfileId } : undefined,
        })
      } catch {
        // ignore
      }
    }
    router.push('/ocr')
  }

  const onInvalid = (formErrors) => {
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

  const onSubmit = async (values) => {
    if (draftId === 'manual' && !selectedProfileId) {
      toast.error('프로필을 선택한 후 다시 시도해주세요.')
      return
    }

    const toIntOrNull = (v) => {
      if (v === '' || v === null || v === undefined) return null
      const n = parseInt(v, 10)
      return Number.isNaN(n) ? null : n
    }
    const toStrOrNull = (v) => (v === '' || v === undefined ? null : v)
    const confirmedMedicines = values.meds.map((med) => ({
      ...med,
      medicine_name: med.medicine_name?.trim() ?? '',
      dose_per_intake: toStrOrNull(med.dose_per_intake),
      daily_intake_count: toIntOrNull(med.daily_intake_count),
      total_intake_days: toIntOrNull(med.total_intake_days),
      intake_instruction: toStrOrNull(med.intake_instruction),
      category: toStrOrNull(med.category),
      department: toStrOrNull(values.prescription_department),
      dispensed_date: values.prescription_date || null,
    }))

    try {
      if (draftId === 'manual') {
        let succeeded = 0
        for (const med of confirmedMedicines) {
          const dailyCount = parseInt(med.daily_intake_count, 10) || 1
          const days = parseInt(med.total_intake_days, 10) || 1
          const startDate = med.dispensed_date || new Date().toISOString().split('T')[0]

          let intakeTimes = []
          if (dailyCount === 1) intakeTimes = ['08:00']
          else if (dailyCount === 2) intakeTimes = ['08:00', '19:00']
          else if (dailyCount === 3) intakeTimes = ['08:00', '13:00', '19:00']
          else {
            const step = 14 / (dailyCount - 1)
            intakeTimes = Array.from({ length: dailyCount }, (_, i) => {
              const hour = Math.round(8 + i * step)
              return `${String(hour).padStart(2, '0')}:00`
            })
          }

          try {
            await api.post('/api/v1/medications', {
              ...med,
              profile_id: selectedProfileId,
              start_date: startDate,
              total_intake_count: dailyCount * days,
              intake_times: intakeTimes,
            })
            succeeded += 1
          } catch (err) {
            const remaining = confirmedMedicines.length - succeeded
            toast.error(
              `${succeeded}개 저장 후 실패했습니다. 남은 ${remaining}개는 저장되지 않았습니다.`,
            )
            throw err
          }
        }
      } else {
        await api.post(
          '/api/v1/ocr/confirm',
          {
            draft_id: draftId,
            confirmed_medicines: confirmedMedicines,
            hospital_name: values.prescription_hospital?.trim() || null,
            department: values.prescription_department?.trim() || null,
          },
          {
            timeout: 60000,
            params: selectedProfileId ? { profile_id: selectedProfileId } : undefined,
          },
        )
        sessionStorage.setItem('ocr_consumed_draft_id', draftId)
      }

      await refetchMedications()
      toast.success('저장 완료! 복약 목록에서 확인해보세요.')
      router.push('/medication')
    } catch {
      toast.error('저장 중 오류가 발생했습니다.')
    }
  }

  if (!initialized) return <ResultSkeleton />

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <form onSubmit={handleSubmit(onSubmit, onInvalid)}>
        <div className="bg-white border-b border-gray-200 px-10 py-4 flex items-center gap-4">
          <button
            type="button"
            onClick={() => router.push('/main')}
            className="text-gray-400 hover:text-black cursor-pointer text-xl"
            aria-label="메인으로 이동"
          >
            ←
          </button>
          <div>
            <h1 className="font-bold text-gray-900">처방전 확인 및 수정</h1>
            <p className="text-xs text-gray-400">오탈자가 있다면 직접 수정해주세요</p>
          </div>
        </div>

        <div className="max-w-3xl mx-auto px-10 py-8 space-y-4">
          <div className="bg-blue-50 rounded-2xl p-4 flex items-center gap-3">
            <span className="text-2xl">!</span>
            <div>
              <p className="font-semibold text-blue-800 text-sm">확인해주세요!</p>
              <p className="text-blue-600 text-xs">AI가 인식한 결과입니다. 틀린 글자는 터치해서 고칠 수 있어요.</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-gray-900">처방일</p>
              <p className="text-xs text-gray-400 mt-0.5">처방전에 적힌 날짜를 확인해주세요</p>
            </div>
            <input
              type="date"
              {...register('prescription_date')}
              className="text-base font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50"
            />
          </div>

          <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-gray-900">병원</p>
              <p className="text-xs text-gray-400 mt-0.5">비워두면 &lsquo;미상&rsquo; 으로 등록됩니다 (나중에 수정 가능)</p>
            </div>
            <div>
              <input
                type="text"
                {...register('prescription_hospital')}
                placeholder="예: 서울내과의원"
                maxLength={128}
                className="text-base font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50 w-56"
              />
              <FormError name="prescription_hospital" errors={errors} />
            </div>
          </div>

          <div className="bg-white rounded-2xl p-5 border border-gray-200 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-gray-900">진료과</p>
              <p className="text-xs text-gray-400 mt-0.5">비워두면 &lsquo;미상&rsquo; 으로 등록됩니다 (나중에 수정 가능)</p>
            </div>
            <div>
              <input
                type="text"
                {...register('prescription_department')}
                placeholder="예: 내과"
                maxLength={64}
                className="text-base font-bold text-gray-700 border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-100 bg-gray-50 w-40"
              />
              <FormError name="prescription_department" errors={errors} />
            </div>
          </div>

          <div className="space-y-4 mb-10">
            {fields.map((field, i) => (
              <div
                key={field.id}
                className="bg-white rounded-2xl p-6 shadow-sm border border-gray-200 animate-in fade-in slide-in-from-bottom-2 duration-300"
                style={{ animationDelay: `${i * 100}ms` }}
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
                    className="text-gray-300 hover:text-red-400 mt-1 cursor-pointer"
                  >
                    <Trash2 size={20} />
                  </button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <div className="bg-gray-50 p-2 rounded-xl border border-gray-100">
                    <p className="text-[10px] text-gray-500 mb-1 px-1">1회 복용량</p>
                    <input
                      type="text"
                      {...register(`meds.${i}.dose_per_intake`)}
                      className="text-sm font-bold text-gray-700 bg-transparent w-full focus:outline-none focus:text-blue-600 px-1"
                      placeholder="예: 1정"
                    />
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
                  </div>
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={() => append({ ...EMPTY_MED })}
              className="w-full bg-white rounded-2xl p-4 border-2 border-dashed border-blue-300 text-blue-500 font-bold hover:bg-blue-50 hover:border-blue-400 transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-sm"
            >
              <span className="text-xl">+</span> 직접 약품 추가하기
            </button>
          </div>

          <div className="flex gap-3 pb-10">
            <button
              type="button"
              onClick={handleRetake}
              className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold cursor-pointer hover:bg-gray-50 transition-colors"
            >
              다시 촬영
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 bg-gray-900 text-white py-4 rounded-xl font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed enabled:hover:bg-gray-800 enabled:cursor-pointer"
            >
              {isSubmitting ? '저장 중...' : '수정 완료 및 저장'}
            </button>
          </div>
        </div>
      </form>

      <BottomNav />
    </main>
  )
}

export default function OcrResultPage() {
  return (
    <Suspense fallback={<ResultSkeleton />}>
      <OcrResultContent />
    </Suspense>
  )
}
