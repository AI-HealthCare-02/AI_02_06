'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { User, Activity, Users, Home, Trash2 } from 'lucide-react'
import EmptyState from '../../components/EmptyState'

function MyPageSkeleton() {
  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 animate-pulse">
      <div className="flex justify-between items-end mb-10 bg-white p-8 rounded-[32px]">
        <div className="h-10 w-48 bg-gray-200 rounded-xl" />
        <div className="flex gap-8">
          <div className="h-6 w-20 bg-gray-200 rounded" />
          <div className="h-6 w-20 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-4 space-y-6">
          <div className="bg-white rounded-[32px] h-64 w-full" />
          <div className="bg-white rounded-[32px] h-80 w-full" />
        </div>
        <div className="md:col-span-8 bg-white rounded-[32px] h-[600px] w-full" />
      </div>
    </main>
  )
}

export default function MyPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [activeMenu, setActiveMenu] = useState('기본정보')

  const [family] = useState([
    { id: 1, name: '정순희', relation: '어머니' }
  ])

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800)
  }, [])

  if (isLoading) return <MyPageSkeleton />

  const menuItems = [
    { id: '기본정보', label: '기본 정보', icon: <User size={18} /> },
    { id: '건강정보', label: '건강 정보', icon: <Activity size={18} /> },
    { id: '가족관리', label: '가족 관리', icon: <Users size={18} /> },
  ]

  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative overflow-x-hidden">

      {/* 상단 헤더 */}
      <div className="flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-gray-100">
        <div>
          <p className="text-gray-400 text-sm font-bold mb-2 px-1">내 설정 및 관리</p>
          <h1 className="text-4xl font-black text-gray-900 leading-tight">마이페이지</h1>
        </div>
        <div className="hidden md:flex items-center gap-10 mb-2">
          <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-gray-400 font-bold text-base hover:text-gray-900 transition-all cursor-pointer">
            <Home size={18} /> 홈
          </button>
          <button onClick={() => router.push('/mypage')} className="flex items-center gap-2 text-gray-900 font-black text-base cursor-pointer">
            <User size={18} /> 마이페이지
          </button>
        </div>
      </div>

      {/* 2단 레이아웃 */}
      <div className="grid md:grid-cols-12 gap-8">

        {/* 좌측: 프로필 + 메뉴 */}
        <div className="md:col-span-4 flex flex-col space-y-6">

          {/* 프로필 카드 */}
          <div className="bg-white rounded-[40px] shadow-sm p-8 border border-gray-100">
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-gray-900 rounded-full flex items-center justify-center shadow-lg mb-4 border-4 border-white">
                <User size={40} className="text-white" />
              </div>
              <h2 className="text-xl font-black text-gray-900 mb-1">홍길동님</h2>
              <p className="text-gray-400 text-xs font-bold mb-6">jw@gmail.com</p>

              <div className="grid grid-cols-2 gap-3 w-full">
                <div className="bg-gray-50 p-4 rounded-[24px] border border-gray-100">
                  <p className="text-[10px] font-black text-gray-500 mb-1">연속 복약</p>
                  <p className="text-lg font-black text-gray-800">3일째</p>
                </div>
                <div className="bg-orange-50 p-4 rounded-[24px] border border-orange-100">
                  <p className="text-[10px] font-black text-orange-500 mb-1">진행 챌린지</p>
                  <p className="text-lg font-black text-gray-800">1개</p>
                </div>
              </div>
            </div>
          </div>

          {/* 세로 메뉴 */}
          <div className="bg-white rounded-[40px] shadow-sm p-4 border border-gray-100">
            <nav className="flex flex-col space-y-2">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveMenu(item.id)}
                  className={`flex items-center gap-4 px-6 py-4 rounded-[24px] transition-all duration-200 active:scale-[0.98] cursor-pointer
                    ${activeMenu === item.id
                      ? 'bg-gray-900 text-white font-black shadow-lg'
                      : 'text-gray-500 hover:bg-gray-50 font-bold'}`}
                >
                  <span>{item.icon}</span>
                  <span className="text-sm">{item.label}</span>
                  {activeMenu === item.id && (
                    <span className="ml-auto w-1.5 h-1.5 bg-white rounded-full" />
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 우측: 콘텐츠 */}
        <div className="md:col-span-8">
          <div className="bg-white rounded-[40px] shadow-sm p-10 border border-gray-100 h-full min-h-[600px]">

            {activeMenu === '기본정보' && (
              <div className="space-y-8 h-full flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">계정 정보</h3>
                  <button className="text-xs font-bold text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer">
                    정보 수정
                  </button>
                </div>

                <div className="space-y-4">
                  {[
                    { label: '닉네임', value: '홍길동' },
                    { label: '이메일 주소', value: 'jw@gmail.com' },
                  ].map((row) => (
                    <div key={row.label} className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px] border border-transparent hover:border-gray-100 transition-all">
                      <span className="text-sm text-gray-400 font-black">{row.label}</span>
                      <span className="text-base font-black text-gray-800">{row.value}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px] border border-transparent hover:border-gray-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">로그인 방식</span>
                    <div className="flex items-center gap-2 bg-yellow-400/10 px-3 py-1.5 rounded-full border border-yellow-400/20">
                      <span className="w-5 h-5 bg-yellow-400 rounded-full flex items-center justify-center text-[10px] font-black">K</span>
                      <span className="text-sm font-black text-yellow-700 uppercase tracking-tighter">Kakao</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto pt-10 flex gap-4">
                  <button className="flex-1 bg-white border-2 border-gray-100 text-gray-400 py-5 rounded-[28px] text-sm font-black hover:bg-gray-50 hover:text-gray-600 transition-all active:scale-[0.98] cursor-pointer">
                    로그아웃
                  </button>
                  <button className="text-gray-300 text-xs font-bold px-6 hover:text-red-400 transition-all cursor-pointer">
                    회원탈퇴
                  </button>
                </div>
              </div>
            )}

            {activeMenu === '건강정보' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">나의 건강 프로필</h3>
                  <button className="text-xs font-black text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer">
                    수정하기
                  </button>
                </div>
                <div className="grid sm:grid-cols-2 gap-6">
                  {[
                    { label: '나이', value: '25세' },
                    { label: '키 / 몸무게', value: '163cm / 55kg' },
                    { label: '보유 질환', value: '고혈압' },
                    { label: '특이 알레르기', value: '페니실린' },
                  ].map((item) => (
                    <div key={item.label} className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">{item.label}</p>
                      <p className="text-xl font-black text-gray-800">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeMenu === '가족관리' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">함께 관리하는 가족</h3>
                  <button className="bg-gray-900 text-white px-6 py-3 rounded-2xl text-sm font-black hover:bg-gray-700 transition-all active:scale-[0.95] cursor-pointer">
                    + 가족 추가하기
                  </button>
                </div>

                {family.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {family.map((member) => (
                      <div key={member.id} className="bg-slate-50 rounded-[32px] p-8 border border-transparent hover:border-gray-200 hover:bg-white hover:shadow-md transition-all flex justify-between items-center group">
                        <div className="flex items-center gap-5">
                          <div className="w-16 h-16 bg-white rounded-[24px] flex items-center justify-center text-2xl font-black text-gray-700 shadow-sm group-hover:bg-gray-900 group-hover:text-white transition-all duration-300">
                            {member.name[0]}
                          </div>
                          <div>
                            <p className="text-lg font-black text-gray-800">{member.name}</p>
                            <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-widest">{member.relation}</p>
                          </div>
                        </div>
                        <button className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all shadow-sm cursor-pointer">
                          <Trash2 size={18} />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-20 bg-slate-50 rounded-[40px] border border-dashed border-slate-200">
                    <EmptyState
                      title="등록된 가족이 없어요"
                      message="가족의 복약도 함께 관리해보세요!"
                      actionLabel="가족 추가하기"
                      onAction={() => {}}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 모바일 하단 네비게이션 */}
      <div className="md:hidden fixed bottom-0 left-0 w-full bg-white/90 backdrop-blur-lg border-t border-gray-100 flex py-5 px-8 z-40 shadow-[0_-5px_30px_rgba(0,0,0,0.06)] rounded-t-[40px]">
        <button onClick={() => router.push('/main')} className="flex-1 flex flex-col items-center gap-2 group cursor-pointer">
          <span className="group-active:scale-90 transition-transform opacity-40 group-hover:opacity-100">
            <Home size={22} />
          </span>
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Home</span>
        </button>
        <button onClick={() => router.push('/mypage')} className="flex-1 flex flex-col items-center gap-2 group cursor-pointer">
          <span className="group-active:scale-90 transition-transform text-gray-900">
            <User size={22} />
          </span>
          <span className="text-[10px] font-black text-gray-900 uppercase tracking-widest">My</span>
        </button>
      </div>
    </main>
  )
}
