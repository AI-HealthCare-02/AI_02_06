'use client'

// /medication/groups/[group_id] — 처방전 그룹 drill-down
//
// 모든 fetch / mutation 은 PrescriptionGroupContext 의 hook 으로 위임.
// 페이지는 화면 정책 (편집 모드 / confirm / 토스트) 만 책임.

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Calendar,
  Building2,
  ChevronRight,
  Pill,
  Trash2,
  Pencil,
  CircleCheck,
  Hospital,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { showError } from '@/lib/api'
import BottomNav from '@/components/layout/BottomNav'
import { usePrescriptionGroup } from '@/contexts/PrescriptionGroupContext'

function formatDate(isoStr) {
  if (!isoStr) return '날짜 미상'
  const [yyyy, mm, dd] = isoStr.split('-')
  return `${yyyy}년 ${parseInt(mm, 10)}월 ${parseInt(dd, 10)}일`
}

function EditableMetaRow({
  icon,
  value,
  placeholder,
  emptyLabel,
  isEditing,
  draft,
  onDraft,
  onStart,
  onCancel,
  onSave,
  isSaving,
  maxLength,
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-700">
      {icon}
      {isEditing ? (
        <input
          type="text"
          value={draft}
          onChange={(e) => onDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              onSave()
            }
            if (e.key === 'Escape') {
              e.preventDefault()
              onCancel()
            }
          }}
          onBlur={() => {
            if (!isSaving) onSave()
          }}
          placeholder={placeholder}
          maxLength={maxLength}
          className="flex-1 bg-gray-50 border border-gray-200 rounded px-2 py-1 outline-none focus:border-gray-400"
          autoFocus
        />
      ) : (
        <>
          <span
            className={`${value ? 'font-bold' : 'text-gray-400'} cursor-text select-none`}
            onDoubleClick={onStart}
            title="더블클릭하거나 연필 아이콘으로 수정"
          >
            {value || emptyLabel}
          </span>
          <button
            type="button"
            onClick={onStart}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700 cursor-pointer"
            aria-label="수정"
          >
            <Pencil size={12} />
          </button>
        </>
      )}
    </div>
  )
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
  const {
    groupsById,
    fetchGroupDetail,
    updateGroup,
    markGroupCompleted,
    deleteGroup,
  } = usePrescriptionGroup()

  // detail 은 Context cache 로부터 derive — fetch 가 끝나면 cache 가 채워지며 자동 렌더.
  const group = groupId ? groupsById[groupId] || null : null
  const [isLoading, setIsLoading] = useState(!group)
  const [error, setError] = useState(null)
  const [editingField, setEditingField] = useState(null)
  const [draft, setDraft] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isCompleting, setIsCompleting] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!groupId) return
    let cancelled = false
    setIsLoading(true)
    setError(null)
    fetchGroupDetail(groupId, { forceRefresh: true })
      .catch((err) => {
        if (cancelled) return
        setError(err?.response?.status === 404 ? '처방전을 찾을 수 없어요.' : '처방전을 불러오지 못했어요.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [groupId, fetchGroupDetail])

  const startEdit = (field) => {
    setDraft(group?.[field] || '')
    setEditingField(field)
  }
  const cancelEdit = () => {
    setEditingField(null)
    setDraft('')
  }
  const saveEdit = async () => {
    if (!groupId || !editingField) return
    const next = draft.trim() || null
    const currentField = editingField
    if ((group?.[currentField] || null) === next) {
      setEditingField(null)
      return
    }
    setIsSaving(true)
    try {
      await updateGroup(groupId, { [currentField]: next })
      setEditingField(null)
      toast.success(currentField === 'hospital_name' ? '병원을 수정했어요.' : '진료과를 수정했어요.')
    } catch {
      showError('수정에 실패했어요.')
    } finally {
      setIsSaving(false)
    }
  }

  const handleComplete = async () => {
    if (!groupId || !group) return
    if (!confirm('이 처방전을 복용 완료로 처리할까요? 그룹 안 모든 약이 비활성으로 변경됩니다.')) return
    setIsCompleting(true)
    try {
      await markGroupCompleted(groupId)
      toast.success('복용 완료 처리됐어요.')
    } catch {
      showError('복용 완료 처리에 실패했어요.')
    } finally {
      setIsCompleting(false)
    }
  }

  const handleDelete = async () => {
    if (!groupId) return
    if (!confirm('이 처방전을 삭제할까요? 안 약품과 관련 가이드도 함께 정리됩니다.')) return
    setIsDeleting(true)
    try {
      await deleteGroup(groupId)
      toast.success('처방전을 삭제했어요.')
      router.push('/medication')
    } catch {
      showError('삭제에 실패했어요.')
      setIsDeleting(false)
    }
  }

  const allInactive = group?.medications?.length > 0 && group.medications.every((m) => !m.is_active)

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
          {group && (
            <>
              <button
                type="button"
                onClick={handleComplete}
                disabled={isCompleting || allInactive}
                title={allInactive ? '이미 복용 완료됨' : '복용 완료 처리'}
                className={`p-2 rounded-lg cursor-pointer transition-colors ${
                  allInactive ? 'text-gray-300 cursor-default' : 'text-green-600 hover:bg-green-50'
                }`}
                aria-label="복용 완료 처리"
              >
                <CircleCheck size={18} />
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="p-2 rounded-lg hover:bg-red-50 text-red-500 cursor-pointer"
                aria-label="처방전 삭제"
              >
                <Trash2 size={18} />
              </button>
            </>
          )}
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {isLoading && !group ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-4 animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-32" />
            <div className="h-3 bg-gray-200 rounded w-24" />
          </div>
        ) : error ? (
          <p className="text-sm text-red-500 text-center py-10">{error}</p>
        ) : group ? (
          <>
            <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm font-bold text-gray-900">
                <Calendar size={16} className="text-gray-400" />
                <span>{formatDate(group.dispensed_date)}</span>
              </div>
              <EditableMetaRow
                icon={<Hospital size={14} className="shrink-0 text-gray-400" />}
                fieldKey="hospital_name"
                value={group.hospital_name}
                placeholder="병원 (예: 서울내과의원)"
                emptyLabel="병원 미상"
                isEditing={editingField === 'hospital_name'}
                draft={draft}
                onDraft={setDraft}
                onStart={() => startEdit('hospital_name')}
                onCancel={cancelEdit}
                onSave={saveEdit}
                isSaving={isSaving}
                maxLength={128}
              />
              <EditableMetaRow
                icon={<Building2 size={14} className="shrink-0 text-gray-400" />}
                fieldKey="department"
                value={group.department}
                placeholder="진료과 (예: 내과)"
                emptyLabel="진료과 미상"
                isEditing={editingField === 'department'}
                draft={draft}
                onDraft={setDraft}
                onStart={() => startEdit('department')}
                onCancel={cancelEdit}
                onSave={saveEdit}
                isSaving={isSaving}
                maxLength={64}
              />
              <p className="text-[11px] text-gray-400 pt-1">
                약 {group.medications?.length || 0}개 · 등록 경로 {group.source}
                {allInactive && <span className="ml-2 text-green-500 font-bold">· 복용 완료</span>}
              </p>
            </div>

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
