'use client'
import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Sunrise, Sun, Sunset, Moon, Clock, CheckCircle2, Circle } from 'lucide-react'
import api from '@/lib/api'

// ── 시간대 블록 정의 ─────────────────────────────────────────────────────────
// 흐름: intake_times 문자열 배열 → 시간 파싱 → 4개 블록 분류 → UI 렌더링
const TIME_BLOCKS = [
  { key: 'morning',   label: '아침', Icon: Sunrise, startH: 0,  endH: 10 },
  { key: 'afternoon', label: '점심', Icon: Sun,     startH: 10, endH: 14 },
  { key: 'evening',   label: '저녁', Icon: Sunset,  startH: 14, endH: 20 },
  { key: 'bedtime',   label: '취침', Icon: Moon,    startH: 20, endH: 24 },
]

function getBlockKey(timeStr) {
  const hour = parseInt(timeStr.split(':')[0], 10)
  if (hour < 10) return 'morning'
  if (hour < 14) return 'afternoon'
  if (hour < 20) return 'evening'
  return 'bedtime'
}

function getCurrentBlockKey() {
  const hour = new Date().getHours()
  if (hour < 10) return 'morning'
  if (hour < 14) return 'afternoon'
  if (hour < 20) return 'evening'
  return 'bedtime'
}

// intake_times가 있는 약품 → 시간대별 분류
// intake_times가 빈 배열인 약품 → unset 목록으로 분리
function classifyMedications(medications) {
  const blocks = { morning: [], afternoon: [], evening: [], bedtime: [] }
  const unset = []

  for (const med of medications) {
    if (!med.intake_times || med.intake_times.length === 0) {
      unset.push(med)
      continue
    }
    for (const t of med.intake_times) {
      const key = getBlockKey(t)
      blocks[key].push({ med, time: t })
    }
  }
  return { blocks, unset }
}

