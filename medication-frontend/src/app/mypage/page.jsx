'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
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
  
  // 예시 데이터
  const [family, setFamily] = useState([
    { id: 1, name: '정순희', relation: '어머니' }
  ])

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800)
  }, [])

  if (isLoading) return <MyPageSkeleton />

  const menuItems = [
    { id: '기본정보', label: '기본 정보', icon: '👤' },
    { id: '건강정보', label: '건강 정보', icon: '🏥' },
    { id: '가족관리', label: '가족 관리', icon: '👨‍👩‍👧‍👦' },
  ]

  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative overflow-x-hidden">
      
      {/* 1. 상단 헤더 영역 (PC 네비게이션) */}
      <div className="flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-white">
        <div>
          <p className="text-gray-400 text-sm font-bold mb-2 px-1">내 설정 및 관리</p>
          <h1 className="text-4xl font-black text-gray-900 leading-tight">마이페이지</h1>
        </div>
        
        {/* PC용 네비게이션 메뉴 (메인과 통일) */}
        <div className="hidden md:flex items-center gap-12 mb-2">
          <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-gray-400 font-bold text-lg hover:text-blue-500 transition-all">
            <span className="text-2xl">🏠</span> 홈
          </button>
          <button onClick={() => router.push('/mypage')} className="flex items-center gap-2 text-blue-500 font-black text-lg hover:opacity-80 transition-all">
            <span className="text-2xl">👤</span> 마이페이지
          </button>
        </div>
      </div>

      {/* 2. 2단 분할 레이아웃 대시보드 */}
      <div className="grid md:grid-cols-12 gap-8">
        
        {/* [좌측 영역] 프로필 요약 및 세로 메뉴 */}
        <div className="md:col-span-4 flex flex-col space-y-6">
          
          {/* 프로필 요약 카드 */}
          <div className="bg-white rounded-[40px] shadow-sm p-8 border border-white/50 animate-in fade-in slide-in-from-left-3 duration-500">
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-4xl shadow-lg shadow-blue-100 mb-4 border-4 border-white">
                👤
              </div>
              <h2 className="text-xl font-black text-gray-900 mb-1">홍길동님</h2>
              <p className="text-gray-400 text-xs font-bold mb-6 italic">jw@gmail.com</p>
              
              {/* 스탯 요약 */}
              <div className="grid grid-cols-2 gap-3 w-full">
                <div className="bg-blue-50/50 p-4 rounded-[24px] border border-blue-50">
                  <p className="text-[10px] font-black text-blue-500 mb-1">연속 복약</p>
                  <p className="text-lg font-black text-gray-800">3일째 🔥</p>
                </div>
                <div className="bg-orange-50/50 p-4 rounded-[24px] border border-orange-50">
                  <p className="text-[10px] font-black text-orange-500 mb-1">진행 챌린지</p>
                  <p className="text-lg font-black text-gray-800">1개 🏆</p>
                </div>
              </div>
            </div>
          </div>

          {/* 세로형 메뉴 리스트 */}
          <div className="bg-white rounded-[40px] shadow-sm p-4 border border-white/50 animate-in fade-in slide-in-from-left-3 duration-700">
            <nav className="flex flex-col space-y-2">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveMenu(item.id)}
                  className={`flex items-center gap-4 px-6 py-4 rounded-[24px] transition-all duration-200 active:scale-[0.98]
                    ${activeMenu === item.id 
                      ? 'bg-blue-500 text-white shadow-lg shadow-blue-100 font-black' 
                      : 'text-gray-500 hover:bg-slate-50 font-bold'}`}
                >
                  <span className="text-xl">{item.icon}</span>
                  <span className="text-sm">{item.label}</span>
                  {activeMenu === item.id && (
                    <span className="ml-auto w-1.5 h-1.5 bg-white rounded-full"></span>
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* [우측 영역] 메뉴별 상세 콘텐츠 */}
        <div className="md:col-span-8">
          <div className="bg-white rounded-[40px] shadow-sm p-10 border border-white/50 h-full min-h-[600px] animate-in fade-in slide-in-from-right-3 duration-500">
            
            {activeMenu === '기본정보' && (
              <div className="space-y-8 h-full flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">계정 정보</h3>
                  <button className="text-xs font-bold text-blue-500 hover:bg-blue-50 px-4 py-2 rounded-xl transition-all border border-blue-50">정보 수정</button>
                </div>
                
                <div className="space-y-6">
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">닉네임</span>
                    <span className="text-base font-black text-gray-800">홍길동</span>
                  </div>
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">이메일 주소</span>
                    <span className="text-base font-bold text-gray-800">jw@gmail.com</span>
                  </div>
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">로그인 방식</span>
                    <div className="flex items-center gap-2 bg-yellow-400/10 px-3 py-1.5 rounded-full border border-yellow-400/20">
                      <span className="w-5 h-5 bg-yellow-400 rounded-full flex items-center justify-center text-[10px] font-black">K</span>
                      <span className="text-sm font-black text-yellow-700 uppercase tracking-tighter">Kakao</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto pt-10 flex gap-4">
                  <button className="flex-1 bg-white border-2 border-slate-100 text-gray-400 py-5 rounded-[28px] text-sm font-black hover:bg-slate-50 hover:text-gray-600 transition-all active:scale-[0.98]">
                    로그아웃
                  </button>
                  <button className="text-slate-300 text-xs font-bold px-6 hover:text-red-400 transition-all">
                    회원탈퇴
                  </button>
                </div>
              </div>
            )}

            {activeMenu === '건강정보' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">나의 건강 프로필</h3>
                  <button className="text-xs font-black text-blue-500 hover:bg-blue-50 px-4 py-2 rounded-xl transition-all border border-blue-50">수정하기</button>
                </div>
                
                <div className="grid sm:grid-cols-2 gap-6">
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                    <p className="text-xs font-black text-gray-400 mb-2">나이</p>
                    <p className="text-xl font-black text-gray-800">25세</p>
                  </div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                    <p className="text-xs font-black text-gray-400 mb-2">키 / 몸무게</p>
                    <p className="text-xl font-black text-gray-800">163cm / 55kg</p>
                  </div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                    <p className="text-xs font-black text-gray-400 mb-2">보유 질환</p>
                    <p className="text-xl font-black text-gray-800">고혈압</p>
                  </div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                    <p className="text-xs font-black text-gray-400 mb-2">특이 알레르기</p>
                    <p className="text-xl font-black text-gray-800">페니실린</p>
                  </div>
                </div>
              </div>
            )}

            {activeMenu === '가족관리' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">함께 관리하는 가족</h3>
                  <button className="bg-blue-500 text-white px-6 py-3 rounded-2xl text-sm font-black shadow-lg shadow-blue-100 hover:bg-blue-600 transition-all active:scale-[0.95]">
                    + 가족 추가하기
                  </button>
                </div>
                
                {family.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {family.map((member) => (
                      <div key={member.id} className="bg-slate-50/50 rounded-[32px] p-8 border border-transparent hover:border-blue-100 hover:bg-white hover:shadow-xl hover:shadow-blue-50/50 transition-all flex justify-between items-center group">
                        <div className="flex items-center gap-5">
                          <div className="w-16 h-16 bg-white rounded-[24px] flex items-center justify-center text-2xl font-black text-blue-500 shadow-sm group-hover:bg-blue-500 group-hover:text-white transition-all duration-300">
                            {member.name[0]}
                          </div>
                          <div>
                            <p className="text-lg font-black text-gray-800">{member.name}</p>
                            <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-widest">{member.relation}</p>
                          </div>
                        </div>
                        <button className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all shadow-sm">
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-20 bg-slate-50/50 rounded-[40px] border border-dashed border-slate-200">
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

      {/* 3. 하단 네비게이션 (모바일 전용) */}
      <div className="md:hidden fixed bottom-0 left-0 w-full bg-white/90 backdrop-blur-lg border-t border-gray-100 flex py-5 px-8 z-40 shadow-[0_-5px_30px_rgba(0,0,0,0.08)] rounded-t-[40px]">
        <button 
          onClick={() => router.push('/main')} 
          className="flex-1 flex flex-col items-center gap-2 group">
          <span className="text-2xl group-active:scale-90 transition-transform opacity-40 group-hover:opacity-100">🏠</span>
          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Home</span>
        </button>
        <button 
          onClick={() => router.push('/mypage')} 
          className="flex-1 flex flex-col items-center gap-2 group">
          <span className="text-2xl group-active:scale-90 transition-transform">👤</span>
          <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">My</span>
        </button>
      </div>
    </main>
  )
}
