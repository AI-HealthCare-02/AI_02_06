'use client'
import { AlertCircle } from 'lucide-react'

export default function EmptyState({
  icon,
  title,
  message,
  actionLabel,
  onAction,
  actionClassName
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center bg-white rounded-2xl shadow-sm border border-gray-50">
      <div className="mb-4 text-gray-200">
        {icon || <AlertCircle size={48} />}
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-400 text-sm mb-6 max-w-[200px] leading-relaxed">
        {message}
      </p>
      {actionLabel && (
        <button
          onClick={onAction}
          className={actionClassName || "bg-gray-900 text-white px-8 py-3 rounded-xl font-black text-sm hover:bg-gray-800 transition-all shadow-lg cursor-pointer active:scale-95"}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
