'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { User, Activity, Users, Home, Trash2, X, Plus, Check, Settings, Mail, Phone, Calendar, Heart, ShieldAlert, UserPlus } from 'lucide-react'
import EmptyState from '../../components/EmptyState'

// --- 모달 컴포넌트들 ---

function Modal({ title, children, onClose, onSave }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <div className="bg-white rounded-[40px] w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200">
        <div className="flex justify-between items-center p-8 border-b border-gray-50">
          <h3 className="text-xl font-black text-gray-900">{title}</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors cursor-pointer">
            <X size={24} className="text-gray-400" />
          </button>
        </div>
        <div className="p-8 max-h-[70vh] overflow-y-auto">
          {children}
        </div>
        <div className="p-8 pt-4 flex gap-3">
          <button onClick={onClose} className="flex-1 py-4 rounded-2xl bg-gray-50 text-gray-500 font-bold hover:bg-gray-100 transition-all cursor-pointer">
            취소
          </button>
          <button onClick={onSave} className="flex-1 py-4 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all shadow-lg cursor-pointer">
            저장하기
          </button>
        </div>
      </div>
    </div>
  )
}

function BasicInfoModal({ info, onClose, onSave }) {
  const [formData, setFormData] = useState({ ...info })
  return (
    <Modal title="계정 정보 수정" onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">닉네임</label>
          <input
            type="text"
            value={formData.nickname}
            onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            placeholder="닉네임을 입력하세요"
          />
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">이메일 주소</label>
          <input
            type="email"
            value={formData.email}
            disabled
            className="w-full px-6 py-4 bg-gray-100 border border-transparent rounded-2xl outline-none font-bold text-gray-400 cursor-not-allowed"
          />
          <p className="text-[10px] text-gray-400 mt-2 ml-1">* 이메일은 변경할 수 없습니다.</p>
        </div>
      </div>
    </Modal>
  )
}

