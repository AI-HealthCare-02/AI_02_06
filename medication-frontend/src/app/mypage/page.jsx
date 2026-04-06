'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

function MyPageSkeleton() {
  return (
    <main className="min-h-screen bg-gray-50 animate-pulse">
      <div className="bg-white border-b border-gray-200 px-10 py-4">
        <div className="h-5 w-24 bg-gray-200 rounded" />
      </div>
      <div className="py-10 flex gap-10 pl-10">
        <div className="w-48 shrink-0 space-y-4">
          <div className="h-4 w-24 bg-gray-200 rounded" />
          <div className="h-4 w-20 bg-gray-200 rounded" />
          <div className="h-4 w-20 bg-gray-200 rounded" />
        </div>
        <div className="flex-1 pr-10 space-y-6">
          <div className="h-6 w-32 bg-gray-200 rounded mb-6" />
          <div className="h-4 w-full bg-gray-200 rounded" />
          <div className="h-4 w-full bg-gray-200 rounded" />
          <div className="h-4 w-3/4 bg-gray-200 rounded" />
        </div>
      </div>
    </main>
  )
}

export default function MyPage() {
  const [activeMenu, setActiveMenu] = useState('기본정보')
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 1000)
  }, [])

  if (isLoading) return <MyPageSkeleton />

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-10 py-4">
        <h1 className="text-lg font-bold tracking-widest">MY PAGE</h1>
      </div>

      <div className="py-10 flex gap-10 pl-10">

        {/* 왼쪽 사이드바 */}
        <div className="w-48 shrink-0 flex flex-col justify-between" style={{minHeight: '400px'}}>
          <div>
            {['기본정보', '건강정보', '가족목록'].map((menu) => (
              <button
                key={menu}
                onClick={() => setActiveMenu(menu)}
                className={`block w-full text-left py-3 text-sm border-b border-gray-100 cursor-pointer
                  ${activeMenu === menu
                    ? 'font-bold text-black'
                    : 'text-gray-400 hover:text-black'
                  }`}
              >
                {menu}
              </button>
            ))}
          </div>
          <div className="space-y-2">
            <button className="block w-full text-left py-2 text-xs text-gray-400 hover:text-black cursor-pointer">
              로그아웃
            </button>
            <button className="block w-full text-left py-2 text-xs text-gray-300 hover:text-gray-500 cursor-pointer">
              회원탈퇴
            </button>
          </div>
        </div>

        {/* 오른쪽 내용 */}
        <div className="flex-1 pr-10">

          {activeMenu === '기본정보' && (
            <div>
              <h2 className="text-lg font-bold mb-8 pb-3 border-b border-black">기본 정보</h2>
              <div className="space-y-6">
                <div className="flex items-center">
                  <span className="w-32 text-sm text-gray-500">닉네임</span>
                  <span className="text-sm">홍길동</span>
                </div>
                <div className="flex items-center border-t border-gray-100 pt-6">
                  <span className="w-32 text-sm text-gray-500">이메일</span>
                  <span className="text-sm">jw@gmail.com</span>
                </div>
                <div className="flex items-center border-t border-gray-100 pt-6">
                  <span className="w-32 text-sm text-gray-500">로그인</span>
                  <span className="text-sm">카카오</span>
                </div>
              </div>
              <button className="w-full border border-gray-200 py-3 rounded-xl text-gray-500 text-sm cursor-pointer hover:bg-gray-50 mt-10">
                로그아웃
              </button>
              <button className="w-full text-gray-300 text-xs cursor-pointer mt-3 hover:text-gray-400">
                회원탈퇴
              </button>
            </div>
          )}

          {activeMenu === '건강정보' && (
            <div>
              <div className="flex justify-between items-center mb-8 pb-3 border-b border-black">
                <h2 className="text-lg font-bold">건강 정보</h2>
                <button className="text-sm text-gray-400 hover:text-black cursor-pointer">수정</button>
              </div>
              <div className="space-y-6">
                <div className="flex items-center">
                  <span className="w-32 text-sm text-gray-500">나이</span>
                  <span className="text-sm">25세</span>
                </div>
                <div className="flex items-center border-t border-gray-100 pt-6">
                  <span className="w-32 text-sm text-gray-500">키 / 몸무게</span>
                  <span className="text-sm">163cm / 55kg</span>
                </div>
                <div className="flex items-center border-t border-gray-100 pt-6">
                  <span className="w-32 text-sm text-gray-500">기저질환</span>
                  <span className="text-sm">고혈압</span>
                </div>
                <div className="flex items-center border-t border-gray-100 pt-6">
                  <span className="w-32 text-sm text-gray-500">알레르기</span>
                  <span className="text-sm">페니실린</span>
                </div>
              </div>
            </div>
          )}

          {activeMenu === '가족목록' && (
            <div>
              <div className="flex justify-between items-center mb-8 pb-3 border-b border-black">
                <h2 className="text-lg font-bold">가족 목록</h2>
                <button className="text-sm text-gray-400 hover:text-black cursor-pointer">+ 추가</button>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center py-4 border-b border-gray-100">
                  <div>
                    <p className="text-sm font-semibold">정순희</p>
                    <p className="text-xs text-gray-400 mt-1">어머니</p>
                  </div>
                  <button className="text-xs text-red-400 hover:text-red-600 cursor-pointer">삭제</button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* 하단 네비게이션 */}
      <div className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex">
        <button onClick={() => router.push('/main')} className="flex-1 py-4 text-gray-400 text-sm">홈</button>
        <button onClick={() => router.push('/mypage')} className="flex-1 py-4 text-blue-500 text-sm font-semibold">마이페이지</button>
      </div>

    </main>
  )
}