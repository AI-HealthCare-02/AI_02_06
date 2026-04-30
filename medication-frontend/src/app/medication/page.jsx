'use client'

// /medication (복용 가이드) — 처방전 카드 list
//
// 흐름: 사용자 -> 처방전 카드 list (날짜/진료과 정렬 + 약품 검색 + 복용 중/완료 탭)
//       -> 카드 클릭 시 /medication/groups/[id] drill-down 으로 이동
//       -> 그 페이지에서 약품 클릭 시 /medication/[id] 약품 상세 페이지
//
// 정렬 / 검색 / 탭 셋 다 독립적이며 동시 사용 가능. 상태는 PrescriptionGroupContext 가 단일 진실.

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Search, X, ChevronRight, Plus, Building2, Calendar, Hospital } from 'lucide-react'

import BottomNav from '@/components/layout/BottomNav'
import EmptyState from '@/components/common/EmptyState'
import {
  PRESCRIPTION_SORT,
  PRESCRIPTION_STATUS,
  usePrescriptionGroup,
} from '@/contexts/PrescriptionGroupContext'
import { useProfile } from '@/contexts/ProfileContext'

const SORT_LABELS = {
  [PRESCRIPTION_SORT.DATE_DESC]: '날짜 ↓ (최신)',
  [PRESCRIPTION_SORT.DATE_ASC]: '날짜 ↑',
  [PRESCRIPTION_SORT.HOSPITAL_ASC]: '병원 ㄱ-ㅎ',
  [PRESCRIPTION_SORT.HOSPITAL_DESC]: '병원 ㅎ-ㄱ',
}

const STATUS_TABS = [
  { key: PRESCRIPTION_STATUS.ALL, label: '전체' },
  { key: PRESCRIPTION_STATUS.ACTIVE, label: '복용 중' },
  { key: PRESCRIPTION_STATUS.COMPLETED, label: '복용 완료' },
]

function formatDate(isoStr) {
  if (!isoStr) return '날짜 미상'
  const [yyyy, mm, dd] = isoStr.split('-')
  return `${yyyy}년 ${parseInt(mm, 10)}월 ${parseInt(dd, 10)}일`
}

function GroupCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4 animate-pulse space-y-3">
      <div className="h-4 bg-gray-200 rounded w-32" />
      <div className="h-3 bg-gray-200 rounded w-24" />
      <div className="h-8 bg-gray-200 rounded w-full" />
    </div>
  )
}

