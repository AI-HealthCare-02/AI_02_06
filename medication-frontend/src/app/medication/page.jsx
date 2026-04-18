'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Pill, ChevronRight, Plus, Building2, Pencil, Trash2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

function MedicationListSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24 animate-pulse">
      <div className="h-14 bg-white border-b border-gray-100" />
      <div className="h-10 bg-white border-b border-gray-100" />
      <div className="max-w-5xl mx-auto flex">
        <div className="hidden md:block w-44 shrink-0 border-r border-gray-100 bg-white p-3 space-y-1.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-7 bg-gray-100 rounded-lg" />
          ))}
        </div>
        <div className="flex-1 px-6 py-5 space-y-4">
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

/** dispensed_date(없으면 start_date) + department 기준으로 처방전 그룹핑 */
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

/** allGroups에서 고유 처방 날짜 목록 추출 (내림차순 유지) */
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

function formatYear(dateStr) {
  if (!dateStr || dateStr === '날짜 미상') return ''
  return dateStr.split('-')[0] + '년'
}

function PrescriptionGroup({ group, onMedClick, onEditGroup, onDeleteGroup }) {
  const { deptKey, items } = group
  const startDates = items.map(m => m.start_date).filter(Boolean).sort()
  const endDates = items.map(m => m.end_date).filter(Boolean).sort()
  const rangeStart = startDates[0]
  const rangeEnd = endDates[endDates.length - 1]
  const hasActive = items.some(m => m.is_active)

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:border-gray-200 hover:shadow-sm transition-all">
      <div className="px-5 pt-4 pb-3.5 border-b border-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
              <Building2 size={12} className="text-gray-500" />
            </div>
            <span className="font-bold text-gray-900 text-sm">{deptKey}</span>
            <span className="text-xs text-gray-400">{items.length}종</span>
          </div>
          <div className="flex items-center gap-1.5">
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
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${hasActive ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
              {hasActive ? '복용중' : '완료'}
            </span>
          </div>
        </div>
        {rangeStart && (
          <p className="text-xs text-gray-400 mt-1.5 ml-8">
            {formatDate(rangeStart)}{rangeEnd ? ` ~ ${formatDate(rangeEnd)}` : ''}
          </p>
        )}
      </div>
      <div className="divide-y divide-gray-50">
        {items.map((med) => (
          <button
            key={med.id}
            onClick={() => onMedClick(med.id)}
            className="w-full flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors cursor-pointer text-left"
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
            <ChevronRight size={13} className="text-gray-300 shrink-0" />
          </button>
        ))}
      </div>
    </div>
  )
}

const TABS = [
  { label: '복용중', param: 'active_only=true' },
  { label: '완료', param: 'inactive_only=true' },
]

