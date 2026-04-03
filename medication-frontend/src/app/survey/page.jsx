'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function SurveyPage() {
  const router = useRouter()

  const [form, setForm] = useState({
    age: '',
    gender: '',
    height: '',
    weight: '',
    is_smoking: null,
    is_drinking: null,
    exercise_freq: '',
    conditions: [],
    allergies: [],
  })

  const handleSubmit = () => {
    console.log('제출 데이터:', form)
    router.push('/main')
  }

  return (
    <main className="max-w-lg mx-auto p-6 mt-10 mb-20">
      <h1 className="text-2xl font-bold mb-2">건강 정보 입력</h1>
      <p className="text-gray-400 text-sm mb-8">
        맞춤 복약 안내를 위해 건강 정보를 입력해주세요
      </p>

      {/* 기본 정보 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <h2 className="font-bold mb-4">기본 정보</h2>
        <div className="space-y-4">
          <div>
            <label className="text-gray-400 text-sm">나이</label>
            <input type="number" placeholder="나이를 입력하세요"
              value={form.age}
              onChange={(e) => setForm({...form, age: e.target.value})}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 mt-1 text-sm"
            />
          </div>
          <div>
            <label className="text-gray-400 text-sm">키 (cm)</label>
            <input type="number" placeholder="키를 입력하세요"
              value={form.height}
              onChange={(e) => setForm({...form, height: e.target.value})}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 mt-1 text-sm"
            />
          </div>
          <div>
            <label className="text-gray-400 text-sm">몸무게 (kg)</label>
            <input type="number" placeholder="몸무게를 입력하세요"
              value={form.weight}
              onChange={(e) => setForm({...form, weight: e.target.value})}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 mt-1 text-sm"
            />
          </div>
        </div>
      </div>

      {/* 성별 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <h2 className="font-bold mb-4">성별</h2>
        <div className="flex gap-3">
          {['MALE', 'FEMALE'].map((g) => (
            <button key={g}
              onClick={() => setForm({...form, gender: g})}
              className={`flex-1 py-3 rounded-xl text-sm font-semibold cursor-pointer border
                ${form.gender === g
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-400 border-gray-200'
                }`}
            >
              {g === 'MALE' ? '남성' : '여성'}
            </button>
          ))}
        </div>
      </div>

      {/* 생활 습관 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <h2 className="font-bold mb-4">생활 습관</h2>
        <div className="space-y-4">
          <div>
            <label className="text-gray-400 text-sm">흡연 여부</label>
            <div className="flex gap-3 mt-2">
              {[true, false].map((val) => (
                <button key={String(val)}
                  onClick={() => setForm({...form, is_smoking: val})}
                  className={`flex-1 py-3 rounded-xl text-sm font-semibold cursor-pointer border
                    ${form.is_smoking === val
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-400 border-gray-200'
                    }`}
                >
                  {val ? '예' : '아니오'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-gray-400 text-sm">음주 여부</label>
            <div className="flex gap-3 mt-2">
              {[true, false].map((val) => (
                <button key={String(val)}
                  onClick={() => setForm({...form, is_drinking: val})}
                  className={`flex-1 py-3 rounded-xl text-sm font-semibold cursor-pointer border
                    ${form.is_drinking === val
                      ? 'bg-blue-500 text-white border-blue-500'
                      : 'bg-white text-gray-400 border-gray-200'
                    }`}
                >
                  {val ? '예' : '아니오'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 기저질환 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <h2 className="font-bold mb-1">기저질환</h2>
        <p className="text-gray-400 text-xs mb-4">해당하는 것을 모두 선택해주세요</p>
        <div className="flex flex-wrap gap-2">
          {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map((item) => (
            <button key={item}
              onClick={() => {
                const updated = form.conditions.includes(item)
                  ? form.conditions.filter(c => c !== item)
                  : [...form.conditions, item]
                setForm({...form, conditions: updated})
              }}
              className={`px-4 py-2 rounded-full text-sm cursor-pointer border
                ${form.conditions.includes(item)
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-400 border-gray-200'
                }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {/* 알레르기 */}
      <div className="bg-white rounded-2xl shadow-sm p-6 mb-4">
        <h2 className="font-bold mb-1">알레르기</h2>
        <p className="text-gray-400 text-xs mb-4">해당하는 것을 모두 선택해주세요</p>
        <div className="flex flex-wrap gap-2">
          {['페니실린', '아스피린', '항생제', '소염제', '없음'].map((item) => (
            <button key={item}
              onClick={() => {
                const updated = form.allergies.includes(item)
                  ? form.allergies.filter(a => a !== item)
                  : [...form.allergies, item]
                setForm({...form, allergies: updated})
              }}
              className={`px-4 py-2 rounded-full text-sm cursor-pointer border
                ${form.allergies.includes(item)
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-white text-gray-400 border-gray-200'
                }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {/* 버튼 */}
<div className="flex gap-3 mt-6">
  <button
    onClick={() => router.push('/main')}
    className="flex-1 border border-gray-200 py-4 rounded-xl text-gray-400 text-sm cursor-pointer hover:bg-gray-50"
  >
    건너뛰기
  </button>
  <button
    onClick={handleSubmit}
    className="flex-1 bg-blue-500 text-white py-4 rounded-xl font-semibold cursor-pointer hover:bg-blue-600"
  >
    완료
  </button>
</div>

    </main>
  )
}