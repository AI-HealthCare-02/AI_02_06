'use client'
import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Clock, Utensils, Pill, Calendar, AlertTriangle, AlertCircle, Ban, Trash2 } from 'lucide-react'
import BottomNav from '@/components/layout/BottomNav'
import api from '@/lib/api'
import { useMedication } from '@/contexts/MedicationContext'

function DetailSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24 animate-pulse">
      <div className="h-16 bg-white border-b border-gray-100" />
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-4">
        <div className="h-32 bg-gray-900 rounded-2xl opacity-80" />
        <div className="h-10 bg-white rounded-xl border border-gray-100" />
        <div className="h-48 bg-white rounded-2xl border border-gray-100" />
      </div>
    </div>
  )
}

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

export default function MedicationDetailPage() {
  const router = useRouter()
  const { id } = useParams()
  const [isLoading, setIsLoading] = useState(true)
  const [isDrugInfoLoading, setIsDrugInfoLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const { medications, deleteMedication, deactivateMedication, getDrugInfo } = useMedication()
  const [fallbackMed, setFallbackMed] = useState(null)
  const [drugInfo, setDrugInfo] = useState(null)
  const [activeTab, setActiveTab] = useState('용법')

  // MedicationContext 의 store 에 있으면 그대로 사용 (즉시 반영) — list 다녀온 후 detail 진입 시
  // 직접 URL 진입 등으로 store 가 비어있으면 fallback fetch
  const med = medications.find(m => m.id === id) || fallbackMed

  useEffect(() => {
    if (!id) return
    if (medications.find(m => m.id === id)) {
      setIsLoading(false)
      return
    }
    if (medications.length === 0) {
      // store 가 아직 안 채워졌을 수도 있어 한 tick 기다림 (Context 의 첫 fetch 진행 중)
      return
    }
    // store 에 채워져있는데 해당 id 가 없음 → 직접 fetch
    const fetchMedication = async () => {
      try {
        const res = await api.get(`/api/v1/medications/${id}`)
        setFallbackMed(res.data)
      } catch (err) {
        alert('약품 정보를 불러올 수 없습니다.')
        router.push('/medication')
      } finally {
        setIsLoading(false)
      }
    }
    fetchMedication()
  }, [id, router, medications])

  useEffect(() => {
    if (med) setIsLoading(false)
  }, [med])

  // 주의사항/부작용/상호작용 탭 선택 시 drug-info — Context 의 lazy cache 사용
  // ('용법' 탭에서는 호출 안 함, 한 번 받은 결과는 같은 세션 동안 cache 재활용)
  useEffect(() => {
    if (!med || activeTab === '용법') return
    if (drugInfo) return
    setIsDrugInfoLoading(true)
    getDrugInfo(id)
      .then(setDrugInfo)
      .catch(err => console.error(err))
      .finally(() => setIsDrugInfoLoading(false))
  }, [activeTab, med, drugInfo, id, getDrugInfo])

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      // Context 의 deleteMedication 이 응답 받자마자 store 갱신 → list 자동 반영
      await deleteMedication(id)
      router.push('/medication')
    } catch (err) {
      console.error(err)
      alert('삭제에 실패했습니다. 다시 시도해주세요.')
      setIsDeleting(false)
      setShowDeleteModal(false)
    }
  }

  // 복용 완료 처리: 삭제와 달리 is_active=false로만 변경 (soft 처리)
  // 완료된 약품은 '완료' 탭에서 계속 조회 가능
  const handleDeactivate = async () => {
    try {
      // Context 의 deactivateMedication 이 응답으로 store in-place 갱신
      await deactivateMedication(id)
    } catch (err) {
      console.error(err)
      alert('처리에 실패했습니다. 다시 시도해주세요.')
    }
  }

  if (isLoading) return <DetailSkeleton />
  if (!med) return null

  // 값이 없는 항목은 filter로 제외 — 빈 필드가 카드에 표시되지 않도록 처리
  const dosageItems = [
    { icon: Pill, label: '1회 복용량', value: med.dose_per_intake },
    { icon: Clock, label: '1일 복용 횟수', value: med.daily_intake_count ? `${med.daily_intake_count}회` : null },
    { icon: Calendar, label: '총 복용 일수', value: med.total_intake_days ? `${med.total_intake_days}일` : null },
    { icon: Utensils, label: '복용 방법', value: med.intake_instruction },
  ].filter(item => item.value)

  const tabs = ['용법', '주의사항', '부작용', '상호작용']

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <div className="max-w-2xl mx-auto">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => router.back()} className="text-gray-400 hover:text-black cursor-pointer text-xl">←</button>
        <div className="flex-1">
          <h1 className="font-bold text-gray-900">약품 상세</h1>
          {med.department && <p className="text-xs text-gray-400">{med.department}</p>}
        </div>
        <button
          onClick={() => setShowDeleteModal(true)}
          className="w-9 h-9 flex items-center justify-center rounded-xl text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer"
        >
          <Trash2 size={18} />
        </button>
      </div>

      <div className="px-6 py-6 space-y-4">
        {/* 약품명 카드 */}
        <div className="bg-gray-900 rounded-2xl p-6 text-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              {med.category && (
                <span className="text-xs font-bold text-gray-400 bg-gray-800 px-3 py-1 rounded-full mb-3 inline-block">{med.category}</span>
              )}
              <h2 className="text-xl font-black leading-snug mt-1">{med.medicine_name}</h2>
              <p className="text-gray-400 text-sm mt-2">
                남은 복용 {med.remaining_intake_count} / {med.total_intake_count}회
              </p>
            </div>
            <div className={`px-3 py-1.5 rounded-full text-xs font-bold shrink-0 ${med.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
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
            {/* 용법 탭 */}
            {activeTab === '용법' && (
              <div className="space-y-3 animate-in fade-in duration-200">
                {dosageItems.length > 0 ? (
                  dosageItems.map(({ icon: Icon, label, value }) => (
                    <div key={label} className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                      <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center border border-gray-100 shrink-0">
                        <Icon size={16} className="text-gray-500" />
                      </div>
                      <div>
                        <p className="text-xs text-gray-400">{label}</p>
                        <p className="font-bold text-sm text-gray-900">{value}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-gray-400 text-center py-6">복용 정보가 없습니다.</p>
                )}
                <div className="mt-4 p-4 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-400 mb-1">처방 기간</p>
                  <p className="font-bold text-sm text-gray-900">
                    {med.start_date}
                    {med.end_date ? ` ~ ${med.end_date}` : ''}
                  </p>
                </div>
              </div>
            )}

            {/* 주의사항 탭 */}
            {activeTab === '주의사항' && (
              <div className="space-y-3 animate-in fade-in duration-200">
                {isDrugInfoLoading ? (
                  <DrugInfoSkeleton />
                ) : drugInfo?.warnings?.length > 0 ? (
                  <>
                    {drugInfo.warnings.map((w, i) => (
                      <div key={i} className="flex gap-3 p-4 bg-yellow-50 rounded-xl">
                        <AlertTriangle size={16} className="text-yellow-500 shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-600 leading-relaxed">{w}</p>
                      </div>
                    ))}
                  </>
                ) : (
                  <p className="text-sm text-gray-400 text-center py-6">주의사항 정보를 불러올 수 없습니다.</p>
                )}
              </div>
            )}

            {/* 부작용 탭 */}
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

            {/* 상호작용 탭 */}
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

        {/* 면책 문구 */}
        <p className="text-xs text-gray-300 text-center leading-relaxed px-2">
          이 정보는 AI가 생성한 참고용 정보입니다. 정확한 복약 지도는 반드시 전문 의료인과 상의하십시오.
        </p>
      </div>
      </div>

      {/* 삭제 확인 모달 */}
      {showDeleteModal && (
        <DeleteConfirmModal
          medicineName={med.medicine_name}
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteModal(false)}
          isDeleting={isDeleting}
        />
      )}

      <BottomNav />
    </main>
  )
}