function HealthInfoModal({ info, onClose, onSave }) {
  const [formData, setFormData] = useState({ ...info })
  return (
    <Modal title="건강 프로필 수정" onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">나이</label>
            <input
              type="text"
              value={formData.age}
              onChange={(e) => setFormData({ ...formData, age: e.target.value })}
              className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            />
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">성별</label>
            <select
              value={formData.gender}
              onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
              className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all appearance-none"
            >
              <option value="남성">남성</option>
              <option value="여성">여성</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">키 (cm)</label>
            <input
              type="number"
              value={formData.height}
              onChange={(e) => setFormData({ ...formData, height: e.target.value })}
              className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            />
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">몸무게 (kg)</label>
            <input
              type="number"
              value={formData.weight}
              onChange={(e) => setFormData({ ...formData, weight: e.target.value })}
              className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            />
          </div>
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">보유 질환</label>
          <input
            type="text"
            value={formData.diseases}
            onChange={(e) => setFormData({ ...formData, diseases: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            placeholder="질환을 콤마(,)로 구분해 입력하세요"
          />
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">특이 알레르기</label>
          <input
            type="text"
            value={formData.allergies}
            onChange={(e) => setFormData({ ...formData, allergies: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            placeholder="알레르기를 입력하세요"
          />
        </div>
      </div>
    </Modal>
  )
}

function FamilyModal({ member, onClose, onSave }) {
  const [formData, setFormData] = useState(member || { name: '', relation: '' })
  return (
    <Modal title={member ? "가족 정보 수정" : "가족 추가하기"} onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">이름</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            placeholder="가족의 이름을 입력하세요"
          />
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">관계</label>
          <input
            type="text"
            value={formData.relation}
            onChange={(e) => setFormData({ ...formData, relation: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all"
            placeholder="관계 (예: 어머니, 동생 등)"
          />
        </div>
      </div>
    </Modal>
  )
}

function MyPageSkeleton() {
  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 animate-pulse">
      <div className="flex justify-between items-end mb-10 bg-white p-8 rounded-[32px]">
        <div className="h-10 w-48 bg-gray-200 rounded-xl" />
        <div className="flex gap-8">
          <div className="h-6 w-20 bg-gray-200 rounded" />
          <div className="h-6 w-20 bg-gray-200 rounded" />
        </div>
      </div>
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-4 space-y-6">
          <div className="bg-white rounded-[32px] h-64 w-full" />
          <div className="bg-white rounded-[32px] h-80 w-full" />
        </div>
        <div className="md:col-span-8 bg-white rounded-[32px] h-[600px] w-full" />
      </div>
    </main>
  )
}

export default function MyPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [activeMenu, setActiveMenu] = useState('기본정보')

  // 데이터 상태
  const [basicInfo, setBasicInfo] = useState({
    nickname: '홍길동',
    email: 'jw@gmail.com',
    provider: 'Kakao'
  })

  const [healthInfo, setHealthInfo] = useState({
    age: '25세',
    gender: '남성',
    height: '163',
    weight: '55',
    diseases: '고혈압',
    allergies: '페니실린'
  })

  const [family, setFamily] = useState([
    { id: 1, name: '정순희', relation: '어머니' }
  ])

  // 모달 상태
  const [modalType, setModalType] = useState(null) // 'basic', 'health', 'family'
  const [selectedFamilyMember, setSelectedFamilyMember] = useState(null)

  useEffect(() => {
    setTimeout(() => setIsLoading(false), 800)
  }, [])

  if (isLoading) return <MyPageSkeleton />

  const menuItems = [
    { id: '기본정보', label: '기본 정보', icon: <User size={18} /> },
    { id: '건강정보', label: '건강 정보', icon: <Activity size={18} /> },
    { id: '가족관리', label: '가족 관리', icon: <Users size={18} /> },
  ]

  const handleSaveBasic = (newData) => {
    setBasicInfo(newData)
    setModalType(null)
  }

  const handleSaveHealth = (newData) => {
    setHealthInfo(newData)
    setModalType(null)
  }

  const handleSaveFamily = (newData) => {
    if (selectedFamilyMember) {
      setFamily(family.map(m => m.id === selectedFamilyMember.id ? { ...newData } : m))
    } else {
      setFamily([...family, { ...newData, id: Date.now() }])
    }
    setModalType(null)
    setSelectedFamilyMember(null)
  }

  const handleDeleteFamily = (id, e) => {
    e.stopPropagation()
    if (confirm('정말로 삭제하시겠습니까?')) {
      setFamily(family.filter(m => m.id !== id))
    }
  }

  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative overflow-x-hidden">

      {/* 상단 헤더 */}
      <div className="flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-gray-100">
        <div>
          <p className="text-gray-400 text-sm font-bold mb-2 px-1">내 설정 및 관리</p>
          <h1 className="text-4xl font-black text-gray-900 leading-tight">마이페이지</h1>
        </div>
        <div className="hidden md:flex items-center gap-10 mb-2">
          <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-gray-400 font-bold text-base hover:text-gray-900 transition-all cursor-pointer">
            <Home size={18} /> 홈
          </button>
          <button onClick={() => router.push('/mypage')} className="flex items-center gap-2 text-gray-900 font-black text-base cursor-pointer">
            <User size={18} /> 마이페이지
          </button>
        </div>
      </div>

      {/* 2단 레이아웃 */}
      <div className="grid md:grid-cols-12 gap-8">

        {/* 좌측: 프로필 + 메뉴 */}
        <div className="md:col-span-4 flex flex-col space-y-6">

          {/* 프로필 카드 */}
          <div className="bg-white rounded-[40px] shadow-sm p-8 border border-gray-100">
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-gray-900 rounded-full flex items-center justify-center shadow-lg mb-4 border-4 border-white">
                <User size={40} className="text-white" />
              </div>
              <h2 className="text-xl font-black text-gray-900 mb-1">{basicInfo.nickname}님</h2>
              <p className="text-gray-400 text-xs font-bold mb-6">{basicInfo.email}</p>

              <div className="grid grid-cols-2 gap-3 w-full">
                <div className="bg-gray-50 p-4 rounded-[24px] border border-gray-100">
                  <p className="text-[10px] font-black text-gray-500 mb-1">연속 복약</p>
                  <p className="text-lg font-black text-gray-800">3일째</p>
                </div>
                <div className="bg-orange-50 p-4 rounded-[24px] border border-orange-100">
                  <p className="text-[10px] font-black text-orange-500 mb-1">진행 챌린지</p>
                  <p className="text-lg font-black text-gray-800">1개</p>
                </div>
              </div>
            </div>
          </div>

          {/* 세로 메뉴 */}
          <div className="bg-white rounded-[40px] shadow-sm p-4 border border-gray-100">
            <nav className="flex flex-col space-y-2">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveMenu(item.id)}
                  className={`flex items-center gap-4 px-6 py-4 rounded-[24px] transition-all duration-200 active:scale-[0.98] cursor-pointer
                    ${activeMenu === item.id
                      ? 'bg-gray-900 text-white font-black shadow-lg'
                      : 'text-gray-500 hover:bg-gray-50 font-bold'}`}
                >
                  <span>{item.icon}</span>
                  <span className="text-sm">{item.label}</span>
                  {activeMenu === item.id && (
                    <span className="ml-auto w-1.5 h-1.5 bg-white rounded-full" />
                  )}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 우측: 콘텐츠 */}
        <div className="md:col-span-8">
          <div className="bg-white rounded-[40px] shadow-sm p-10 border border-gray-100 h-full min-h-[600px]">

            {activeMenu === '기본정보' && (
              <div className="space-y-8 h-full flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">계정 정보</h3>
                  <button 
                    onClick={() => setModalType('basic')}
                    className="text-xs font-bold text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer"
                  >
                    정보 수정
                  </button>
                </div>

                <div className="space-y-4">
                  {[
                    { label: '닉네임', value: basicInfo.nickname },
                    { label: '이메일 주소', value: basicInfo.email },
                  ].map((row) => (
                    <div key={row.label} className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px] border border-transparent hover:border-gray-100 transition-all">
                      <span className="text-sm text-gray-400 font-black">{row.label}</span>
                      <span className="text-base font-black text-gray-800">{row.value}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px] border border-transparent hover:border-gray-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">로그인 방식</span>
                    <div className="flex items-center gap-2 bg-yellow-400/10 px-3 py-1.5 rounded-full border border-yellow-400/20">
                      <span className="w-5 h-5 bg-yellow-400 rounded-full flex items-center justify-center text-[10px] font-black">K</span>
                      <span className="text-sm font-black text-yellow-700 uppercase tracking-tighter">{basicInfo.provider}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto pt-10 flex gap-4">
                  <button className="flex-1 bg-white border-2 border-gray-100 text-gray-400 py-5 rounded-[28px] text-sm font-black hover:bg-gray-50 hover:text-gray-600 transition-all active:scale-[0.98] cursor-pointer">
                    로그아웃
                  </button>
                  <button className="text-gray-300 text-xs font-bold px-6 hover:text-red-400 transition-all cursor-pointer">
                    회원탈퇴
                  </button>
                </div>
              </div>
            )}

            {activeMenu === '건강정보' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">나의 건강 프로필</h3>
                  <button 
                    onClick={() => setModalType('health')}
                    className="text-xs font-black text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer"
                  >
                    수정하기
                  </button>
                </div>
                <div className="grid sm:grid-cols-2 gap-6">
                  {[
                    { label: '나이', value: healthInfo.age },
                    { label: '키 / 몸무게', value: `${healthInfo.height}cm / ${healthInfo.weight}kg` },
                    { label: '보유 질환', value: healthInfo.diseases },
                    { label: '특이 알레르기', value: healthInfo.allergies },
                  ].map((item) => (
                    <div key={item.label} className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">{item.label}</p>
                      <p className="text-xl font-black text-gray-800">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeMenu === '가족관리' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">함께 관리하는 가족</h3>
                  <button 
                    onClick={() => {
                      setSelectedFamilyMember(null)
                      setModalType('family')
                    }}
                    className="bg-gray-900 text-white px-6 py-3 rounded-2xl text-sm font-black hover:bg-gray-700 transition-all active:scale-[0.95] cursor-pointer"
                  >
                    + 가족 추가하기
                  </button>
                </div>

                {family.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {family.map((member) => (
                      <div 
                        key={member.id} 
                        onClick={() => {
                          setSelectedFamilyMember(member)
                          setModalType('family')
                        }}
                        className="bg-slate-50 rounded-[32px] p-8 border border-transparent hover:border-gray-200 hover:bg-white hover:shadow-md transition-all flex justify-between items-center group cursor-pointer"
                      >
                        <div className="flex items-center gap-5">
                          <div className="w-16 h-16 bg-white rounded-[24px] flex items-center justify-center text-2xl font-black text-gray-700 shadow-sm group-hover:bg-gray-900 group-hover:text-white transition-all duration-300">
                            {member.name[0]}
                          </div>
                          <div>
                            <p className="text-lg font-black text-gray-800">{member.name}</p>
                            <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-widest">{member.relation}</p>
                          </div>
                        </div>
                        <button 
                          onClick={(e) => handleDeleteFamily(member.id, e)}
                          className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all shadow-sm cursor-pointer"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-20 bg-slate-50 rounded-[40px] border border-dashed border-slate-200">
                    <EmptyState
                      title="등록된 가족이 없어요"
                      message="가족의 복약도 함께 관리해보세요!"
                      actionLabel="가족 추가하기"
                      onAction={() => {
                        setSelectedFamilyMember(null)
                        setModalType('family')
                      }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 모달 렌더링 */}
      {modalType === 'basic' && (
        <BasicInfoModal 
          info={basicInfo} 
          onClose={() => setModalType(null)} 
          onSave={handleSaveBasic} 
        />
      )}
      {modalType === 'health' && (
        <HealthInfoModal 
          info={healthInfo} 
          onClose={() => setModalType(null)} 
          onSave={handleSaveHealth} 
        />
      )}
      {modalType === 'family' && (
        <FamilyModal 
          member={selectedFamilyMember} 
          onClose={() => {
            setModalType(null)
            setSelectedFamilyMember(null)
          }} 
          onSave={handleSaveFamily} 
        />
      )}

    </main>
  )
}
