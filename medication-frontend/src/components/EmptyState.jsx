'use client'

export default function EmptyState({ 
  icon, 
  title, 
  message, 
  actionLabel, 
  onAction 
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-6 text-center bg-white rounded-2xl shadow-sm border border-gray-50">
      <div className="mb-4 text-gray-200">
        {icon || (
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        )}
      </div>
      <h3 className="text-lg font-bold text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-400 text-sm mb-6 max-w-[200px] leading-relaxed">
        {message}
      </p>
      {actionLabel && (
        <button
          onClick={onAction}
          className="bg-blue-500 text-white px-8 py-3 rounded-xl font-semibold text-sm hover:bg-blue-600 transition-colors shadow-sm cursor-pointer"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}
