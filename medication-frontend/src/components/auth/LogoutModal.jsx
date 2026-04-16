'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { LogOut, UserX } from 'lucide-react'
import api from '@/lib/api'
import toast from 'react-hot-toast'


export function useLogout() {
  const router = useRouter()
  const [showLogoutModal, setShowLogoutModal] = useState(false)

  const handleLogout = async () => {
    setShowLogoutModal(false)
    try {
      await api.post('/api/v1/auth/logout')
      toast.success('로그아웃 되었습니다.')
      router.push('/')
    } catch (err) {
      toast.error('로그아웃 중 오류가 발생했습니다.')
      router.push('/')
    }
  }

  return { showLogoutModal, setShowLogoutModal, handleLogout }
}

export function useDeleteAccount() {
  const router = useRouter()
  const [showDeleteModal, setShowDeleteModal] = useState(false)

  const handleDeleteAccount = async () => {
    setShowDeleteModal(false)
    try {
      await api.delete('/api/v1/auth/account')
      toast.success('회원 탈퇴가 완료되었습니다.')
      router.push('/')
    } catch (err) {
      toast.error('회원 탈퇴 중 오류가 발생했습니다.')
    }
  }

  return { showDeleteModal, setShowDeleteModal, handleDeleteAccount }
}

export function DeleteAccountModal({ onClose, onConfirm }) {
  return (
    <div className="fixed inset-0 bg-black/50 z-[200] flex items-center justify-center p-4">
      <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-xl">
        <div className="flex items-center justify-center w-14 h-14 bg-red-50 rounded-full mx-auto mb-5">
          <UserX size={24} className="text-red-500" />
        </div>
        <h3 className="text-xl font-black text-gray-900 mb-2 text-center">회원 탈퇴</h3>
        <p className="text-gray-400 text-sm text-center mb-2">정말로 탈퇴하시겠습니까?</p>
        <p className="text-red-400 text-xs text-center mb-8">탈퇴 시 모든 데이터가 삭제되며 복구할 수 없습니다.</p>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-2xl bg-gray-50 text-gray-500 font-bold hover:bg-gray-100 transition-all cursor-pointer">
            취소
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-3 rounded-2xl bg-red-500 text-white font-black hover:bg-red-600 transition-all cursor-pointer">
            탈퇴하기
          </button>
        </div>
      </div>
    </div>
  )
}

export default function LogoutModal({ onClose, onConfirm }) {
  return (
    <div className="fixed inset-0 bg-black/50 z-[200] flex items-center justify-center p-4">
      <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-xl">
        <div className="flex items-center justify-center w-14 h-14 bg-gray-100 rounded-full mx-auto mb-5">
          <LogOut size={24} className="text-gray-600" />
        </div>
        <h3 className="text-xl font-black text-gray-900 mb-2 text-center">로그아웃</h3>
        <p className="text-gray-400 text-sm text-center mb-8">정말 로그아웃 하시겠습니까?</p>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 rounded-2xl bg-gray-50 text-gray-500 font-bold hover:bg-gray-100 transition-all cursor-pointer">
            취소
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-3 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-700 transition-all cursor-pointer">
            로그아웃
          </button>
        </div>
      </div>
    </div>
  )
}
