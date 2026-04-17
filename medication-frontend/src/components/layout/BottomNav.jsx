'use client'
import { useRouter, usePathname } from 'next/navigation'
import { Home, FileText, Trophy, Pill, User } from 'lucide-react'

export default function BottomNav() {
  const router = useRouter()
  const pathname = usePathname()

  // 랜딩 페이지에서는 표시하지 않음
  if (pathname === '/') return null

  const tabs = [
    { label: '홈',         path: '/main',       Icon: Home },
    { label: '등록',       path: '/ocr',        Icon: FileText },
    { label: '챌린지',     path: '/challenge',  Icon: Trophy },
    { label: '가이드',     path: '/medication', Icon: Pill },
    { label: '마이',       path: '/mypage',     Icon: User },
  ]

  return (
    <nav className="md:hidden fixed bottom-0 left-0 w-full bg-white/95 backdrop-blur-lg border-t border-gray-100 flex py-3 px-2 z-50 shadow-[0_-5px_30px_rgba(0,0,0,0.06)] rounded-t-[32px]">
      {tabs.map(({ label, path, Icon }) => {
        const isActive = pathname === path
        return (
          <button
            key={path}
            onClick={() => router.push(path)}
            className="flex-1 flex flex-col items-center justify-center gap-1.5 group cursor-pointer"
          >
            <div className={`p-1 transition-all duration-300 ${isActive ? 'scale-110 text-gray-900' : 'text-gray-300'}`}>
              <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
            </div>
            <span className={`text-[10px] tracking-tight transition-all duration-300
              ${isActive ? 'text-gray-900 font-black' : 'text-gray-400 font-bold'}`}>
              {label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
