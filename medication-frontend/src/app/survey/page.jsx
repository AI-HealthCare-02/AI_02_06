'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Check, Activity, User, Heart, Loader2, X, Activity as ActivityIcon } from 'lucide-react'
import api, { handleApiError } from '@/lib/api'
import toast from 'react-hot-toast'
import { useProfile } from '@/contexts/ProfileContext'

export default function SurveyPage() {
  const router = useRouter()
  const { refetchProfiles } = useProfile()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    age: '',
    gender: 'MALE',
    height: '',
    weight: '',
    is_smoking: null,
    is_drinking: null,
    conditions: [],
    allergies: []
  })

  const handleSkip = () => {
    router.push('/main')
  }

  const handleSubmit = async () => {
    // 최종 데이터 검증
    const h = parseInt(formData.height);
    const w = parseFloat(formData.weight);

    if (formData.height && (h < 50 || h > 250)) {
      toast.error("키는 50cm ~ 250cm 사이로 입력해주세요.");
      return;
    }
    if (formData.weight && (w < 1 || w > 300)) {
      toast.error("몸무게는 1kg ~ 300kg 사이로 입력해주세요.");
      return;
    }

    setIsLoading(true)
    try {
      const healthSurvey = {
        age: parseInt(formData.age) || null,
        gender: formData.gender,
        height: h || null,
        weight: w || null,
        is_smoking: formData.is_smoking,
        is_drinking: formData.is_drinking,
        conditions: formData.conditions.length > 0 ? formData.conditions : null,
        allergies: formData.allergies.length > 0 ? formData.allergies : null,
      }

      const res = await api.get('/api/v1/profiles')
      const selfProfile = res.data.find(p => p.relation_type === 'SELF')

      if (selfProfile) {
        await api.patch(`/api/v1/profiles/${selfProfile.id}`, {
          health_survey: healthSurvey,
        })
      }

      toast.success('건강 프로필이 등록되었습니다!')
      if (refetchProfiles) await refetchProfiles()
      router.push('/main')
    } catch (err) {
      handleApiError(err)
      setIsLoading(false)
    }
  }

  const btnSelected = 'bg-gray-900 text-white border-gray-900 shadow-lg'
  const btnUnselected = 'bg-white text-gray-400 border-gray-100 hover:border-gray-200'
  const chipSelected = 'bg-gray-900 text-white border-gray-900 shadow-md'
  const chipUnselected = 'bg-white text-gray-500 border-gray-100 hover:border-gray-200'

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative">
      {/* 로딩 오버레이 */}
      {isLoading && (
        <div className="fixed inset-0 bg-white/60 backdrop-blur-sm z-[200] flex flex-col items-center justify-center animate-in fade-in duration-300">
          <div className="w-20 h-20 bg-gray-900 rounded-[32px] flex items-center justify-center shadow-2xl mb-6 animate-bounce">
            <ActivityIcon size={40} className="text-white animate-pulse" />
          </div>
          <p className="text-xl font-black text-gray-900">건강 프로필을 분석하고 있어요</p>
          <p className="text-gray-400 font-bold mt-2">잠시만 기다려 주세요...</p>
        </div>
      )}

      <div className={`max-w-2xl w-full bg-white rounded-[40px] shadow-2xl overflow-hidden border border-gray-100 transition-all duration-500 ${isLoading ? 'scale-95 opacity-50' : 'scale-100 opacity-100'}`}>
        {/* Header */}
        <div className="flex justify-between items-center p-8 border-b border-gray-50">
          <div>
            <h3 className="text-xl font-black text-gray-900">건강 정보 입력</h3>
            <p className="text-xs font-bold text-gray-400 mt-1">맞춤형 관리를 위해 정보를 입력해주세요</p>
          </div>
          <button onClick={handleSkip} className="flex items-center gap-1 text-xs font-black text-gray-400 hover:text-gray-900 transition-all">
            건너뛰기 <X size={14} />
          </button>
        </div>

        <div className="p-8 space-y-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
          {/* 1. 기본 정보 */}
          <div className="space-y-4">
            <h4 className="text-sm font-black text-gray-900 flex items-center gap-2">
              <User size={16} /> 기본 정보
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">나이</label>
                <input type="text" inputMode="numeric" value={formData.age} placeholder="예: 30"
                  onChange={(e) => setFormData({...formData, age: e.target.value.replace(/[^0-9]/g, '')})}
                  className="w-full px-5 py-3.5 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800 border-2 border-transparent focus:border-gray-900 transition-all text-sm" />
              </div>
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">성별</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map(g => (
                    <button key={g} onClick={() => setFormData({...formData, gender: g})}
                      className={`flex-1 py-3.5 rounded-2xl font-bold text-xs border-2 transition-all ${formData.gender === g ? btnSelected : btnUnselected}`}>
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 2. 신체 정보 */}
          <div className="space-y-4">
            <h4 className="text-sm font-black text-gray-900 flex items-center gap-2">
              <Activity size={16} /> 신체 정보
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">키 (cm)</label>
                <input type="text" inputMode="decimal" value={formData.height} placeholder="예: 170"
                  onChange={(e) => setFormData({...formData, height: e.target.value.replace(/[^0-9]/g, '')})}
                  className="w-full px-5 py-3.5 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800 border-2 border-transparent focus:border-gray-900 transition-all text-sm" />
              </div>
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">몸무게 (kg)</label>
                <input type="text" inputMode="decimal" value={formData.weight} placeholder="예: 65.5"
                  onChange={(e) => {
                    let val = e.target.value.replace(/[^0-9.]/g, '');
                    const parts = val.split('.');
                    if (parts.length > 2) val = parts[0] + '.' + parts.slice(1).join('');
                    setFormData({...formData, weight: val})
                  }}
                  className="w-full px-5 py-3.5 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800 border-2 border-transparent focus:border-gray-900 transition-all text-sm" />
              </div>
            </div>
          </div>

          {/* 3. 생활 습관 */}
          <div className="space-y-4">
            <h4 className="text-sm font-black text-gray-900 flex items-center gap-2">
              <Heart size={16} /> 생활 습관
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">흡연 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setFormData({...formData, is_smoking: v})}
                      className={`flex-1 py-3.5 rounded-2xl font-bold text-xs border-2 transition-all ${formData.is_smoking === v ? btnSelected : btnUnselected}`}>
                      {v ? '흡연' : '비흡연'}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-black text-gray-400 mb-1.5 block ml-1">음주 여부</label>
                <div className="flex gap-2">
                  {[true, false].map(v => (
                    <button key={String(v)} onClick={() => setFormData({...formData, is_drinking: v})}
                      className={`flex-1 py-3.5 rounded-2xl font-bold text-xs border-2 transition-all ${formData.is_drinking === v ? btnSelected : btnUnselected}`}>
                      {v ? '음주' : '비음주'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 4. 질환 및 알레르기 */}
          <div className="space-y-6">
            <div>
              <label className="text-xs font-black text-gray-400 mb-3 block ml-1">보유 질환</label>
              <div className="flex flex-wrap gap-2">
                {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map(item => (
                  <button key={item}
                    onClick={() => {
                      let updated
                      if (item === '없음') {
                        updated = formData.conditions.includes(item) ? [] : ['없음']
                      } else {
                        const withoutNone = formData.conditions.filter(c => c !== '없음')
                        updated = withoutNone.includes(item) ? withoutNone.filter(c => c !== item) : [...withoutNone, item]
                      }
                      setFormData({...formData, conditions: updated})
                    }}
                    className={`px-4 py-2 rounded-full text-[11px] font-black transition-all border-2 ${formData.conditions.includes(item) ? chipSelected : chipUnselected}`}>
                    {item}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 mb-3 block ml-1">알레르기</label>
              <div className="flex flex-wrap gap-2">
                {['페니실린', '아스피린', '항생제', '소염제', '없음'].map(item => (
                  <button key={item}
                    onClick={() => {
                      let updated
                      if (item === '없음') {
                        updated = formData.allergies.includes(item) ? [] : ['없음']
                      } else {
                        const withoutNone = formData.allergies.filter(a => a !== '없음')
                        updated = withoutNone.includes(item) ? withoutNone.filter(a => a !== item) : [...withoutNone, item]
                      }
                      setFormData({...formData, allergies: updated})
                    }}
                    className={`px-4 py-2 rounded-full text-[11px] font-black transition-all border-2 ${formData.allergies.includes(item) ? chipSelected : chipUnselected}`}>
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer Action */}
        <div className="p-8 bg-gray-50 border-t border-gray-100">
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full py-5 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all shadow-xl flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <div className="flex items-center gap-2"><Loader2 className="animate-spin" size={20} /> 처리 중...</div>
            ) : (
              <div className="flex items-center gap-2 text-lg">시작하기 <Check size={22} /></div>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
