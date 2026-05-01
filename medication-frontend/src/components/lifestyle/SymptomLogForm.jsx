'use client'

// 일일 증상 트래킹 폼 — /lifestyle-guide 의 "증상 트래킹" 탭에서 mount.
//
// react-hook-form + zod (PR-B 표준 패턴):
//   - 실시간 onChange 검증 (note 길이 제한 등)
//   - 검증 실패 시 빨간 helper + submit 차단 + toast
//   - 성공 시 toast.success + form 리셋

import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import toast from 'react-hot-toast'

import api, { showError } from '@/lib/api'
import { dailyLogCreateSchema } from '@/schemas'
import FormError from '@/components/form/FormError'

const PRESET_SYMPTOMS = [
  '어지러움', '두통', '구역질', '복통', '설사', '변비',
  '피로감', '수면 장애', '식욕 부진', '발진', '심계항진',
]

export default function SymptomLogForm({ profileId, onSaved }) {
  const today = new Date().toISOString().split('T')[0]

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(dailyLogCreateSchema),
    mode: 'onChange',
    defaultValues: {
      log_date: today,
      symptoms: [],
      note: '',
    },
  })

  const onSubmit = async (values) => {
    if (!profileId) {
      showError('프로필을 먼저 선택해주세요.')
      return
    }
    try {
      await api.post('/api/v1/daily-logs', {
        profile_id: profileId,
        log_date: today,
        symptoms: values.symptoms || [],
        note: values.note || null,
      })
      toast.success('증상 기록이 저장되었습니다.')
      reset({ log_date: today, symptoms: [], note: '' })
      onSaved?.()
    } catch (err) {
      if (err.response?.status === 409) {
        showError('오늘 기록이 이미 있습니다.')
      } else {
        showError('저장에 실패했습니다.')
      }
    }
  }

  const onInvalid = (formErrors) => {
    const first = formErrors.note?.message || formErrors.symptoms?.message
    toast.error(first || '입력값을 다시 확인해주세요.')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="mt-4 space-y-4">
      <div>
        <p className="text-xs font-bold text-gray-500 mb-2">오늘의 증상 선택</p>
        <Controller
          control={control}
          name="symptoms"
          render={({ field }) => (
            <div className="flex flex-wrap gap-2">
              {PRESET_SYMPTOMS.map((s) => {
                const selected = (field.value || []).includes(s)
                return (
                  <button
                    key={s}
                    type="button"
                    onClick={() =>
                      field.onChange(
                        selected
                          ? (field.value || []).filter((v) => v !== s)
                          : [...(field.value || []), s],
                      )
                    }
                    className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${
                      selected
                        ? 'bg-orange-500 text-white border-orange-500'
                        : 'bg-white text-gray-500 border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          )}
        />
        <FormError name="symptoms" errors={errors} />
      </div>

      <div>
        <p className="text-xs font-bold text-gray-500 mb-1">메모 (선택)</p>
        <textarea
          {...register('note')}
          placeholder="오늘 몸 상태를 자유롭게 적어보세요"
          maxLength={512}
          rows={3}
          className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2 resize-none focus:outline-none focus:border-orange-300"
        />
        <FormError name="note" errors={errors} />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className={`w-full py-3 rounded-xl text-sm font-bold transition-colors ${
          isSubmitting
            ? 'bg-gray-100 text-gray-400 cursor-wait'
            : 'bg-orange-500 text-white hover:bg-orange-600 cursor-pointer'
        }`}
      >
        {isSubmitting ? '저장 중...' : '오늘 증상 기록하기'}
      </button>
    </form>
  )
}
