'use client'
import { useState } from 'react'

export default function MyPage() {
  const [activeTab, setActiveTab] = useState('기본정보')

  return (
    <main className="max-w-lg mx-auto p-6 mt-10">
      <h1 className="text-2xl font-bold mb-6">마이페이지</h1>

      {/* 탭 버튼 */}
      <div className="flex gap-6 mb-8 border-b border-gray-200">
  {['기본정보', '건강정보', '가족목록'].map((tab) => (
    <button
      key={tab}
      onClick={() => setActiveTab(tab)}
      className={`pb-3 text-sm font-semibold cursor-pointer
        ${activeTab === tab
          ? 'text-blue-500 border-b-2 border-blue-500'
          : 'text-gray-400'
        }`}
    >
      {tab}
    </button>
  ))}
</div>

      {/* 기본정보 탭 */}
      {activeTab === '기본정보' && (
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <div className="space-y-4">
            <div>
              <span className="text-gray-400 text-sm">닉네임</span>
              <p className="font-semibold">홍길동</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">이메일</span>
              <p className="font-semibold">jw@gmail.com</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">로그인</span>
              <p className="font-semibold">카카오</p>
            </div>
          </div>

          {/* 로그아웃 버튼 */}
          <button className="w-full border border-gray-200 py-3 rounded-xl text-gray-500 text-sm cursor-pointer hover:bg-gray-50 mt-6">
            로그아웃
          </button>

          {/* 회원탈퇴 - 작고 눈에 안 띄게 */}
          <button className="w-full text-gray-300 text-xs cursor-pointer mt-3 hover:text-gray-400">
            회원탈퇴
          </button>
        </div>
      )}

      {/* 건강정보 탭 */}
      {activeTab === '건강정보' && (
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-bold">건강 정보</h2>
            <button className="text-blue-500 text-sm cursor-pointer">수정</button>
          </div>
          <div className="space-y-4">
            <div>
              <span className="text-gray-400 text-sm">나이</span>
              <p className="font-semibold">25세</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">키 / 몸무게</span>
              <p className="font-semibold">163cm / 55kg</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">기저질환</span>
              <p className="font-semibold">고혈압</p>
            </div>
            <div>
              <span className="text-gray-400 text-sm">알레르기</span>
              <p className="font-semibold">페니실린</p>
            </div>
          </div>
        </div>
      )}

      {/* 가족목록 탭 */}
      {activeTab === '가족목록' && (
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-bold">가족 목록</h2>
            <button className="text-blue-500 text-sm cursor-pointer">+ 추가</button>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-semibold">정순희</p>
                <span className="text-gray-400 text-sm">어머니</span>
              </div>
              <button className="text-red-400 text-sm cursor-pointer">삭제</button>
            </div>
          </div>
        </div>
      )}

    </main>
  )
}