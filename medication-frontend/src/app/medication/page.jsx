'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Pill, ChevronRight, Plus, Building2, Pencil, Trash2, CheckCircle2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import { useProfile } from '@/contexts/ProfileContext'
import { useMedication } from '@/contexts/MedicationContext'
import { useOcrEntryNavigator } from '@/contexts/OcrDraftContext'

function MedicationListSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24 animate-pulse">
      <div className="h-14 bg-white border-b border-gray-100" />
      <div className="h-10 bg-white border-b border-gray-100" />
      <div className="max-w-4xl mx-auto flex">
        <div className="hidden md:block w-36 shrink-0 border-r border-gray-100 bg-white p-3 space-y-1.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-7 bg-gray-100 rounded-lg" />
          ))}
        </div>
        <div className="flex-1 px-8 py-5 space-y-4">
          {[1, 2].map((i) => (
            <div key={i}>
              <div className="h-3 w-24 bg-gray-200 rounded mb-2" />
              <div className="h-32 bg-white rounded-2xl border border-gray-100" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function groupByPrescription(medications) {
  const groups = {}
  for (const med of medications) {
    const dateKey = med.dispensed_date || med.start_date || '날짜 미상'
    const deptKey = med.department || '기타'
    const key = `${dateKey}__${deptKey}`
    if (!groups[key]) {
      groups[key] = { dateKey, deptKey, items: [] }
    }
    groups[key].items.push(med)
  }
  return Object.values(groups).sort((a, b) => (a.dateKey < b.dateKey ? 1 : -1))
}

function extractUniqueDates(allGroups) {
  const seen = new Set()
  const result = []
  for (const g of allGroups) {
    if (!seen.has(g.dateKey)) {
      seen.add(g.dateKey)
      result.push(g.dateKey)
    }
  }
  return result
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === '날짜 미상') return '날짜 미상'
  const [year, month, day] = dateStr.split('-')
  return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`
}

function formatDateNav(dateStr) {
  if (!dateStr || dateStr === '날짜 미상') return '날짜 미상'
  const [, month, day] = dateStr.split('-')
  return `${parseInt(month)}월 ${parseInt(day)}일`
}


// start_date와 total_intake_days로 복약 진행도 계산 (마이그레이션 불필요)
function getProgressInfo(items) {
  const rep = items.find(m => m.is_active && m.start_date && m.total_intake_days) || null
  if (!rep) return null

  const today = new Date()
  const startDate = new Date(rep.start_date)
  const daysPassed = Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) + 1
  const currentDay = Math.min(Math.max(daysPassed, 1), rep.total_intake_days)
  const progress = Math.round((currentDay / rep.total_intake_days) * 100)

  return { currentDay, totalDays: rep.total_intake_days, progress }
}

function PrescriptionGroup({ group, onMedClick, onEditGroup, onDeleteGroup, onDeleteMed, completedMedIds, onCompleteToday, isCompleting }) {
  const { deptKey, items } = group
  const startDates = items.map(m => m.start_date).filter(Boolean).sort()
  const endDates = items.map(m => m.end_date).filter(Boolean).sort()
  const rangeStart = startDates[0]
  const rangeEnd = endDates[endDates.length - 1]
  const hasActive = items.some(m => m.is_active)
  // 처방전 복약 진행도 (start_date 기준으로 계산)
  const progressInfo = hasActive ? getProgressInfo(items) : null

  // 활성 약 중 오늘 이미 복약 완료된 항목 수 계산
  const activeMeds = items.filter(m => m.is_active)
  const isCompletedToday = activeMeds.length > 0 && activeMeds.every(m => completedMedIds.has(m.id))

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:border-gray-200 hover:shadow-sm transition-all">
      <div className="px-6 pt-4 pb-3.5 border-b border-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
              <Building2 size={12} className="text-gray-500" />
            </div>
            <span className="font-bold text-gray-900 text-sm">{deptKey}</span>
            <span className="text-xs text-gray-400">{items.length}종</span>
          </div>
          <div className="flex items-center gap-1.5">
            {/* 복용중 처방전에만 오늘 복약 완료 버튼 표시 */}
            {hasActive && (
              <button
                onClick={() => onCompleteToday(items)}
                disabled={isCompletedToday || isCompleting}
                className={`flex items-center gap-1 px-3 py-1 rounded-lg text-[11px] font-bold transition-colors cursor-pointer
                  ${isCompletedToday
                    ? 'bg-green-50 text-green-600 cursor-default'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed'}`}
              >
                <CheckCircle2 size={11} />
                {isCompletedToday ? '오늘 완료!' : isCompleting ? '처리 중...' : '오늘 복약 완료'}
              </button>
            )}
            <button
              onClick={() => onEditGroup(items)}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <Pencil size={10} />
              수정
            </button>
            <button
              onClick={() => onDeleteGroup(items)}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
            >
              <Trash2 size={10} />
              삭제
            </button>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gray-100 text-gray-700">
              {hasActive ? '복용중' : '완료'}
            </span>
          </div>
        </div>
        {rangeStart && (
          <p className="text-xs text-gray-400 mt-1.5 ml-8">
            {formatDate(rangeStart)}{rangeEnd ? ` ~ ${formatDate(rangeEnd)}` : ''}
          </p>
        )}
        {/* 복용 진행도 — start_date 기준으로 N일차 / M일 계산 */}
        {progressInfo && (
          <div className="mt-2 ml-8">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-bold text-gray-500">
                {progressInfo.currentDay}일차 / {progressInfo.totalDays}일
              </span>
              <span className="text-[11px] font-bold text-gray-400">{progressInfo.progress}%</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gray-700 rounded-full transition-all duration-500"
                style={{ width: `${progressInfo.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>
      <div className="divide-y divide-gray-50">
        {items.map((med) => (
          <div key={med.id} className="w-full flex items-center px-5 py-3 hover:bg-gray-50 transition-colors group">
            <div
              className="flex-1 flex items-center gap-3 cursor-pointer min-w-0"
              onClick={() => onMedClick(med.id)}
            >
              <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${med.is_active ? 'bg-green-400' : 'bg-gray-300'}`} />
              <div className="flex-1 min-w-0">
                <span className={`text-sm font-bold truncate block ${med.is_active ? 'text-gray-900' : 'text-gray-400'}`}>
                  {med.medicine_name}
                </span>
                {med.dose_per_intake && (
                  <span className="text-xs text-gray-400">{med.dose_per_intake}</span>
                )}
              </div>
              {med.category && (
                <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full shrink-0">
                  {med.category}
                </span>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteMed([med]);
              }}
              className="ml-3 p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0"
              aria-label="삭제"
            >
              <Trash2 size={16} />
            </button>
            <ChevronRight size={13} className="text-gray-300 shrink-0 ml-1" />
          </div>
        ))}
      </div>
    </div>
  )
}