// ── 오늘의 복약 스케줄 ────────────────────────────────────────────────────────
// 흐름: activeMedications → 시간대 분류 → 오늘 복약 기록 fetch
//       → 블록별 체크리스트 표시 → 체크 시 POST intake-log + take
export default function TodaySchedule({ medications, profileId }) {
  const router = useRouter()
  const [todayLogs, setTodayLogs] = useState([])
  const [takingKeys, setTakingKeys] = useState(new Set())
  const currentBlock = getCurrentBlockKey()

  const fetchTodayLogs = useCallback(async () => {
    if (!profileId) return
    try {
      const today = new Date().toISOString().split('T')[0]
      const res = await api.get('/api/v1/intake-logs', {
        params: { profile_id: profileId, target_date: today },
      })
      setTodayLogs(res.data || [])
    } catch {
      // silent — 홈 화면 보조 기능이므로 에러 노출 없음
    }
  }, [profileId])

  useEffect(() => { fetchTodayLogs() }, [fetchTodayLogs])

  // medication_id + 시간 HH:MM prefix 기준으로 TAKEN 여부 확인
  const isTaken = useCallback(
    (medId, time) =>
      todayLogs.some(
        (l) =>
          l.medication_id === medId &&
          l.intake_status === 'TAKEN' &&
          l.scheduled_time?.startsWith(time.substring(0, 5)),
      ),
    [todayLogs],
  )

  // ── 체크오프 처리 ─────────────────────────────────────────────────────────
  // 흐름: POST intake-log 생성 (scheduled_time 포함) → POST take → 오늘 기록 재조회
  const handleCheck = useCallback(
    async (med, time) => {
      const key = `${med.id}__${time}`
      if (takingKeys.has(key) || isTaken(med.id, time)) return

      setTakingKeys((prev) => new Set([...prev, key]))
      try {
        const today = new Date().toISOString().split('T')[0]
        // "HH:MM" → "HH:MM:SS" 변환 (서버 time 타입 호환)
        const scheduledTime = time.split(':').length === 2 ? `${time}:00` : time
        const logRes = await api.post('/api/v1/intake-logs', {
          medication_id: med.id,
          profile_id: profileId,
          scheduled_date: today,
          scheduled_time: scheduledTime,
        })
        await api.post(`/api/v1/intake-logs/${logRes.data.id}/take`)
        await fetchTodayLogs()
      } catch {
        // silent
      } finally {
        setTakingKeys((prev) => {
          const s = new Set(prev)
          s.delete(key)
          return s
        })
      }
    },
    [takingKeys, isTaken, profileId, fetchTodayLogs],
  )

  const { blocks, unset } = classifyMedications(medications)

  // 전체 진행도 (시간대 배정된 항목 기준)
  const totalItems = Object.values(blocks).reduce((acc, items) => acc + items.length, 0)
  const takenItems = Object.values(blocks).reduce(
    (acc, items) =>
      acc + items.filter(({ med, time }) => isTaken(med.id, time)).length,
    0,
  )

  if (medications.length === 0) return null

  return (
    <section className="bg-white rounded-[32px] p-8 border border-gray-100 mb-6">
      {/* 헤더 + 완료 카운터 */}
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gray-100 rounded-2xl flex items-center justify-center">
            <Clock size={20} className="text-gray-900" />
          </div>
          <h2 className="text-xl font-bold text-gray-900">오늘의 복약</h2>
        </div>
        {totalItems > 0 && (
          <span className="text-sm font-bold text-gray-400">
            {takenItems}/{totalItems} 완료
          </span>
        )}
      </div>

      {/* 진행도 바 */}
      {totalItems > 0 && (
        <div className="mt-4 mb-6">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gray-900 rounded-full transition-all duration-500"
              style={{ width: `${Math.round((takenItems / totalItems) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* 4개 시간대 블록 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {TIME_BLOCKS.map(({ key, label, Icon }) => {
          const items = blocks[key]
          const isActive = key === currentBlock

          return (
            <div
              key={key}
              className={`rounded-2xl p-4 border transition-all ${
                isActive
                  ? 'border-gray-900 bg-gray-50'
                  : 'border-gray-100 bg-white'
              }`}
            >
              {/* 블록 헤더 */}
              <div className="flex items-center gap-2 mb-3">
                <Icon
                  size={14}
                  className={isActive ? 'text-gray-900' : 'text-gray-400'}
                />
                <span
                  className={`text-xs font-bold ${
                    isActive ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {label}
                </span>
              </div>

              {/* 약품 목록 */}
              {items.length === 0 ? (
                <p className="text-xs text-gray-300 font-bold">-</p>
              ) : (
                <ul className="space-y-2.5">
                  {items.map(({ med, time }) => {
                    const taken = isTaken(med.id, time)
                    const loading = takingKeys.has(`${med.id}__${time}`)
                    return (
                      <li key={`${med.id}__${time}`} className="flex items-start gap-2">
                        <button
                          onClick={() => handleCheck(med, time)}
                          disabled={taken || loading}
                          aria-label={taken ? '복약 완료' : '복약 확인'}
                          className={`mt-0.5 shrink-0 transition-all cursor-pointer disabled:cursor-default ${
                            taken
                              ? 'text-gray-900'
                              : 'text-gray-300 hover:text-gray-600'
                          }`}
                        >
                          {taken ? (
                            <CheckCircle2 size={16} />
                          ) : (
                            <Circle size={16} />
                          )}
                        </button>
                        <div className="min-w-0">
                          <p
                            className={`text-xs font-bold leading-snug truncate transition-all ${
                              taken
                                ? 'text-gray-400 line-through'
                                : 'text-gray-900'
                            }`}
                          >
                            {med.medicine_name}
                          </p>
                          {(med.dose_per_intake || med.intake_instruction) && (
                            <p className="text-[10px] text-gray-400 mt-0.5">
                              {[
                                med.dose_per_intake && `1회 ${med.dose_per_intake}`,
                                med.intake_instruction,
                              ].filter(Boolean).join(' · ')}
                            </p>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          )
        })}
      </div>

      {/* 시간 미설정 약품 섹션 */}
      {unset.length > 0 && (
        <div className="mt-4 rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Clock size={13} className="text-gray-400" />
              <span className="text-xs font-bold text-gray-400">
                복약 시간 미설정
              </span>
            </div>
            <button
              onClick={() => router.push('/medication')}
              className="text-[10px] font-bold text-gray-400 hover:text-gray-700 transition-colors cursor-pointer"
            >
              설정하기 →
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {unset.map((med) => (
              <span
                key={med.id}
                className="text-xs text-gray-500 bg-white border border-gray-200 px-3 py-1.5 rounded-xl font-bold"
              >
                {med.medicine_name}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
