'use client'
import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, FileText, Trophy, Pill, User, MessageCircle, LogOut } from 'lucide-react'
import LogoutModal, { useLogout } from '@/components/auth/LogoutModal'
import ChatModal from '@/components/chat/ChatModal'
import ProfileSwitcher from '@/components/layout/ProfileSwitcher'
import { useProfile } from '@/contexts/ProfileContext'
import { useOcrEntryNavigator } from '@/contexts/OcrDraftContext'

export default function Navigation() {
  const router = useRouter()
  const pathname = usePathname()
  const [showChat, setShowChat] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  const isLanding = pathname === '/' || pathname === '/login'
  const isAuthPage = pathname === '/login' || pathname.startsWith('/auth/')

  const { selectedProfileId } = useProfile()
  const goToOcrEntry = useOcrEntryNavigator()

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  const { showLogoutModal, setShowLogoutModal, handleLogout } = useLogout()

  const menus = [
    { label: '홈',         path: '/main',            icon: <Home size={18} /> },
    { label: '처방전 등록', path: '/ocr',             icon: <FileText size={18} /> },
    { label: '챌린지',     path: '/challenge',       icon: <Trophy size={18} /> },
    { label: '복약 가이드', path: '/medication',      icon: <Pill size={18} /> },
    { label: '생활습관 가이드', path: '/lifestyle-guide', icon: <Pill size={18} /> },
    { label: '마이페이지', path: '/mypage',          icon: <User size={18} /> },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={selectedProfileId} />}
      {showLogoutModal && <LogoutModal onClose={() => setShowLogoutModal(false)} onConfirm={handleLogout} />}

      <nav className={`fixed top-0 w-full z-50 transition-all duration-200 border-b
        ${scrolled
          ? 'bg-white/90 backdrop-blur-xl border-gray-200/80'
          : 'bg-white border-gray-200'}`}>
        <div className="max-w-[1400px] mx-auto px-6 flex justify-between items-center h-14">

          <div className="flex items-center gap-10">
            {/* 로고 */}
            <Link href={isLanding ? '/' : '/main'} className="flex items-center gap-2 flex-shrink-0">
              <div className="w-7 h-7 bg-gray-900 rounded-md flex items-center justify-center text-white">
                <Pill size={14} />
              </div>
              <span className="font-semibold text-[15px] tracking-tight text-gray-900">Downforce</span>
            </Link>

            {/* 앱 내부 페이지 데스크탑 네비게이션.
                "처방전 등록" 메뉴는 활성 draft 가 있으면 result 로 보내야 하므로
                정적 Link 가 아닌 useOcrEntryNavigator 훅 사용. */}
            {!isLanding && (
              <div className="hidden md:flex items-center gap-1">
                {menus.map((menu) => {
                  const isActive = menu.path === '/ocr'
                    ? pathname.startsWith('/ocr')
                    : pathname === menu.path
                  const className = `px-4 py-1.5 text-[13px] rounded-lg transition-all
                    ${isActive
                      ? 'text-gray-900 font-bold bg-gray-50'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-50/50'}`
                  if (menu.path === '/ocr') {
                    return (
                      <button key={menu.path} onClick={goToOcrEntry} className={`${className} cursor-pointer`}>
                        {menu.label}
                      </button>
                    )
                  }
                  return (
                    <Link key={menu.path} href={menu.path} className={className}>
                      {menu.label}
                    </Link>
                  )
                })}
              </div>
            )}
          </div>

          {/* 오른쪽 버튼 영역 */}
          <div className="hidden md:flex items-center gap-2">
            {isLanding ? (
              <>
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm text-gray-600 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md">
                  로그인
                </button>
                <button
                  onClick={() => router.push('/login')}
                  className="text-sm bg-gray-900 text-white font-medium cursor-pointer px-4 py-1.5 rounded-lg hover:bg-gray-700 transition-colors">
                  시작하기
                </button>
              </>
            ) : (isAuthPage ? (<></>) : (
              <>
                <ProfileSwitcher />
                <div className="w-px h-4 bg-gray-200" />
                <button onClick={() => setShowLogoutModal(true)}
                className="text-sm text-gray-500 hover:text-gray-900 transition-colors cursor-pointer px-3.5 py-1.5 hover:bg-gray-100 rounded-md flex items-center gap-1.5">
                  <LogOut size={15} />
                  로그아웃
                </button>
              </>
            ))}
          </div>

          {/* 모바일: 랜딩은 로그인 버튼, 앱 페이지는 표시 없음 (하단 네비게이션 사용) */}
          {isLanding && (
            <button
              onClick={() => router.push('/login')}
              className="md:hidden text-sm bg-gray-900 text-white font-medium cursor-pointer px-4 py-1.5 rounded-lg">
              로그인
            </button>
          )}
        </div>
      </nav>

      {/* 플로팅 챗 버튼 - 앱 내부 페이지에서만 (로그인/인증 페이지 제외) */}
      {!isLanding && !isAuthPage && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed bottom-24 right-6 z-[60] w-12 h-12 bg-gray-900 rounded-2xl shadow-lg flex items-center justify-center text-white cursor-pointer hover:bg-gray-700 hover:scale-105 transition-all active:scale-95">
          <MessageCircle size={20} />
        </button>
      )}

      <div className="h-14" />
    </>
  )
}
