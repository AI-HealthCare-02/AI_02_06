'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, User } from 'lucide-react'
import { useProfile } from '@/contexts/ProfileContext'

export default function ProfileSwitcher() {
  const { profiles, selectedProfile, selectedProfileId, setSelectedProfileId, RELATION_LABELS } = useProfile()
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef(null)

  // 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (!selectedProfile || profiles.length <= 1) {
    // 프로필이 1개 이하면 이름만 표시
    return (
      <div className="flex items-center gap-1.5 text-[13px] text-gray-700 px-2">
        <User size={14} className="text-gray-400" />
        <span className="font-medium">{selectedProfile?.name || ''}</span>
        <span className="text-[11px] text-gray-400">
          {selectedProfile ? RELATION_LABELS[selectedProfile.relation_type] || selectedProfile.relation_type : ''}
        </span>
      </div>
    )
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setIsOpen(prev => !prev)}
        className="flex items-center gap-1.5 text-[13px] text-gray-700 px-2.5 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <User size={14} className="text-gray-400" />
        <span className="font-medium">{selectedProfile.name}</span>
        <span className="text-[11px] text-gray-400">
          {RELATION_LABELS[selectedProfile.relation_type] || selectedProfile.relation_type}
        </span>
        <ChevronDown size={13} className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1.5 w-52 bg-white border border-gray-200 rounded-xl shadow-lg z-[100] overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-[11px] text-gray-400 font-medium tracking-wide uppercase">프로필 전환</p>
          </div>
          <ul className="py-1">
            {profiles.map(profile => (
              <li key={profile.id}>
                <button
                  onClick={() => {
                    setSelectedProfileId(profile.id)
                    setIsOpen(false)
                  }}
                  className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                      <User size={13} className="text-gray-500" />
                    </div>
                    <div>
                      <p className="text-[13px] font-medium text-gray-900">{profile.name}</p>
                      <p className="text-[11px] text-gray-400">
                        {RELATION_LABELS[profile.relation_type] || profile.relation_type}
                      </p>
                    </div>
                  </div>
                  {profile.id === selectedProfileId && (
                    <Check size={14} className="text-gray-900 flex-shrink-0" />
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
