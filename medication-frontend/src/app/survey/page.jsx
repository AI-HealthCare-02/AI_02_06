'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'

export default function SurveyPage() {
  const router = useRouter()

  const handleCancel = () => {
    if (window.confirm('작성 중인 내용이 사라집니다. 정말 나가시겠습니까?')) {
      router.push('/main')
    }
  }

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

  const handleSubmit = () => {
    console.log('제출 데이터:', form)
    router.push('/main')
  }

  const selectedClass = 'bg-gray-900 text-white border-gray-900'
  const unselectedClass = 'bg-white text-gray-400 border-gray-200 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  return (
    <main className="min-h-screen bg-gray-50 pb-12">
      <Header
        title="건강 정보 입력"
        subtitle="맞춤 안내를 위한 기본 정보"
        showBack={true}
        onBack={handleCancel}
      />

      <div className="max-w-3xl mx-auto px-6 py-8">

        {/* 기본 정보 */}
        <div className="bg-white rounded-2xl shadow-sm p-6 mb-6 border border-gray-100">
          <h2 className="font-bold text-gray-900 mb-6 flex items-center gap-2">
            <span className="w-1 h-4 bg-gray-900 rounded-full"></span>
            기본 정보
          </h2>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">나이</label>
                <input type="number" placeholder="세"
                  value={form.age}
                  onChange={(e) => setForm({...form, age: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">성별</label>
                <div className="flex gap-2">
                  {['MALE', 'FEMALE'].map((g) => (
                    <button key={g}
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
                  value={form.height}
                  onChange={(e) => setForm({...form, height: e.target.value})}
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:border-gray-400 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="text-gray-400 text-xs font-bold mb-1.5 block px-1">몸무게 (kg)</label>
                <input type="number" placeholder="kg"
                  value={form.weight}
                  onChange={(e) => setForm({...form, weight: e.target.value})}
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
                    onClick={() => {
                      const updated = form.conditions.includes(item)
                        ? form.conditions.filter(c => c !== item)
                        : [...form.conditions, item]
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
                    onClick={() => {
                      const updated = form.allergies.includes(item)
                        ? form.allergies.filter(a => a !== item)
                        : [...form.allergies, item]
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
            onClick={handleCancel}
            className="flex-1 bg-white border border-gray-200 py-4 rounded-xl text-gray-500 text-sm font-bold hover:bg-gray-50 transition-all active:scale-[0.98] cursor-pointer"
          >
            건너뛰기
          </button>
          <button
            onClick={handleSubmit}
            className="flex-1 bg-gray-900 text-white py-4 rounded-xl text-sm font-bold hover:bg-gray-700 active:scale-[0.95] transition-all cursor-pointer"
          >
            입력 완료
          </button>
        </div>
      </div>
    </main>
  )
}