function PrescriptionCard({ group, onClick }) {
  const dateLabel = formatDate(group.dispensed_date)
  const hospital = group.hospital_name || '병원 미상'
  const dept = group.department || '진료과 미상'
  const statusLabel = group.has_active_medication ? '복용 중' : '복용 완료'
  const statusStyle = group.has_active_medication
    ? 'bg-blue-50 text-blue-600 border-blue-100'
    : 'bg-gray-100 text-gray-500 border-gray-200'
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white rounded-2xl border border-gray-100 hover:border-gray-300 transition-colors p-4 flex items-center gap-3 cursor-pointer"
    >
      <div className="flex-1 min-w-0 space-y-1.5">
        <div className="flex items-center gap-2 text-xs">
          <Calendar size={14} className="text-gray-400 shrink-0" />
          <span className="font-bold text-gray-900">{dateLabel}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-700">
          <Hospital size={14} className="shrink-0 text-gray-400" />
          <span className={group.hospital_name ? 'font-bold' : 'text-gray-400'}>{hospital}</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <Building2 size={14} className="shrink-0" />
          <span>{dept}</span>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${statusStyle}`}>{statusLabel}</span>
          <span className="text-[11px] text-gray-400">약 {group.medications_count}개</span>
        </div>
      </div>
      <ChevronRight size={18} className="text-gray-300 shrink-0" />
    </button>
  )
}

export default function MedicationPage() {
  const router = useRouter()
  const { selectedProfileId } = useProfile()
  const {
    groups,
    isLoading,
    sort,
    search,
    statusFilter,
    setSort,
    setSearch,
    setStatusFilter,
  } = usePrescriptionGroup()

  // 검색 input toggle + 입력 버퍼 (즉시 적용보다 사용자 경험 위해 enter 또는 blur 시 적용)
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [searchDraft, setSearchDraft] = useState('')

  useEffect(() => {
    setSearchDraft(search)
  }, [search])

  const applySearch = () => setSearch(searchDraft.trim())
  const clearSearch = () => {
    setSearchDraft('')
    setSearch('')
    setIsSearchOpen(false)
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      {/* ── 상단 헤더 ── */}
      <header className="sticky top-0 z-20 bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <h1 className="flex-1 text-base font-bold text-gray-900">복용 가이드</h1>
          <button
            type="button"
            onClick={() => setIsSearchOpen((v) => !v)}
            className="p-2 rounded-lg hover:bg-gray-100 cursor-pointer"
            aria-label="약품 검색"
          >
            <Search size={18} className={isSearchOpen ? 'text-blue-500' : 'text-gray-500'} />
          </button>
          <button
            type="button"
            onClick={() => router.push('/ocr')}
            className="p-2 rounded-lg hover:bg-gray-100 cursor-pointer"
            aria-label="처방전 추가"
          >
            <Plus size={18} className="text-gray-700" />
          </button>
        </div>

        {/* 검색 input — toggle 시에만 표시 */}
        {isSearchOpen && (
          <div className="max-w-4xl mx-auto px-4 pb-3">
            <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
              <Search size={16} className="text-gray-400 shrink-0" />
              <input
                type="text"
                value={searchDraft}
                onChange={(e) => setSearchDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') applySearch()
                }}
                onBlur={applySearch}
                placeholder="약품 이름으로 검색"
                className="flex-1 bg-transparent text-sm outline-none"
                autoFocus
              />
              {searchDraft && (
                <button
                  type="button"
                  onClick={clearSearch}
                  className="p-0.5 rounded hover:bg-gray-200 cursor-pointer"
                  aria-label="검색 지우기"
                >
                  <X size={14} className="text-gray-400" />
                </button>
              )}
            </div>
            {search && (
              <p className="text-[11px] text-gray-400 mt-1.5 px-1">
                <span className="font-bold text-gray-600">{search}</span> 약품을 포함하는 처방전을 보여드려요.
              </p>
            )}
          </div>
        )}

        {/* 탭: 전체 / 복용 중 / 복용 완료 */}
        <div className="max-w-4xl mx-auto px-2 pb-1 flex gap-1 overflow-x-auto scrollbar-hide">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setStatusFilter(tab.key)}
              className={`px-3 py-2 text-xs font-bold whitespace-nowrap border-b-2 transition-colors cursor-pointer ${
                statusFilter === tab.key
                  ? 'border-gray-900 text-gray-900'
                  : 'border-transparent text-gray-400 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 space-y-3">
        {/* 정렬 dropdown — 헤더 아래 */}
        <div className="flex items-center justify-end">
          <label className="text-[11px] text-gray-400 mr-2">정렬</label>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="text-xs font-bold border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white cursor-pointer"
          >
            {Object.entries(SORT_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* 카드 list */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <GroupCardSkeleton key={i} />
            ))}
          </div>
        ) : !selectedProfileId ? (
          <EmptyState title="프로필을 선택해주세요" message="프로필을 선택하면 처방전이 표시됩니다." />
        ) : groups.length === 0 ? (
          <EmptyState
            title={search ? '검색 결과가 없어요' : '등록된 처방전이 없어요'}
            message={search ? `'${search}' 약품을 포함하는 처방전을 찾지 못했어요.` : '처방전을 등록해 보세요.'}
          />
        ) : (
          <div className="space-y-3">
            {groups.map((g) => (
              <PrescriptionCard
                key={g.id}
                group={g}
                onClick={() => router.push(`/medication/groups/${g.id}`)}
              />
            ))}
          </div>
        )}
      </div>

      <BottomNav />
    </main>
  )
}
