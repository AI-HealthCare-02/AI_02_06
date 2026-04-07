'use client'
import { useRouter, usePathname } from 'next/navigation'
import { Home, Trophy, User } from 'lucide-react'

export default function BottomNav() {
  const router = useRouter()
  const pathname = usePathname()

  const tabs = [
    { label: '홈',       path: '/main',      Icon: Home },
    { label: '챌린지',   path: '/challenge', Icon: Trophy },
    { label: '마이페이지', path: '/mypage',  Icon: User },
  ]

  return (
    <nav className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex pb-safe shadow-lg z-40">
      {tabs.map(({ label, path, Icon }) => {
        const isActive = pathname === path
        return (
          <button
            key={path}
            onClick={() => router.push(path)}
            className={`flex-1 flex flex-col items-center justify-center py-3 gap-1 cursor-pointer transition-colors
              ${isActive ? 'text-blue-500' : 'text-gray-400 hover:text-gray-600'}`}
          >
            <Icon size={24} fill={isActive ? 'currentColor' : 'none'} />
            <span className="text-[10px] font-medium leading-none">{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
