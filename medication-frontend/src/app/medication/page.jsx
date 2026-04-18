'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Pill, ChevronRight, Plus, Building2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

function MedicationListSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24 animate-pulse">
      <div className="h-16 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-4">
        {[1, 2].map((i) => (
          <div key={i} className="space-y-1">
            <div className="h-4 w-24 bg-gray-200 rounded mb-3" />
            <div className="h-36 bg-white rounded-2xl border border-gray-100" />
          </div>
        ))}
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
  // 날짜 내림차순 정렬
  return Object.values(groups).sort((a, b) => (a.dateKey < b.dateKey ? 1 : -1))
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === '날짜 미상') return '날짜 미상'
  const [year, month, day] = dateStr.split('-')
  return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`
}

function PrescriptionGroup({ group, onMedClick }) {
  const { deptKey, items } = group
  // 처방 기간: 가장 이른 start ~ 가장 늦은 end_date
  const startDates = items.map(m => m.start_date).filter(Boolean).sort()
  const endDates = items.map(m => m.end_date).filter(Boolean).sort()
  const rangeStart = startDates[0]
  const rangeEnd = endDates[endDates.length - 1]

  const hasActive = items.some(m => m.is_active)

  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden hover:border-gray-200 hover:shadow-sm transition-all">
      {/* 그룹 헤더 */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
              <Building2 size={13} className="text-gray-500" />
            </div>
            <span className="font-bold text-gray-900 text-sm">{deptKey}</span>
            <span className="text-xs text-gray-400 font-medium">{items.length}종</span>
          </div>
          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold ${hasActive ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
            {hasActive ? '복용중' : '완료'}
          </span>
        </div>
        {rangeStart && (
          <p className="text-xs text-gray-400 mt-2 ml-9">
            {formatDate(rangeStart)}{rangeEnd ? ` ~ ${formatDate(rangeEnd)}` : ''}
          </p>
        )}
      </div>

      {/* 약품 목록 */}
      <div className="divide-y divide-gray-50">
        {items.map((med) => (
          <button
            key={med.id}
            onClick={() => onMedClick(med.id)}
            className="w-full flex items-center gap-3 px-5 py-3.5 hover:bg-gray-50 transition-colors cursor-pointer text-left"
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
            <ChevronRight size={14} className="text-gray-300 shrink-0" />
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

  const { selectedProfileId: profileId } = useProfile()
  const isInitialLoad = useRef(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    if (!profileId) return
    const fetchMedications = async () => {
      if (isInitialLoad.current) {
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
    fetchMedications()
  }, [activeTab, profileId])

  if (isLoading) return <MedicationListSkeleton />

  const groups = groupByPrescription(medications)

  const emptyMessage = activeTab === '복용중'
    ? { title: '복용 중인 약이 없어요', sub: '처방전을 촬영해서 약을 등록해보세요' }
    : { title: '완료된 처방 내역이 없어요', sub: '복용이 끝난 처방전은 여기에 표시됩니다' }

  return (
    <main className={`min-h-screen bg-gray-50 pb-24 transition-opacity duration-200 ${isRefreshing ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
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

      {/* 탭 */}
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

      <div className="max-w-3xl mx-auto px-6 py-4">
        {groups.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mb-4">
              <Pill size={28} className="text-gray-300" />
            </div>
            <p className="text-gray-400 font-bold mb-1">{emptyMessage.title}</p>
            <p className="text-gray-300 text-sm mb-6">{emptyMessage.sub}</p>
            {activeTab === '복용중' && (
              <button
                onClick={() => router.push('/ocr')}
                className="px-6 py-3 bg-gray-900 text-white text-sm font-bold rounded-full cursor-pointer hover:bg-gray-800 transition-colors"
              >
                처방전 등록하기
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {groups.map((group) => (
              <div key={`${group.dateKey}__${group.deptKey}`}>
                <p className="text-xs font-bold text-gray-400 mb-2 px-1">
                  {formatDate(group.dateKey)} 처방
                </p>
                <PrescriptionGroup
                  group={group}
                  onMedClick={(id) => router.push(`/medication/${id}`)}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <BottomNav />
    </main>
  )
}
