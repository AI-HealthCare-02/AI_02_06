'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'

function MyPageSkeleton() {
  return (
    <main className="min-h-screen bg-gray-50 animate-pulse">
      <div className="bg-white border-b border-gray-100 px-6 py-5">
        <div className="h-6 w-24 bg-gray-200 rounded" />
      </div>
      <div className="px-6 py-8 space-y-6">
        <div className="bg-white rounded-2xl p-6 h-32 w-full" />
        <div className="bg-white rounded-2xl p-6 h-64 w-full" />
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

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <Header title="마이페이지" subtitle="내 정보 및 관리" />

      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* 상단 탭 메뉴 */}
        <div className="flex gap-6 mb-8 border-b border-gray-200 overflow-x-auto whitespace-nowrap scrollbar-hide">
          {['기본정보', '건강정보', '가족관리'].map((menu) => (
            <button
              key={menu}
              onClick={() => setActiveMenu(menu)}
              className={`pb-3 text-sm font-bold cursor-pointer transition-colors active:scale-[0.98] transition-transform duration-150
                ${activeMenu === menu ? 'text-blue-500 border-b-2 border-blue-500' : 'text-gray-400'}`}
            >
              {menu}
            </button>
          ))}
        </div>

        {/* 컨텐츠 영역 */}
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
          {activeMenu === '기본정보' && (
            <div className="space-y-4">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-50">
                <div className="space-y-6">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-400 font-medium">닉네임</span>
                    <span className="text-sm font-bold text-gray-900">홍길동</span>
                  </div>
                  <div className="flex justify-between items-center pt-6 border-t border-gray-50">
                    <span className="text-sm text-gray-400 font-medium">이메일</span>
                    <span className="text-sm font-medium text-gray-900">jw@gmail.com</span>
                  </div>
                  <div className="flex justify-between items-center pt-6 border-t border-gray-50">
                    <span className="text-sm text-gray-400 font-medium">로그인 계정</span>
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 bg-yellow-400 rounded-full flex items-center justify-center text-[10px]">K</span>
                      <span className="text-sm font-medium text-gray-900">카카오</span>
                    </div>
                  </div>
                </div>
              </div>
              <button className="w-full bg-white border border-gray-200 text-gray-500 py-4 rounded-xl text-sm font-bold hover:bg-gray-50 transition-colors mt-4">
                로그아웃
              </button>
              <button className="w-full text-gray-300 text-xs py-2 hover:text-gray-400 transition-colors">
                회원탈퇴
              </button>
            </div>
          )}

          {activeMenu === '건강정보' && (
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-50">
              <div className="flex justify-between items-center mb-8">
                <h3 className="font-bold text-gray-900">내 건강 프로필</h3>
                <button className="text-xs text-blue-500 font-bold hover:underline">수정하기</button>
              </div>
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-400 font-medium">나이</span>
                  <span className="text-sm font-bold text-gray-900">25세</span>
                </div>
                <div className="flex justify-between items-center pt-6 border-t border-gray-50">
                  <span className="text-sm text-gray-400 font-medium">키 / 몸무게</span>
                  <span className="text-sm font-bold text-gray-900">163cm / 55kg</span>
                </div>
                <div className="flex justify-between items-center pt-6 border-t border-gray-50">
                  <span className="text-sm text-gray-400 font-medium">기저질환</span>
                  <span className="text-sm font-bold text-gray-900">고혈압</span>
                </div>
                <div className="flex justify-between items-center pt-6 border-t border-gray-50">
                  <span className="text-sm text-gray-400 font-medium">알레르기</span>
                  <span className="text-sm font-bold text-gray-900">페니실린</span>
                </div>
              </div>
            </div>
          )}

          {activeMenu === '가족관리' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center mb-2 px-1">
                <h3 className="font-bold text-gray-900">함께 관리하는 가족</h3>
                <button className="text-xs bg-blue-50 text-blue-600 px-3 py-1.5 rounded-lg font-bold hover:bg-blue-100 transition-colors">
                  + 추가하기
                </button>
              </div>
              
              {family.length > 0 ? (
                family.map((member) => (
                  <div key={member.id} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-50 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-xl font-bold text-blue-500">
                        {member.name[0]}
                      </div>
                      <div>
                        <p className="font-bold text-gray-900">{member.name}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{member.relation}</p>
                      </div>
                    </div>
                    <button className="text-xs text-red-400 font-bold hover:text-red-600 px-2 py-1 transition-colors">삭제</button>
                  </div>
                ))
              ) : (
                <EmptyState 
                  title="등록된 가족이 없어요" 
                  message="가족의 복약도 함께 관리해보세요!" 
                  actionLabel="가족 추가하기"
                  onAction={() => {}}
                />
              )}
            </div>
          )}
        </div>
      </div>

      <BottomNav />
    </main>
  )
}
