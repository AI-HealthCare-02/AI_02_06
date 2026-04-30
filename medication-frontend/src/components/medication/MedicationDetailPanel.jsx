'use client'

// 약품 상세 본문 panel — /medication/[id] 페이지와 처방전 drill-down 의 데스크탑
// split-pane 우측에서 공유. 페이지 헤더 (처방전 상세의 ← 버튼 등) 는 외부에서
// 책임지므로 본 컴포넌트는 본문만 렌더한다.

import { useEffect, useState } from 'react'

import { AlertCircle, AlertTriangle, Ban, Calendar, Clock, Pill, Trash2, Utensils } from 'lucide-react'

import api from '@/lib/api'
import { useMedication } from '@/contexts/MedicationContext'
import TimeSlotPicker from '@/components/medication/TimeSlotPicker'

function DrugInfoSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-14 bg-gray-100 rounded-xl" />
      ))}
    </div>
  )
}

function DeleteConfirmModal({ medicineName, onConfirm, onCancel, isDeleting }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 px-4 pb-6">
      <div className="bg-white rounded-2xl w-full max-w-sm p-6 space-y-4">
        <div className="text-center space-y-1">
          <div className="w-12 h-12 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-3">
            <Trash2 size={20} className="text-red-500" />
          </div>
          <p className="font-bold text-gray-900">약품을 삭제할까요?</p>
          <p className="text-sm text-gray-400 leading-relaxed">
            <span className="font-bold text-gray-700">{medicineName}</span> 복용 기록이<br />영구적으로 삭제됩니다.
          </p>
        </div>
        <div className="flex gap-2 pt-1">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-gray-500 bg-gray-100 cursor-pointer hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 py-3 rounded-xl text-sm font-bold text-white bg-red-500 cursor-pointer hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {isDeleting ? '삭제 중...' : '삭제'}
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * @param {object} props
 * @param {string} props.medicationId 표시할 medication UUID.
 * @param {() => void} [props.onDeleted] 삭제 완료 시 콜백 (페이지 이동 / panel close 등).
 */
export default function MedicationDetailPanel({ medicationId, onDeleted }) {
  const id = medicationId
  const { medications, deleteMedication, deactivateMedication, getDrugInfo } = useMedication()
  const [isLoading, setIsLoading] = useState(true)
  const [isDrugInfoLoading, setIsDrugInfoLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [fallbackMed, setFallbackMed] = useState(null)
  const [drugInfo, setDrugInfo] = useState(null)
  const [activeTab, setActiveTab] = useState('용법')

  const med = medications.find((m) => m.id === id) || fallbackMed

  useEffect(() => {
    if (!id) return
    /* eslint-disable react-hooks/set-state-in-effect -- id 변경 시 panel state reset */
    setDrugInfo(null)
    setActiveTab('용법')
    if (medications.find((m) => m.id === id)) {
      setIsLoading(false)
      return
    }
    if (medications.length === 0) return
    setIsLoading(true)
    /* eslint-enable react-hooks/set-state-in-effect */
    api
      .get(`/api/v1/medications/${id}`)
      .then((res) => setFallbackMed(res.data))
      .catch(() => setFallbackMed(null))
      .finally(() => setIsLoading(false))
  }, [id, medications])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- store 도착 시 loading off
    if (med) setIsLoading(false)
  }, [med])

  useEffect(() => {
    if (!med || drugInfo || !id) return
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 비동기 fetch 의 trigger 이며 컴포넌트 외부 store (lazy LLM cache) 와 동기화
    setIsDrugInfoLoading(true)
    getDrugInfo(id)
      .then((data) => {
        if (!cancelled) setDrugInfo(data)
      })
      .catch((err) => console.error(err))
      .finally(() => {
        if (!cancelled) setIsDrugInfoLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [med, drugInfo, id, getDrugInfo])

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteMedication(id)
      onDeleted?.()
    } catch (err) {
      console.error(err)
      alert('삭제에 실패했습니다. 다시 시도해주세요.')
      setIsDeleting(false)
      setShowDeleteModal(false)
    }
  }

  const handleDeactivate = async () => {
    try {
      await deactivateMedication(id)
    } catch (err) {
      console.error(err)
      alert('처리에 실패했습니다. 다시 시도해주세요.')
    }
  }

  if (!id) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-400 py-12">
        약을 선택하면 상세 정보가 표시됩니다.
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="px-6 py-6 space-y-4 animate-pulse">
        <div className="h-32 bg-gray-900 rounded-2xl opacity-80" />
        <div className="h-10 bg-white rounded-xl border border-gray-100" />
        <div className="h-48 bg-white rounded-2xl border border-gray-100" />
      </div>
    )
  }

  if (!med) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-gray-400 py-12">
        약품 정보를 찾을 수 없습니다.
      </div>
    )
  }

  // 짧은 숫자형 값 (1일 복용 횟수 / 총 복용 일수) 은 grid 2-col 로 한 행에 좌우 배치 —
  // 사용자 피드백: 단독 row 일 때 오른쪽 여백 낭비.
  // 자유 텍스트 (1회 복용량 / 복용 방법) 은 full row 로 유지 — 한 줄에 가둘 수 없는 길이 가능성.
  const compactItems = [
    {
      icon: Clock,
      label: '1일 복용 횟수',
      value: med.daily_intake_count ? `${med.daily_intake_count}회` : null,
    },
    {
      icon: Calendar,
      label: '총 복용 일수',
      value: med.total_intake_days ? `${med.total_intake_days}일` : null,
    },
  ].filter((item) => item.value)
  const fullRowItems = [
    { icon: Pill, label: '1회 복용량', value: med.dose_per_intake },
    { icon: Utensils, label: '복용 방법', value: med.intake_instruction },
  ].filter((item) => item.value)

  const tabs = ['용법', '주의사항', '부작용', '상호작용']

  return (
    <div className="space-y-4">
      {/* 약품명 카드 + 삭제 버튼 */}
      <div className="bg-gray-900 rounded-2xl p-6 text-white relative">
        <button
          onClick={() => setShowDeleteModal(true)}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-red-400 hover:bg-gray-800 transition-colors cursor-pointer"
          aria-label="약품 삭제"
        >
          <Trash2 size={16} />
        </button>
        <div className="flex items-start justify-between gap-4 pr-10">
          <div className="flex-1">
            {med.category && (
              <span className="text-xs font-bold text-gray-400 bg-gray-800 px-3 py-1 rounded-full mb-3 inline-block">
                {med.category}
              </span>
            )}
            <h2 className="text-xl font-black leading-snug mt-1">{med.medicine_name}</h2>
            <p className="text-gray-400 text-sm mt-2 flex items-center flex-wrap gap-x-3">
              <span>
                남은 복용 {med.remaining_intake_count} / {med.total_intake_count}회
              </span>
              {med.dispensed_date && (
                <span className="text-gray-500">· 처방일 {med.dispensed_date.replace(/-/g, '.')}</span>
              )}
            </p>
          </div>
          <div
            className={`px-3 py-1.5 rounded-full text-xs font-bold shrink-0 ${
              med.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'
            }`}
          >
            {med.is_active ? '복용중' : '완료'}
          </div>
        </div>
        {med.is_active && (
          <button
            onClick={handleDeactivate}
            className="mt-4 w-full py-2.5 rounded-xl text-xs font-bold text-gray-400 bg-gray-800 hover:bg-gray-700 hover:text-white transition-colors cursor-pointer"
          >
            복용 완료로 변경
          </button>
        )}
      </div>

      {/* 탭 */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <div className="flex border-b border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-3 text-xs font-bold cursor-pointer transition-colors ${
                activeTab === tab ? 'text-gray-900 border-b-2 border-gray-900' : 'text-gray-400'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="p-5">
          {activeTab === '용법' && (
            <div className="space-y-3 animate-in fade-in duration-200">
              {compactItems.length === 0 && fullRowItems.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">복용 정보가 없습니다.</p>
              ) : (
                <>
                  {/* 1회 복용량 / 복용 방법 — 자유 텍스트라 full row */}
                  {fullRowItems.map(({ icon: Icon, label, value }) => (
                    <div key={label} className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                      <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center border border-gray-100 shrink-0">
                        <Icon size={16} className="text-gray-500" />
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">{label}</p>
                        <p className="font-bold text-sm text-gray-900">{value}</p>
                      </div>
                    </div>
                  ))}
                  {/* 1일 복용 횟수 + 총 복용 일수 — 한 행에 좌우 grid 2-col */}
                  {compactItems.length > 0 && (
                    <div className="grid grid-cols-2 gap-3">
                      {compactItems.map(({ icon: Icon, label, value }) => (
                        <div
                          key={label}
                          className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl"
                        >
                          <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center border border-gray-100 shrink-0">
                            <Icon size={16} className="text-gray-500" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs text-gray-400">{label}</p>
                            <p className="font-bold text-sm text-gray-900 truncate">{value}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* 복용 시간대 — 토글 시 PATCH /medications/{id} + 홈 TodaySchedule 즉시 반영 */}
              <div className="mt-4 p-4 bg-gray-50 rounded-xl space-y-2">
                <p className="text-xs text-gray-400">복용 시간대</p>
                <TimeSlotPicker medication={med} />
                <p className="text-[11px] text-gray-400">
                  선택한 시간대는 홈 화면의 시간대별 복용 알림에 표시됩니다.
                </p>
              </div>
              {drugInfo?.dosage && (
                <div className="mt-4 p-4 bg-blue-50 rounded-xl">
                  <p className="text-xs font-black text-blue-600 mb-2 uppercase tracking-wide">
                    식약처 표준 용법
                  </p>
                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                    {drugInfo.dosage}
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === '주의사항' && (
            <div className="space-y-5 animate-in fade-in duration-200">
              {isDrugInfoLoading ? (
                <DrugInfoSkeleton />
              ) : drugInfo?.warnings?.length > 0 ? (
                drugInfo.warnings.map((section) => (
                  <div key={section.category}>
                    <h3 className="text-xs font-black text-gray-700 mb-2 uppercase tracking-wide">
                      {section.category}
                    </h3>
                    <div className="space-y-2">
                      {section.items.map((item, i) => (
                        <div key={i} className="flex gap-3 p-4 bg-yellow-50 rounded-xl">
                          <AlertTriangle size={16} className="text-yellow-500 shrink-0 mt-0.5" />
                          <p className="text-sm text-gray-600 leading-relaxed">{item}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400 text-center py-6">주의사항 정보를 불러올 수 없습니다.</p>
              )}
            </div>
          )}

          {activeTab === '부작용' && (
            <div className="animate-in fade-in duration-200">
              {isDrugInfoLoading ? (
                <DrugInfoSkeleton />
              ) : drugInfo?.side_effects?.length > 0 ? (
                <>
                  <div className="flex flex-wrap gap-2 mb-5">
                    {drugInfo.side_effects.map((s, i) => (
                      <span key={i} className="bg-red-50 text-red-500 px-4 py-2 rounded-full text-sm font-bold">
                        {s}
                      </span>
                    ))}
                  </div>
                  <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                    <p className="text-red-600 text-sm font-bold mb-1 flex items-center gap-1">
                      <AlertCircle size={14} />
                      이런 증상이 나타나면
                    </p>
                    <p className="text-gray-500 text-xs leading-relaxed">{drugInfo.severe_reaction_advice}</p>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-400 text-center py-6">부작용 정보를 불러올 수 없습니다.</p>
              )}
            </div>
          )}

          {activeTab === '상호작용' && (
            <div className="space-y-3 animate-in fade-in duration-200">
              {isDrugInfoLoading ? (
                <DrugInfoSkeleton />
              ) : drugInfo?.interactions?.length > 0 ? (
                drugInfo.interactions.map((item, i) => (
                  <div key={i} className="flex gap-3 p-4 bg-orange-50 rounded-xl">
                    <Ban size={16} className="text-orange-500 shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-bold text-gray-800">{item.drug}</p>
                      <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-400 text-center py-6">상호작용 정보를 불러올 수 없습니다.</p>
              )}
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-300 text-center leading-relaxed px-2">
        이 정보는 AI가 생성한 참고용 정보입니다. 정확한 복약 지도는 반드시 전문 의료인과 상의하십시오.
      </p>

      {showDeleteModal && (
        <DeleteConfirmModal
          medicineName={med.medicine_name}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteModal(false)}
          isDeleting={isDeleting}
        />
      )}
    </div>
  )
}
