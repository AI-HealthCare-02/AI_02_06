'use client'
import { useState, useEffect } from 'react'  // ← useEffect 추가
import { useRouter } from 'next/navigation'

function MainSkeleton() {
  return (
    <main className="min-h-screen bg-gray-50 pb-20 animate-pulse">
      <div className="bg-white border-b border-gray-200 px-10 py-5">
        <div className="h-3 w-40 bg-gray-200 rounded mb-2" />
        <div className="h-5 w-32 bg-gray-200 rounded" />
      </div>
      <div className="px-10 py-6 grid grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-6 col-span-2 row-span-2 h-64" />
        <div className="bg-gray-200 rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
        <div className="bg-white rounded-2xl h-32" />
      </div>
    </main>
  )
}

export default function MainPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)  // ← 추가

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 1000)  // ← 추가 (초 후 로딩 끝)
  }, [])

  if (isLoading) return <MainSkeleton />  // ← 추가

  const todayMeds = [
    { time: '08:00', name: '혈압약', done: true },
    { time: '13:00', name: '당뇨약', done: true },
    { time: '19:00', name: '비타민', done: false },
  ]

  const challenge = { title: '금연 챌린지', days: 3, target: 30 }
  const recentPrescription = { date: '2024.03.31', hospital: '내과' }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 12) return { msg: '좋은 아침이에요! ☀️', sub: '오늘 하루도 건강하게 시작해봐요' }
    if (hour >= 12 && hour < 17) return { msg: '좋은 오후예요! 🌤️', sub: '점심 식사 후 약 챙기셨나요?' }
    if (hour >= 17 && hour < 21) return { msg: '좋은 저녁이에요! 🌇', sub: '저녁 복약 시간을 확인해보세요' }
    return { msg: '잠들기 전 확인해요! 🌙', sub: '오늘 복약을 모두 완료했나요?' }
  }

  const greeting = getGreeting()

  return (
    <main className="min-h-screen bg-gray-50 pb-20">
      <div className="bg-white border-b border-gray-200 px-10 py-5">
        <p className="text-gray-400 text-sm mb-1">{greeting.sub}</p>
        <h1 className="text-xl font-bold">{greeting.msg} 홍길동님</h1>
      </div>
      <div className="px-10 py-6 grid grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl shadow-sm p-6 col-span-2 row-span-2">
          <div className="flex justify-between items-center mb-4 pb-3 border-b border-gray-100">
            <h2 className="font-bold">오늘 복약 현황</h2>
            <span className="text-blue-500 text-sm font-semibold">2/3 완료</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2 mb-6">
            <div className="bg-blue-500 h-2 rounded-full" style={{width: '66%'}} />
          </div>
          <div className="space-y-3">
            {todayMeds.map((med, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-gray-50">
                <div className="flex items-center gap-4">
                  <span className="text-gray-400 text-sm w-12">{med.time}</span>
                  <span className={`text-sm font-semibold ${med.done ? 'text-gray-400 line-through' : 'text-black'}`}>
                    💊 {med.name}
                  </span>
                </div>
                <span className={`text-xs px-3 py-1 rounded-full ${med.done ? 'bg-green-50 text-green-500' : 'bg-blue-50 text-blue-500'}`}>
                  {med.done ? '완료' : '예정'}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div onClick={() => router.push('/chat')} className="bg-blue-500 rounded-2xl p-6 text-white cursor-pointer hover:bg-blue-600">
          <p className="text-xs mb-2 opacity-80">궁금한 게 있으신가요?</p>
          <h2 className="font-bold">💊 복약 AI 상담하기</h2>
          <p className="text-xs mt-3 opacity-60">약 복용 방법, 부작용 등</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="font-bold mb-2">처방전 등록</h2>
          <button onClick={() => router.push('/ocr')} className="w-full border-2 border-dashed border-gray-200 py-3 rounded-xl text-gray-400 text-sm cursor-pointer hover:border-blue-300 mt-2">
            + 업로드
          </button>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="font-bold mb-3">챌린지 현황</h2>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">🏆</span>
            <span className="font-semibold text-sm">{challenge.title}</span>
          </div>
          <p className="text-gray-400 text-xs mb-2">{challenge.days}일째 진행 중!</p>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div className="bg-yellow-400 h-1.5 rounded-full" style={{width: `${(challenge.days/challenge.target)*100}%`}} />
          </div>
          <p className="text-xs text-gray-400 mt-1">{challenge.days}/{challenge.target}일</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="font-bold mb-3">최근 처방전</h2>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">{recentPrescription.hospital}</p>
              <p className="text-xs text-gray-400 mt-1">{recentPrescription.date}</p>
            </div>
            <span className="text-xs text-blue-500 cursor-pointer">보기</span>
          </div>
        </div>
      </div>
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
        <button onClick={() => router.push('/main')} className="flex-1 py-4 text-blue-500 text-sm font-semibold">홈</button>
        <button onClick={() => router.push('/mypage')} className="flex-1 py-4 text-gray-400 text-sm">마이페이지</button>
      </div>
    </main>
  )
}