export default function MedicationListPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [medications, setMedications] = useState([])
  const [activeTab, setActiveTab] = useState('복용중')
  const [selectedDate, setSelectedDate] = useState(null)
  const [deleteTargetItems, setDeleteTargetItems] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const { selectedProfileId: profileId } = useProfile()
  const isInitialLoad = useRef(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchMedications = async (isInitial = false) => {
    if (isInitial || isInitialLoad.current) {
      setIsLoading(true)
    } else {
      setIsRefreshing(true)
    }
    try {
      const tab = TABS.find(t => t.label === activeTab)
      const res = await api.get(`/api/v1/medications?profile_id=${profileId}&${tab.param}`)
      setMedications(res.data || [])
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
      isInitialLoad.current = false
    }
  }

  useEffect(() => {
    if (!profileId) return
    isInitialLoad.current = true
    fetchMedications(true)
    setSelectedDate(null)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, profileId])

  const handleDeleteGroup = (items) => {
    setDeleteTargetItems(items)
  }

  const executeDelete = async () => {
    if (!deleteTargetItems || isDeleting) return
    setIsDeleting(true)
    try {
      await Promise.all(deleteTargetItems.map(med => api.delete(`/api/v1/medications/${med.id}`)))
      setDeleteTargetItems(null)
      await fetchMedications()
    } catch (err) {
      console.error(err)
      alert('삭제 중 오류가 발생했습니다. 다시 시도해주세요.')
    } finally {
      setIsDeleting(false)
    }
  }

  if (isLoading) return <MedicationListSkeleton />

  const allGroups = groupByPrescription(medications)
  const sidebarDates = extractUniqueDates(allGroups)
  const groups = selectedDate
    ? allGroups.filter(g => g.dateKey === selectedDate)
    : allGroups

  const emptyMessage = activeTab === '복용중'
    ? { title: '복용 중인 약이 없어요', sub: '처방전을 촬영해서 약을 등록해보세요' }
    : { title: '완료된 처방 내역이 없어요', sub: '복용이 끝난 처방전은 여기에 표시됩니다' }

  return (
    <main className={`min-h-screen bg-gray-50 pb-24 transition-opacity duration-200 ${isRefreshing ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
      <div className="max-w-5xl mx-auto">

        {/* 헤더 */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h1 className="font-bold text-gray-900 text-lg">내 처방 내역</h1>
          <button
            onClick={() => router.push('/ocr')}
            className="flex items-center gap-1 text-sm font-bold text-gray-900 cursor-pointer hover:opacity-70 transition-opacity"
          >
            <Plus size={16} />
            추가
          </button>
        </div>

      <div className={`flex ${sidebarDates.length > 0 ? '' : 'block'}`}>

        {/* 좌측 사이드바 (데스크톱) */}
        {sidebarDates.length > 0 && (
          <aside className="hidden md:flex flex-col w-44 shrink-0 bg-white border-r border-gray-100 sticky top-0 self-start max-h-screen overflow-y-auto">

            {/* 탭 (사이드바 상단) */}
            <div className="flex border-b border-gray-100">
              {TABS.map(({ label }) => (
                <button
                  key={label}
                  onClick={() => setActiveTab(label)}
                  className={`flex-1 py-2.5 text-xs font-bold transition-colors ${
                    activeTab === label
                      ? 'text-gray-900 border-b-2 border-gray-900 -mb-px'
                      : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* 날짜 네비게이션 */}
            <nav className="flex-1 py-2 overflow-y-auto">
              {/* 전체 보기 */}
              <button
                onClick={() => setSelectedDate(null)}
                className={`w-full flex items-center justify-between pl-4 pr-3 py-2 text-left transition-colors ${
                  selectedDate === null
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                <span className="text-xs font-bold">전체 보기</span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                  selectedDate === null ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-400'
                }`}>
                  {allGroups.length}
                </span>
              </button>

              {/* 연도별 그룹 + 날짜 목록 */}
              {(() => {
                let lastYear = null
                return sidebarDates.map((dateKey) => {
                  const year = formatYear(dateKey)
                  const showYearDivider = year !== lastYear
                  lastYear = year
                  const groupCount = allGroups.filter(g => g.dateKey === dateKey).length
                  const isSelected = selectedDate === dateKey

                  return (
                    <div key={dateKey}>
                      {showYearDivider && (
                        <p className="px-4 pt-3 pb-1 text-[10px] font-bold text-gray-300 uppercase tracking-wider">
                          {year}
                        </p>
                      )}
                      <button
                        onClick={() => setSelectedDate(dateKey)}
                        className={`w-full flex items-center justify-between pl-5 pr-3 py-2 text-left transition-colors border-l-2 ${
                          isSelected
                            ? 'border-gray-900 bg-gray-50 text-gray-900'
                            : 'border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                        }`}
                      >
                        <span className={`text-xs ${isSelected ? 'font-bold' : 'font-medium'}`}>
                          {formatDateNav(dateKey)}
                        </span>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0 ${
                          isSelected ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-400'
                        }`}>
                          {groupCount}
                        </span>
                      </button>
                    </div>
                  )
                })
              })()}
            </nav>
          </aside>
        )}

        <div className="flex-1 min-w-0">

          {/* 탭 (모바일 — 사이드바 없을 때 or 모바일 뷰) */}
          <div className={`bg-white border-b border-gray-100 px-6 flex gap-6 ${sidebarDates.length > 0 ? 'md:hidden' : ''}`}>
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

          {/* 모바일 날짜 필터 (가로 스크롤) */}
          {sidebarDates.length > 0 && (
            <div className="md:hidden bg-white border-b border-gray-100 px-4 py-2 overflow-x-auto flex gap-1.5">
              <button
                onClick={() => setSelectedDate(null)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition-colors ${
                  selectedDate === null
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-500'
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
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {formatDateNav(dateKey)}
                </button>
              ))}
            </div>
          )}

          {/* 처방 그룹 목록 */}
          <div className="px-6 py-5">
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
                    onClick={() => router.push('/ocr')}
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
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      </div>

      {/* 처방전 그룹 삭제 확인 모달 */}
      {deleteTargetItems && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 px-4 pb-6">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-4">
            <div className="text-center space-y-1">
              <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-3">
                <Trash2 size={20} className="text-red-500" />
              </div>
              <p className="font-bold text-gray-900">처방전을 삭제할까요?</p>
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