const TABS = [
  { label: '복용중' },
  { label: '완료' },
]

export default function MedicationListPage() {
  const router = useRouter()
  const goToOcrEntry = useOcrEntryNavigator()
  const [activeTab, setActiveTab] = useState('복용중')
  const [selectedDate, setSelectedDate] = useState(null)
  const [deleteTargetItems, setDeleteTargetItems] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)
  // 오늘 복약 기록 상태 (medication_id → TAKEN 여부 확인용)
  const [todayLogs, setTodayLogs] = useState([])
  const [isCompleting, setIsCompleting] = useState(false)

  // MedicationContext 가 단일 진실 — 자체 fetch 제거, 탭 전환 시 client-side filter
  const { activeMedications, completedMedications, isLoading, deleteMedications } = useMedication()
  const medications = activeTab === '복용중' ? activeMedications : completedMedications

  // 오늘 복약 기록은 별도 endpoint (intake-logs) — Context 외부 fetch
  const fetchTodayLogs = async () => {
    if (!profileId) return
    try {
      const today = new Date().toISOString().split('T')[0]
      const res = await api.get(`/api/v1/intake-logs?profile_id=${profileId}&target_date=${today}`)
      setTodayLogs(res.data || [])
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    if (!profileId) return
    fetchTodayLogs()
    setSelectedDate(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, profileId])

  // 처방전 그룹 전체 오늘 복약 완료 처리
  const handleCompleteToday = async (items) => {
    if (isCompleting) return
    setIsCompleting(true)
    try {
      const today = new Date().toISOString().split('T')[0]
      const nowTime = new Date().toTimeString().split(' ')[0] // HH:MM:SS 형식

      // 오늘 이미 TAKEN 상태인 medication_id 집합
      const takenMedIds = new Set(
        todayLogs.filter(l => l.intake_status === 'TAKEN').map(l => l.medication_id)
      )

      // 활성 약 중 아직 완료되지 않은 것만 처리
      const pending = items.filter(m => m.is_active && !takenMedIds.has(m.id))

      for (const med of pending) {
        // 복약 기록 생성 후 즉시 완료 처리
        const logRes = await api.post('/api/v1/intake-logs', {
          medication_id: med.id,
          profile_id: profileId,
          scheduled_date: today,
          scheduled_time: nowTime,
        })
        await api.post(`/api/v1/intake-logs/${logRes.data.id}/take`)
      }

      // 오늘 복약 기록 갱신
      await fetchTodayLogs()
    } catch (err) {
      console.error(err)
      alert('복약 완료 처리 중 오류가 발생했습니다.')
    } finally {
      setIsCompleting(false)
    }
  }

  const handleDeleteGroup = (items) => {
    setDeleteTargetItems(items)
  }

  const executeDelete = async () => {
    if (!deleteTargetItems || isDeleting) return
    setIsDeleting(true)
    try {
      // Context 의 deleteMedications 가 응답 받자마자 setMedications 자동 갱신
      await deleteMedications(deleteTargetItems.map(m => m.id))
      setDeleteTargetItems(null)
    } catch (err) {
      console.error(err)
      alert('삭제 중 오류가 발생했습니다. 다시 시도해주세요.')
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading || !profileId) return <MedicationListSkeleton />

  // 오늘 TAKEN 상태인 medication_id 집합 (PrescriptionGroup 완료 여부 판단용)
  const completedMedIds = new Set(
    todayLogs.filter(l => l.intake_status === 'TAKEN').map(l => l.medication_id)
  )

  const allGroups = groupByPrescription(medications)
  const sidebarDates = extractUniqueDates(allGroups)
  const groups = selectedDate
    ? allGroups.filter(g => g.dateKey === selectedDate)
    : allGroups

  const emptyMessage = activeTab === '복용중'
    ? { title: '복용 중인 약이 없어요', sub: '처방전을 촬영해서 약을 등록해보세요' }
    : { title: '완료된 처방 내역이 없어요', sub: '복용이 끝난 처방전은 여기에 표시됩니다' }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <div className="max-w-5xl mx-auto">

      {/* 헤더 — 전체 너비 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="font-bold text-gray-900 text-lg">복약 가이드</h1>
        <div className="flex items-center gap-2">
          {/* 생활습관 가이드 작은 버튼 (챌린지 시작하기 스타일) */}
          <button
            onClick={() => router.push('/lifestyle-guide')}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-gray-50 text-gray-600 hover:bg-gray-100 cursor-pointer transition-colors"
          >
            생활습관 가이드 →
          </button>
          <button
            onClick={goToOcrEntry}
            className="flex items-center gap-1 text-sm font-bold text-gray-900 cursor-pointer hover:opacity-70 transition-opacity"
          >
            <Plus size={16} />
            추가
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto">

        {/* 탭 — 전체 너비 */}
        <div className="bg-white border-b border-gray-100 px-6 flex gap-6">
          {TABS.map(({ label }) => (
            <button
              key={label}
              onClick={() => setActiveTab(label)}
              className={`py-3 text-sm font-bold cursor-pointer transition-colors border-b-2 ${
                activeTab === label ? 'text-gray-900 border-gray-900' : 'text-gray-400 border-transparent'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* 날짜 필터 — 사이드바 대신 상단 가로 스크롤 */}
        {sidebarDates.length > 0 && (
          <div className="bg-white border-b border-gray-100 px-4 py-2 overflow-x-auto flex gap-1.5">
            <button
              onClick={() => setSelectedDate(null)}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${
                selectedDate === null
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              전체
            </button>
            {sidebarDates.map((dateKey) => (
              <button
                key={dateKey}
                onClick={() => setSelectedDate(dateKey)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${
                  selectedDate === dateKey
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {formatDateNav(dateKey)}
              </button>
            ))}
          </div>
        )}

        {/* 메인 콘텐츠 — 전체 너비 */}
        <div className="px-8 py-5">

          {selectedDate && (
                <p className="text-xs font-bold text-gray-400 mb-4">
                  {formatDate(selectedDate)} 처방
                </p>
              )}

              {groups.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="w-14 h-14 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
                    <Pill size={24} className="text-gray-300" />
                  </div>
                  <p className="text-gray-400 font-bold mb-1">
                    {selectedDate ? `해당 날짜의 처방 내역이 없어요` : emptyMessage.title}
                  </p>
                  <p className="text-gray-300 text-sm mb-6">
                    {selectedDate ? '다른 날짜를 선택해보세요' : emptyMessage.sub}
                  </p>
                  {activeTab === '복용중' && !selectedDate && (
                    <button
                      onClick={goToOcrEntry}
                      className="px-6 py-3 bg-gray-900 text-white text-sm font-bold rounded-full cursor-pointer hover:bg-gray-800 transition-colors"
                    >
                      처방전 등록하기
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-5">
                  {groups.map((group) => (
                    <div key={`${group.dateKey}__${group.deptKey}`}>
                      {!selectedDate && (
                        <p className="text-xs font-bold text-gray-400 mb-2 px-0.5">
                          {formatDate(group.dateKey)} 처방
                        </p>
                      )}
                      <PrescriptionGroup
                        group={group}
                        onMedClick={(id) => router.push(`/medication/${id}`)}
                        onEditGroup={(items) => router.push(`/medication/edit?ids=${items.map(m => m.id).join(',')}`)}
                        onDeleteGroup={handleDeleteGroup}
                        onDeleteMed={handleDeleteGroup}
                        completedMedIds={completedMedIds}
                        onCompleteToday={handleCompleteToday}
                        isCompleting={isCompleting}
                      />
                    </div>
                  ))}
                </div>
              )}
        </div>
      </div>

      {/* 삭제 확인 모달 */}
      {deleteTargetItems && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 px-4 pb-6">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-4">
            <div className="text-center space-y-1">
              <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-3">
                <Trash2 size={20} className="text-red-500" />
              </div>
              <p className="font-bold text-gray-900">
                {deleteTargetItems.length === 1 ? '약품을 삭제할까요?' : '처방전을 삭제할까요?'}
              </p>
              <p className="text-sm text-gray-400 leading-relaxed">
                아래 {deleteTargetItems.length}개 약품의 복용 기록이<br />영구적으로 삭제됩니다.
              </p>
              <div className="mt-2 space-y-1">
                {deleteTargetItems.map((med) => (
                  <p key={med.id} className="text-xs font-bold text-gray-600">{med.medicine_name}</p>
                ))}
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setDeleteTargetItems(null)}
                disabled={isDeleting}
                className="flex-1 py-3 rounded-xl text-sm font-bold text-gray-500 bg-gray-100 cursor-pointer hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                취소
              </button>
              <button
                onClick={executeDelete}
                disabled={isDeleting}
                className="flex-1 py-3 rounded-xl text-sm font-bold text-white bg-red-500 cursor-pointer hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                {isDeleting ? '삭제 중...' : '삭제'}
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </main>
  )
}
