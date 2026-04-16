'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Home, User, Camera, Trophy, ClipboardList, MessageCircle, X, Send } from 'lucide-react'
import api from '@/lib/api'
import ChatModal from '@/components/ChatModal'

export default function Navigation() {
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [profileId, setProfileId] = useState(null)

  // 프로필 ID 가져오기
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/api/v1/profiles')
        if (res.data?.length > 0) {
          const self = res.data.find(p => p.relation_type === 'SELF') || res.data[0]
          setProfileId(self.id)
        }
      } catch (err) {
        console.error('프로필 조회 실패:', err)
      }
    }
    fetchProfile()
  }, [])

  const menus = [
    { icon: <Home size={18} />, label: '홈', path: '/main' },
    { icon: <User size={18} />, label: '마이페이지', path: '/mypage' },
    { icon: <Camera size={18} />, label: '처방전 등록', path: '/ocr' },
    { icon: <Trophy size={18} />, label: '챌린지', path: '/challenge' },
    { icon: <ClipboardList size={18} />, label: '용법/주의사항', path: '/medication' },
  ]

  return (
    <>
      {showChat && <ChatModal onClose={() => setShowChat(false)} profileId={profileId} />}

      {/* 햄버거 버튼 */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed top-6 left-6 z-40 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center cursor-pointer hover:shadow-xl transition-all active:scale-90 border border-gray-100"
      >
        <div className="flex flex-col gap-1">
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
          <div className="w-5 h-0.5 bg-gray-600 rounded-full" />
        </div>
      </button>

      {/* 챗봇 플로팅 버튼 */}
      <button
        onClick={() => setShowChat(true)}
        className="fixed bottom-8 right-8 z-40 w-16 h-16 bg-blue-600 rounded-full shadow-2xl flex items-center justify-center text-white cursor-pointer hover:bg-blue-700 hover:scale-110 transition-all active:scale-95"
      >
        <MessageCircle size={28} />
      </button>

      {/* 어두운 배경 */}
      {isOpen && (
        <div onClick={() => setIsOpen(false)} className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-all" />
      )}

      {/* 사이드바 */}
      <div className={`fixed top-0 left-0 h-full w-72 bg-white z-50 shadow-2xl transform transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex justify-between items-center px-8 py-8 border-b border-gray-50">
          <h2 className="font-black text-2xl text-blue-600 tracking-tighter">Downforce</h2>
          <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-black transition-colors">
            <X size={24} />
          </button>
        </div>
        <div className="py-6 px-4">
          {menus.map((menu, i) => (
            <button key={i}
              onClick={() => { router.push(menu.path); setIsOpen(false) }}
              className="flex items-center gap-4 w-full px-6 py-4 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all group"
            >
              <span className="group-hover:scale-110 transition-transform">{menu.icon}</span>
              <span className="font-bold">{menu.label}</span>
            </button>
          ))}
        </div>
        <div className="absolute bottom-0 w-full border-t border-gray-50 p-8">
          <button className="text-gray-400 font-bold hover:text-red-500 transition-colors">로그아웃</button>
        </div>
      </div>
    </>
  )
}
