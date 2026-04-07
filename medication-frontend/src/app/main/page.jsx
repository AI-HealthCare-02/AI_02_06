'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Pill, FileText, Flame, Ban, X, Check, Plus } from 'lucide-react'

function MainSkeleton() {
  return (
    <main className="max-w-7xl mx-auto w-full px-6 py-12 min-h-screen animate-pulse">
      <div className="h-40 w-full bg-gray-100 rounded-[40px] mb-10" />
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-8 bg-gray-100 rounded-[40px] h-[500px]" />
        <div className="md:col-span-4 space-y-8">
          <div className="bg-gray-100 rounded-[40px] h-60" />
          <div className="bg-gray-100 rounded-[40px] h-60" />
        </div>
      </div>
    </main>
  )
}

// 설문 모달 (메인 전용)
function SurveyModal({ onClose }) {
  const [form, setForm] = useState({
    gender: '',
  })

  return (
    <div className="fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6 backdrop-blur-sm">
      <div className="bg-white rounded-[32px] w-full max-w-md max-h-[90vh] overflow-y-auto shadow-2xl animate-in zoom-in-95 duration-300">
        <div className="flex justify-between items-center p-8 border-b border-gray-50 sticky top-0 bg-white z-10">
          <div>
            <h2 className="font-black text-2xl text-gray-900 leading-tight">건강 정보 입력</h2>
            <p className="text-gray-400 text-sm mt-1">맞춤 복약 가이드를 제공해 드릴게요</p>
          </div>
          <button onClick={onClose} className="text-gray-300 hover:text-black cursor-pointer p-2 transition-colors"><X size={20} /></button>
        </div>
        <div className="p-8 space-y-8">
          <div>
            <h3 className="font-bold mb-4 text-gray-800">기본 정보</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-gray-400 text-xs font-bold px-1 uppercase tracking-wider">나이</label>
                <input type="number" placeholder="만 나이"
                  className="w-full bg-gray-50 border border-gray-100 rounded-2xl px-4 py-3 text-sm focus:border-blue-500 outline-none transition-all" />
              </div>
              <div className="space-y-2">
                <label className="text-gray-400 text-xs font-bold px-1 uppercase tracking-wider">성별</label>
                <div className="flex gap-2">
                  {['M', 'F'].map(g => (
                    <button key={g} onClick={() => setForm({...form, gender: g})}
                      className={`flex-1 py-3 rounded-2xl text-xs font-black transition-all border
                        ${form.gender === g ? 'bg-blue-600 text-white border-blue-600 shadow-md shadow-blue-100' : 'bg-white text-gray-400 border-gray-100 hover:border-gray-200'}`}>
                      {g === 'M' ? '남성' : '여성'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="pt-4 border-t border-gray-50 flex gap-4">
            <button onClick={onClose} className="flex-1 border border-gray-100 py-4 rounded-2xl text-gray-400 font-bold hover:bg-gray-50 transition-all cursor-pointer">다음에 할게요</button>
            <button onClick={onClose} className="flex-1 bg-blue-600 text-white py-4 rounded-2xl font-black shadow-lg shadow-blue-100 hover:bg-blue-700 transition-all cursor-pointer">저장하기</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function MainPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [showSurvey, setShowSurvey] = useState(false)

  useEffect(() => {
    setTimeout(() => {
      setIsLoading(false)
      // setShowSurvey(true) // 필요 시 활성화
    }, 800)
  }, [])

  if (isLoading) return <MainSkeleton />

  const todayMeds = [
    { time: '08:00', name: '혈압약', done: true },
    { time: '13:00', name: '당뇨약', done: true },
    { time: '19:00', name: '비타민', done: false },
  ]
  const challenge = { title: '금연 챌린지', days: 3, target: 30 }
  
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 12) return { msg: '좋은 아침이에요!', sub: '오늘 하루도 건강하게 시작해봐요' }
    if (hour >= 12 && hour < 17) return { msg: '좋은 오후예요!', sub: '점심 식사 후 약 챙기셨나요?' }
    if (hour >= 17 && hour < 21) return { msg: '좋은 저녁이에요!', sub: '저녁 복약 시간을 확인해보세요' }
    return { msg: '잠들기 전 확인해요!', sub: '오늘 복약을 모두 완료했나요?' }
  }
  const greeting = getGreeting()

  return (
    <>
      {showSurvey && <SurveyModal onClose={() => setShowSurvey(false)} />}

      <main className="max-w-7xl mx-auto w-full px-6 py-12 min-h-screen">
        
        {/* 히어로 인사말 (대시보드 상단) */}
        <section className="mb-12 bg-white p-10 md:p-14 rounded-[40px] shadow-sm border border-gray-50 relative overflow-hidden group">
          <div className="absolute -right-20 -top-20 w-80 h-80 bg-blue-50 rounded-full opacity-30 group-hover:scale-110 transition-transform duration-700" />
          <div className="relative z-10">
            <p className="text-blue-600 font-black text-sm mb-4 uppercase tracking-[0.2em]">{greeting.sub}</p>
            <h1 className="text-4xl md:text-5xl font-black text-gray-900 leading-tight">
              {greeting.msg} <br/>
              <span className="text-gray-400">홍길동님,</span> 반가워요
            </h1>
          </div>
        </section>

        {/* 대시보드 그리드 */}
        <div className="grid md:grid-cols-12 gap-8 items-start">
          
          {/* 복약 현황 (메인 섹션) */}
          <section className="md:col-span-8 bg-white rounded-[40px] shadow-sm p-10 border border-gray-50 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-center mb-10">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-50 rounded-2xl flex items-center justify-center">
                  <Pill size={22} className="text-blue-500" />
                </div>
                <h2 className="text-2xl font-black text-gray-900 tracking-tight">오늘 복약 현황</h2>
              </div>
              <div className="flex flex-col items-end">
                <span className="text-sm font-black text-blue-600 mb-1">66% 달성</span>
                <span className="text-[10px] text-gray-400 font-bold">2/3 복용 완료</span>
              </div>
            </div>

            {/* 프로그레스 바 */}
            <div className="w-full bg-gray-50 rounded-full h-4 mb-12 overflow-hidden border border-gray-100">
              <div className="bg-gradient-to-r from-blue-600 to-blue-400 h-full rounded-full transition-all duration-1000" style={{width: '66%'}} />
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {todayMeds.map((med, i) => (
                <div key={i} 
                  onClick={() => router.push('/medication')}
                  className={`group relative p-8 rounded-[32px] transition-all border cursor-pointer active:scale-95
                    ${med.done 
                      ? 'bg-gray-50 border-gray-50 opacity-60' 
                      : 'bg-white border-gray-100 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-50/50'}`}>
                  <div className="flex justify-between items-start mb-6">
                    <span className="text-xs font-black text-gray-400">{med.time}</span>
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all
                      ${med.done ? 'bg-green-500 text-white shadow-sm' : 'bg-gray-50 text-gray-300 group-hover:bg-blue-600 group-hover:text-white'}`}>
                      {med.done ? <Check size={14} /> : <Plus size={14} />}
                    </div>
                  </div>
                  <h3 className={`text-xl font-black transition-all ${med.done ? 'text-gray-400 line-through' : 'text-gray-900 group-hover:text-blue-600'}`}>
                    {med.name}
                  </h3>
                </div>
              ))}
            </div>
          </section>

          {/* 사이드 액션 섹션 */}
          <div className="md:col-span-4 space-y-8">
            {/* 처방전 등록 (강조) */}
            <div onClick={() => router.push('/ocr')}
              className="group bg-gray-900 rounded-[40px] p-10 text-white shadow-2xl shadow-gray-200 cursor-pointer hover:-translate-y-2 transition-all duration-300 relative overflow-hidden min-h-[240px] flex flex-col justify-end">
              <div className="absolute -right-6 -top-6 opacity-5 group-hover:rotate-12 transition-transform">
                <FileText size={140} className="text-white" />
              </div>
              <div>
                <p className="text-blue-400 font-black text-xs mb-4 uppercase tracking-widest">Prescription</p>
                <h2 className="text-3xl font-black leading-tight mb-4">처방전<br/>간편 등록하기</h2>
                <div className="flex items-center gap-2 text-sm font-bold opacity-60 group-hover:opacity-100 transition-opacity">
                  카메라로 찍어보세요 <span className="text-xl">→</span>
                </div>
              </div>
            </div>

            {/* 챌린지 카드 */}
            <div onClick={() => router.push('/challenge')}
              className="bg-white rounded-[40px] p-10 border border-gray-50 shadow-sm hover:shadow-md transition-all cursor-pointer group">
              <div className="flex justify-between items-center mb-8">
                <h2 className="text-xl font-black text-gray-900">진행 중 챌린지</h2>
                <div className="w-10 h-10 bg-orange-50 rounded-2xl flex items-center justify-center group-hover:animate-bounce">
                  <Flame size={18} className="text-orange-500" />
                </div>
              </div>
              <div className="flex items-center gap-5 mb-8">
                <div className="w-14 h-14 bg-gray-50 rounded-[20px] flex items-center justify-center shadow-inner group-hover:bg-white transition-colors">
                  <Ban size={22} className="text-gray-400" />
                </div>
                <div>
                  <h3 className="font-black text-gray-900">{challenge.title}</h3>
                  <p className="text-sm text-orange-500 font-bold">{challenge.days}일째 연속 성공 중!</p>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <div className="bg-orange-500 h-full rounded-full transition-all duration-1000" style={{width: '15%'}} />
              </div>
            </div>
          </div>

        </div>
      </main>
    </>
  )
}
