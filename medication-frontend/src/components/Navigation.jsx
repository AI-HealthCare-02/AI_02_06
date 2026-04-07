'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function Navigation() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)

  const menus = [
    { icon: '🏠', label: '홈', path: '/main' },
    { icon: '👤', label: '마이페이지', path: '/mypage' },
    { icon: '💊', label: '복약 현황', path: '/main' },
    { icon: '📷', label: '처방전 등록', path: '/ocr' },
    { icon: '🏆', label: '챌린지', path: '/challenge' },
    { icon: '📋', label: '용법/주의사항', path: '/medication' },
  ]

  return (
    <>
      {/* 햄버거 버튼 - 모든 페이지 왼쪽 상단 고정 */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-4 left-4 z-40 w-10 h-10 bg-white rounded-full shadow-md flex items-center justify-center cursor-pointer hover:shadow-lg">
        ≡
      </button>

      {/* 챗봇 플로팅 버튼 - 오른쪽 하단 고정 */}
      <button
        onClick={() => router.push('/chat')}
        className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-blue-500 rounded-full shadow-lg flex items-center justify-center text-white text-2xl cursor-pointer hover:bg-blue-600">
        💊
      </button>

      {/* 어두운 배경 */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 bg-black/50 z-40"
        />
      )}

      {/* 사이드바 */}
      <div className={`fixed top-0 left-0 h-full w-64 bg-white z-50 shadow-xl transform transition-transform duration-300
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>

        {/* 사이드바 헤더 */}
        <div className="flex justify-between items-center px-6 py-5 border-b border-gray-100">
          <h2 className="font-bold text-lg">💊 Downforce</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="text-gray-400 hover:text-black cursor-pointer text-xl">
            ✕
          </button>
        </div>

        {/* 메뉴 목록 */}
        <div className="py-4">
          {menus.map((menu, i) => (
            <button
              key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className="flex items-center gap-4 w-full px-6 py-4 text-sm hover:bg-gray-50 cursor-pointer">
              <span className="text-xl">{menu.icon}</span>
              <span className="font-medium">{menu.label}</span>
            </button>
          ))}
        </div>

        {/* 하단 로그아웃 */}
        <div className="absolute bottom-0 w-full border-t border-gray-100 p-6">
          <button className="text-gray-400 text-sm cursor-pointer hover:text-black">
            로그아웃
          </button>
        </div>
      </div>
    </>
  )
}