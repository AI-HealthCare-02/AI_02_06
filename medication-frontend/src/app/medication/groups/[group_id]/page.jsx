'use client'

// /medication/groups/[group_id] — 처방전 그룹 drill-down
//
// 사용자가 /medication 의 처방전 카드를 누르면 본 페이지로. 그룹 메타 + 약 list 표시.
// 약품 카드를 누르면 기존 /medication/[id] 약품 상세 페이지로 이동.

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Calendar, Building2, ChevronRight, Pill } from 'lucide-react'

import api from '@/lib/api'
import BottomNav from '@/components/layout/BottomNav'

function formatDate(isoStr) {
  if (!isoStr) return '날짜 미상'
  const [yyyy, mm, dd] = isoStr.split('-')
  return `${yyyy}년 ${parseInt(mm, 10)}월 ${parseInt(dd, 10)}일`
}

function MedicationItem({ medication, onClick }) {
  const dose = medication.dose_per_intake || ''
  const instr = medication.intake_instruction || ''
  const inactive = !medication.is_active
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white rounded-2xl border border-gray-100 hover:border-gray-300 transition-colors p-4 flex items-center gap-3 cursor-pointer"
    >
      <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-500 flex items-center justify-center shrink-0">
        <Pill size={18} />
      </div>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-900 truncate">{medication.medicine_name}</span>
          {inactive && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0">완료</span>
          )}
        </div>
        {(dose || instr) && (
          <p className="text-xs text-gray-500 truncate">
            {[dose, instr].filter(Boolean).join(' · ')}
          </p>
        )}
      </div>
      <ChevronRight size={18} className="text-gray-300 shrink-0" />
    </button>
  )
}

export default function PrescriptionGroupDetailPage() {
  const router = useRouter()
  const params = useParams()
  const groupId = params?.group_id
  const [group, setGroup] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!groupId) return
    let cancelled = false
    ;(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const { data } = await api.get(`/api/v1/prescription-groups/${groupId}`)
        if (!cancelled) setGroup(data)
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.status === 404 ? '처방전을 찾을 수 없어요.' : '처방전을 불러오지 못했어요.')
        }
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [groupId])

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <header className="sticky top-0 z-20 bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-2 py-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.push('/medication')}
            className="p-2 rounded-lg hover:bg-gray-100 cursor-pointer"
            aria-label="뒤로"
          >
            <ArrowLeft size={18} className="text-gray-700" />
          </button>
          <h1 className="flex-1 text-base font-bold text-gray-900 truncate">처방전 상세</h1>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {isLoading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-4 animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-32" />
            <div className="h-3 bg-gray-200 rounded w-24" />
          </div>
        ) : error ? (
          <p className="text-sm text-red-500 text-center py-10">{error}</p>
        ) : group ? (
          <>
            {/* 그룹 메타 카드 */}
            <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-bold text-gray-900">
                <Calendar size={16} className="text-gray-400" />
                <span>{formatDate(group.dispensed_date)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Building2 size={14} />
                <span>{group.department || '진료과 미상'}</span>
              </div>
              <p className="text-[11px] text-gray-400 pt-1">
                약 {group.medications?.length || 0}개 · 등록 경로 {group.source}
              </p>
            </div>

            {/* 약 list */}
            {(group.medications || []).length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">이 처방전엔 등록된 약이 없어요.</p>
            ) : (
              <div className="space-y-2">
                {group.medications.map((m) => (
                  <MedicationItem
                    key={m.id}
                    medication={m}
                    onClick={() => router.push(`/medication/${m.id}`)}
                  />
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>

      <BottomNav />
    </main>
  )
}
