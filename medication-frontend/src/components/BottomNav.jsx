'use client'
import { useRouter, usePathname } from 'next/navigation'

export default function BottomNav() {
  const router = useRouter()
  const pathname = usePathname()

  const tabs = [
    { 
      label: '홈', 
      path: '/main', 
      icon: (active) => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill={active ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      )
    },
    { 
      label: '챌린지', 
      path: '/challenge', 
      icon: (active) => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill={active ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526"/>
          <circle cx="12" cy="8" r="6"/>
        </svg>
      )
    },
    { 
      label: '마이페이지', 
      path: '/mypage', 
      icon: (active) => (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill={active ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
        </svg>
      )
    }
  ]

  return (
    <nav className="fixed bottom-0 w-full bg-white border-t border-gray-100 flex pb-safe shadow-lg z-40">
      {tabs.map((tab) => {
        const isActive = pathname === tab.path
        return (
          <button
            key={tab.path}
            onClick={() => router.push(tab.path)}
            className={`flex-1 flex flex-col items-center justify-center py-3 gap-1 cursor-pointer transition-colors
              ${isActive ? 'text-blue-500' : 'text-gray-400 hover:text-gray-600'}`}
          >
            {tab.icon(isActive)}
            <span className="text-[10px] font-medium leading-none">{tab.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
