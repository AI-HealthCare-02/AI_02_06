'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/layout/Header'
import api, { showError } from '@/lib/api'

export default function SurveyPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [existingProfile, setExistingProfile] = useState(null) // 기존 SELF 프로필
  const [accountNickname, setAccountNickname] = useState('') // 계정 닉네임

  const [form, setForm] = useState({
    age: '',
    gender: '',
    height: '',
    weight: '',
    is_smoking: null,
    is_drinking: null,
    conditions: [],
    allergies: [],
  })

  // 초기 데이터 로드
  useEffect(() => {
    const fetchData = async () => {
      try {
        // 프로필 목록 조회
        const profileRes = await api.get('/api/v1/profiles')
        const profiles = profileRes.data

        // SELF 프로필 찾기
        const selfProfile = profiles.find(p => p.relation_type === 'SELF')

        if (selfProfile) {
          setExistingProfile(selfProfile)
          setAccountNickname(selfProfile.name)

          // 기존 health_survey 데이터가 있으면 폼에 채우기
          if (selfProfile.health_survey) {
            const survey = selfProfile.health_survey
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
        }
      } catch (err) {
        console.error('프로필 로드 실패:', err)
        // 401은 api 인터셉터에서 처리
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleCancel = () => {
    if (window.confirm('작성 중인 내용이 사라집니다. 정말 나가시겠습니까?')) {
      router.push('/main')
    }
  }

  const handleSkip = () => {
    // 건너뛰기 - 프로필이 없으면 빈 프로필 생성
    if (!existingProfile) {
      createEmptyProfile()
    } else {
      router.push('/main')
    }
  }

  const createEmptyProfile = async () => {
    setIsSubmitting(true)
    try {
      await api.post('/api/v1/profiles', {
        relation_type: 'SELF',
        name: '나',
        health_survey: null,
      })
      router.push('/main')
    } catch (err) {
      console.error('프로필 생성 실패:', err)
      showError(err.parsed?.message || '프로필 생성에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmit = async () => {
    // 기본 유효성 검사
    if (!form.age || !form.gender) {
      showError('나이와 성별은 필수 입력입니다.')
      return
    }

    setIsSubmitting(true)

    // health_survey 데이터 구성
    const healthSurvey = {
      age: parseInt(form.age) || null,
      gender: form.gender || null,
      height: parseInt(form.height) || null,
      weight: parseFloat(form.weight) || null,
      is_smoking: form.is_smoking,
      is_drinking: form.is_drinking,
      conditions: form.conditions.length > 0 ? form.conditions : null,
      allergies: form.allergies.length > 0 ? form.allergies : null,
    }

    try {
      if (existingProfile) {
        // 기존 프로필 수정
        await api.patch(`/api/v1/profiles/${existingProfile.id}`, {
          health_survey: healthSurvey,
        })
      } else {
        // 새 프로필 생성
        await api.post('/api/v1/profiles', {
          relation_type: 'SELF',
          name: accountNickname || '나',
          health_survey: healthSurvey,
        })
      }

      router.push('/main')
    } catch (err) {
      console.error('설문 저장 실패:', err)
      showError(err.parsed?.message || '설문 저장에 실패했습니다.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 pb-12">
        <Header title="건강 정보 입력" subtitle="맞춤 안내를 위한 기본 정보" showBack={true} />
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="animate-pulse space-y-6">
            <div className="bg-white rounded-2xl h-48 w-full" />
            <div className="bg-white rounded-2xl h-32 w-full" />
            <div className="bg-white rounded-2xl h-48 w-full" />
          </div>
        </div>
      </main>
    )
  }

  const selectedClass = 'bg-gray-900 text-white border-gray-900'
  const unselectedClass = 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  return (
    <main className="min-h-screen bg-gray-50 pb-12">
      <Header
        title="건강 정보 입력"
        subtitle={existingProfile ? '정보를 수정할 수 있습니다' : '맞춤 안내를 위한 기본 정보'}


        showBack={true}
        onBack={handleCancel}
      />

      <div className="max-w-3xl mx-auto px-6 py-8">

        {/* 기본 정보 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6 border border-gray-100">
          <h2 className="font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
            기본 정보
            <span className="text-red-400 text-xs ml-1">*필수</span>
          </h2>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">나이 *</label>
                <input type="number" placeholder="세"
                  min={1} max={120} step={1}
                  value={form.age}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 1 && parseInt(val) <= 120)) {
                      setForm({...form, age: val})
                    }
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">성별 *</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map((g) => (
                    <button key={g}
                      type="button"
                      onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer
                        ${form.gender === g ? selectedClass : unselectedClass}`}
                    >
                      {g === 'MALE' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">키 (cm)</label>
                <input type="number" placeholder="cm"
                  min={50} max={250} step={1}
                  value={form.height}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseInt(val) >= 50 && parseInt(val) <= 250)) {
                      setForm({...form, height: val})
                    }
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">몸무게 (kg)</label>
                <input type="number" placeholder="kg"
                  min={1} max={300} step={0.1}
                  value={form.weight}
                  onChange={(e) => {
                    const val = e.target.value
                    if (val === '' || (parseFloat(val) >= 1 && parseFloat(val) <= 300)) {
                      setForm({...form, weight: val})
                    }
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-colors"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 생활 습관 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6 border border-gray-100">
          <h2 className="font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
            생활 습관
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">흡연 여부</label>
              <div className="flex gap-2">
                {[true, false].map((val) => (
                  <button key={String(val)}
                    type="button"
                    onClick={() => setForm({...form, is_smoking: val})}
                    className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer
                      ${form.is_smoking === val ? selectedClass : unselectedClass}`}
                  >
                    {val ? '예' : '아니오'}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">음주 여부</label>
              <div className="flex gap-2">
                {[true, false].map((val) => (
                  <button key={String(val)}
                    type="button"
                    onClick={() => setForm({...form, is_drinking: val})}
                    className={`flex-1 py-3 rounded-xl text-sm font-bold border transition-all cursor-pointer
                      ${form.is_drinking === val ? selectedClass : unselectedClass}`}
                  >
                    {val ? '예' : '아니오'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 질환 및 알레르기 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-8 border border-gray-100">
          <h2 className="font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
            질환 및 알레르기
          </h2>
          <div className="space-y-6">
            <div>
              <label className="text-gray-400 text-xs font-bold mb-3 block px-1">기저질환 (중복 선택 가능)</label>
              <div className="flex flex-wrap gap-2">
                {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map((item) => (
                  <button key={item}
                    type="button"
                    onClick={() => {
                      let updated
                      if (item === '없음') {
                        // '없음' 선택 시 다른 항목 모두 해제
                        updated = form.conditions.includes(item) ? [] : ['없음']
                      } else {
                        // 다른 항목 선택 시 '없음' 해제
                        const withoutNone = form.conditions.filter(c => c !== '없음')
                        updated = withoutNone.includes(item)
                          ? withoutNone.filter(c => c !== item)
                          : [...withoutNone, item]
                      }
                      setForm({...form, conditions: updated})
                    }}
                    className={`px-4 py-2 rounded-full text-xs font-bold transition-all border cursor-pointer
                      ${form.conditions.includes(item) ? chipSelected : chipUnselected}`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-gray-400 text-xs font-bold mb-3 block px-1">알레르기 (중복 선택 가능)</label>
              <div className="flex flex-wrap gap-2">
                {['페니실린', '아스피린', '항생제', '소염제', '없음'].map((item) => (
                  <button key={item}
                    type="button"
                    onClick={() => {
                      let updated
                      if (item === '없음') {
                        updated = form.allergies.includes(item) ? [] : ['없음']
                      } else {
                        const withoutNone = form.allergies.filter(a => a !== '없음')
                        updated = withoutNone.includes(item)
                          ? withoutNone.filter(a => a !== item)
                          : [...withoutNone, item]
                      }
                      setForm({...form, allergies: updated})
                    }}
                    className={`px-4 py-2 rounded-full text-xs font-bold transition-all border cursor-pointer
                      ${form.allergies.includes(item) ? chipSelected : chipUnselected}`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 하단 버튼 */}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleSkip}
            disabled={isSubmitting}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold hover:bg-gray-50 transition-all active:scale-[0.98] duration-150 disabled:opacity-50"


          >
            건너뛰기
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex-1 bg-blue-500 text-white py-4 rounded-xl text-sm font-bold shadow-sm hover:bg-blue-600 active:scale-[0.95] transition-all duration-150 disabled:opacity-50 disabled:cursor-wait"


          >
            {isSubmitting ? '저장 중...' : existingProfile ? '수정 완료' : '입력 완료'}
          </button>
        </div>
      </div>
    </main>
  )
}
