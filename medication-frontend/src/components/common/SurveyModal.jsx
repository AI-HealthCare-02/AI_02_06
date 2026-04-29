'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { showError } from '@/lib/api'
import { useProfile } from '@/contexts/ProfileContext'

export default function SurveyModal({ onClose, userName, profileId }) {
  const { profiles, updateProfile, createProfile } = useProfile()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [existingProfile, setExistingProfile] = useState(null)
  const [form, setForm] = useState({
    age: '', gender: '', height: '', weight: '',
    is_smoking: null, is_drinking: null,
    conditions: [], allergies: []
  })

  // ProfileContext 가 이미 가진 데이터 재사용 — 별도 GET /profiles/{id} 호출 안 함.
  // form 은 사용자 입력 상태라 props/context 변동 시 1회 sync (mount + profileId 변경 시).
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!profileId) return
    const profile = profiles.find(p => p.id === profileId)
    if (!profile) return
    setExistingProfile(profile)
    if (profile.health_survey) {
      const survey = profile.health_survey
      setForm({
        age: survey.age?.toString() || '',
        gender: survey.gender || '',
        height: survey.height?.toString() || '',
        weight: survey.weight?.toString() || '',
        is_smoking: survey.is_smoking ?? null,
        is_drinking: survey.is_drinking ?? null,
        conditions: survey.conditions || [],
        allergies: survey.allergies || [],
      })
    }
  }, [profileId, profiles])
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSkip = async () => {
    if (!existingProfile) {
      setIsSubmitting(true)
      try {
        await createProfile({ relation_type: 'SELF', name: userName || '나', health_survey: null })
      } catch (err) { console.error(err) }
      setIsSubmitting(false)
    }
    onClose()
  }

  const handleSubmit = async () => {
    if (!form.age || !form.gender) {
      showError('나이와 성별은 필수 입력입니다.')
      return
    }
    setIsSubmitting(true)
    const healthSurvey = {
      age: parseInt(form.age) || null,
      gender: form.gender || null,
      height: parseInt(form.height) || null,
      weight: parseFloat(form.weight) || null,
      is_smoking: form.is_smoking,
      is_drinking: form.is_drinking,
      conditions: form.conditions.length > 0 ? form.conditions : null,
      allergies: form.allergies.length > 0 ? form.allergies : null
    }
    try {
      if (existingProfile) {
        await updateProfile(existingProfile.id, { health_survey: healthSurvey })
      } else {
        await createProfile({ relation_type: 'SELF', name: userName || '나', health_survey: healthSurvey })
      }
      onClose()
    } catch (err) {
      console.error(err)
      showError(err.parsed?.message || '설문 저장에 실패했습니다.')
    }
    setIsSubmitting(false)
  }

  const selectedClass = 'bg-gray-900 text-white border-gray-900'
  const unselectedClass = 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <div className="bg-white rounded-[32px] w-full max-w-lg max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">
        {/* 헤더 */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center shrink-0">
          <div>
            <h2 className="font-black text-xl text-gray-900">건강 정보 입력</h2>
            <p className="text-gray-400 text-sm mt-1">{userName} 님에게 딱 맞는 복약 가이드를 준비할게요</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X size={24} className="text-gray-400" />
          </button>
        </div>

        {/* 스크롤 영역 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 기본 정보 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              기본 정보 <span className="text-red-400 text-xs">*필수</span>
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">나이 *</label>
                <input type="number" placeholder="세" min={1} max={120}
                  value={form.age}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 1 && parseInt(val) <= 120)) setForm({...form, age: val})
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">성별 *</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map(g => (
                    <button key={g} type="button" onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.gender === g ? selectedClass : unselectedClass}`}>
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">키 (cm)</label>
                <input type="number" placeholder="cm" min={50} max={250}
                  value={form.height}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 50 && parseInt(val) <= 250)) setForm({...form, height: val})
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">몸무게 (kg)</label>
                <input type="number" placeholder="kg" min={1} max={300} step={0.1}
                  value={form.weight}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseFloat(val) >= 1 && parseFloat(val) <= 300)) setForm({...form, weight: val})
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none bg-white" />
              </div>
            </div>
          </div>

          {/* 생활 습관 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              생활 습관
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">흡연 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} type="button" onClick={() => setForm({...form, is_smoking: v})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.is_smoking === v ? selectedClass : unselectedClass}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block">음주 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} type="button" onClick={() => setForm({...form, is_drinking: v})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer ${form.is_drinking === v ? selectedClass : unselectedClass}`}>
                      {v ? '예' : '아니오'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 질환 및 알레르기 */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
              질환 및 알레르기
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-2 block">기저질환 (중복 선택)</label>
                <div className="flex flex-wrap gap-2">
                  {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map(item => (
                    <button key={item} type="button"
                      onClick={() => {
                        let updated
                        if (item === '없음') {
                          updated = form.conditions.includes(item) ? [] : ['없음']
                        } else {
                          const withoutNone = form.conditions.filter(c => c !== '없음')
                          updated = withoutNone.includes(item) ? withoutNone.filter(c => c !== item) : [...withoutNone, item]
                        }
                        setForm({...form, conditions: updated})
                      }}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${form.conditions.includes(item) ? chipSelected : chipUnselected}`}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-2 block">알레르기 (중복 선택)</label>
                <div className="flex flex-wrap gap-2">
                  {['페니실린', '아스피린', '항생제', '소염제', '없음'].map(item => (
                    <button key={item} type="button"
                      onClick={() => {
                        let updated
                        if (item === '없음') {
                          updated = form.allergies.includes(item) ? [] : ['없음']
                        } else {
                          const withoutNone = form.allergies.filter(a => a !== '없음')
                          updated = withoutNone.includes(item) ? withoutNone.filter(a => a !== item) : [...withoutNone, item]
                        }
                        setForm({...form, allergies: updated})
                      }}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-all cursor-pointer ${form.allergies.includes(item) ? chipSelected : chipUnselected}`}>
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 하단 버튼 */}
        <div className="p-6 pt-4 border-t border-gray-100 flex gap-3 shrink-0">
          <button onClick={handleSkip} disabled={isSubmitting}
            className="flex-1 py-4 rounded-2xl bg-gray-100 text-gray-500 font-bold hover:bg-gray-200 transition-all disabled:opacity-50">
            건너뛰기
          </button>
          <button onClick={handleSubmit} disabled={isSubmitting}
            className="flex-1 py-4 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all shadow-lg disabled:opacity-50">
            {isSubmitting ? '저장 중...' : '저장하기'}
          </button>
        </div>
      </div>
    </div>
  )
}
