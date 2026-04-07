'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { handleApiError } from '../../lib/api'
import toast from 'react-hot-toast'

function MyPageSkeleton() {
  return (
    <div className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50">
      <div className="h-32 bg-white rounded-[40px] mb-10 animate-pulse" />
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-4 space-y-6">
          <div className="h-64 bg-white rounded-[40px] animate-pulse" />
          <div className="h-80 bg-white rounded-[40px] animate-pulse" />
        </div>
        <div className="md:col-span-8">
          <div className="h-full bg-white rounded-[40px] animate-pulse" />
        </div>
      </div>
    </div>
  )
}

export default function MyPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [activeMenu, setActiveMenu] = useState('기본정보')
  const [userProfile, setUserProfile] = useState(null)
  const [family, setFamily] = useState([])
  const [ongoingCount, setOngoingCount] = useState(0)
  
  // 수정 모드 상태
  const [isEditingHealth, setIsEditingEditingHealth] = useState(false)
  const [healthForm, setHealthForm] = useState({
    age: '',
    gender: '',
    conditions: [],
    allergies: []
  })

  // 한글 입력 및 쉼표 처리를 위한 임시 문자열 상태
  const [condStr, setCondStr] = useState('')
  const [allerStr, setAllerStr] = useState('')

  // 가족 추가 모달 상태
  const [showAddFamily, setShowAddFamily] = useState(false)
  const [familyForm, setFamilyForm] = useState({
    name: '',
    relation_type: 'OTHER'
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setIsLoading(true)
      // 1. 프로필 정보 조회
      const res = await api.get('/api/v1/profiles/')
      const allProfiles = res.data
      
      const self = allProfiles.find(p => p.relation_type === 'SELF') || allProfiles[0]
      setUserProfile(self)
      
      // 건강 정보 폼 초기화
      if (self?.health_survey) {
        setHealthForm({
          age: self.health_survey.age || '',
          gender: self.health_survey.gender || '',
          conditions: self.health_survey.conditions || [],
          allergies: self.health_survey.allergies || []
        })
      }
      
      const others = allProfiles.filter(p => p.relation_type !== 'SELF')
      setFamily(others)

      // 2. 챌린지 개수 조회
      try {
        const challengeRes = await api.get('/api/v1/challenges/')
        setOngoingCount(challengeRes.data.length)
      } catch (e) {
        console.error('챌린지 로드 실패:', e)
      }

    } catch (err) {
      handleApiError(err)
    } finally {
      setIsLoading(false)
    }
  }

  // 건강 정보 수정 저장
  const handleUpdateHealth = async () => {
    try {
      // 1. 특수문자 제거 정규식 (한글, 영문, 숫자, 쉼표만 허용)
      const cleanRegex = /[^a-zA-Z0-9가-힣ㄱ-ㅎㅏ-ㅣ,]/g
      
      // 2. 임시 문자열을 정제하고 배열로 변환
      const finalConditions = condStr.replace(cleanRegex, '').split(',').filter(Boolean)
      const finalAllergies = allerStr.replace(cleanRegex, '').split(',').filter(Boolean)

      const cleanedForm = {
        ...healthForm,
        conditions: finalConditions,
        allergies: finalAllergies
      }
      
      await api.patch(`/api/v1/profiles/${userProfile.id}`, {
        health_survey: cleanedForm
      })
      toast.success('건강 정보가 업데이트되었습니다. ✨')
      setIsEditingEditingHealth(false)
      fetchData() // 데이터 새로고침
    } catch (err) {
      handleApiError(err)
    }
  }

  // 가족 추가 저장
  const handleAddFamily = async () => {
    if (!familyForm.name.trim()) {
      toast.error('이름을 입력해주세요.')
      return
    }
    try {
      await api.post('/api/v1/profiles/', {
        account_id: userProfile.account_id,
        name: familyForm.name,
        relation_type: familyForm.relation_type,
        health_survey: {}
      })
      toast.success(`${familyForm.name}님이 등록되었습니다. 👨‍👩‍👧‍👦`)
      setShowAddFamily(false)
      setFamilyForm({ name: '', relation_type: 'OTHER' })
      fetchData()
    } catch (err) {
      handleApiError(err)
    }
  }

  // 로그아웃 핸들러
  const handleLogout = async () => {
    try {
      await api.post('/api/v1/auth/logout')
      router.push('/')
    } catch (err) {
      console.error('로그아웃 실패:', err)
      router.push('/')
    }
  }

  if (isLoading) return <MyPageSkeleton />

  const menuItems = [
    { id: '기본정보', label: '기본 정보', icon: '👤' },
    { id: '건강정보', label: '건강 정보', icon: '🏥' },
    { id: '가족관리', label: '가족 관리', icon: '👨‍👩‍👧‍👦' },
  ]

  const stats = {
    streak: 3, 
    challenges: ongoingCount
  }

  const relationLabels = {
    SELF: '본인',
    PARENT: '부모님',
    CHILD: '자녀',
    SPOUSE: '배우자',
    OTHER: '기타'
  }

  return (
    <main className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative overflow-x-hidden">
      
      {/* 상단 헤더 영역 */}
      <div className="flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-white">
        <div>
          <p className="text-gray-400 text-sm font-bold mb-2 px-1">내 설정 및 관리</p>
          <h1 className="text-4xl font-black text-gray-900 leading-tight">마이페이지</h1>
        </div>
        
        <div className="hidden md:flex items-center gap-12 mb-2">
          <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-gray-400 font-bold text-lg hover:text-blue-500 transition-all">
            <span className="text-2xl">🏠</span> 홈
          </button>
          <button onClick={() => router.push('/mypage')} className="flex items-center gap-2 text-blue-500 font-black text-lg hover:opacity-80 transition-all">
            <span className="text-2xl">👤</span> 마이페이지
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-12 gap-8">
        
        {/* [좌측 영역] 프로필 요약 및 세로 메뉴 */}
        <div className="md:col-span-4 flex flex-col space-y-6">
          <div className="bg-white rounded-[40px] shadow-sm p-8 border border-white/50 animate-in fade-in slide-in-from-left-3 duration-500">
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center text-4xl shadow-lg shadow-blue-100 mb-4 border-4 border-white">
                👤
              </div>
              <h2 className="text-xl font-black text-gray-900 mb-1">{userProfile?.name.split('(')[0]}님</h2>
              <p className="text-gray-400 text-xs font-bold mb-6 italic">{userProfile?.relation_type === 'SELF' ? '본인 계정' : '사용자'}</p>
              
              <div className="grid grid-cols-2 gap-3 w-full">
                <div className="bg-blue-50/50 p-4 rounded-[24px] border border-blue-50">
                  <p className="text-[10px] font-black text-blue-500 mb-1">연속 복약</p>
                  <p className="text-lg font-black text-gray-800">{stats.streak}일째 🔥</p>
                </div>
                <div className="bg-orange-50/50 p-4 rounded-[24px] border border-orange-50">
                  <p className="text-[10px] font-black text-orange-500 mb-1">진행 챌린지</p>
                  <p className="text-lg font-black text-gray-800">{stats.challenges}개 🏆</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[40px] shadow-sm p-4 border border-white/50 animate-in fade-in slide-in-from-left-3 duration-700">
            <nav className="flex flex-col space-y-2">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveMenu(item.id)}
                  className={`flex items-center gap-4 px-6 py-4 rounded-[24px] transition-all
                    ${activeMenu === item.id 
                      ? 'bg-blue-500 text-white shadow-lg shadow-blue-100 font-black' 
                      : 'text-gray-400 hover:bg-slate-50 font-bold'}`}
                >
                  <span className="text-xl">{item.icon}</span>
                  <span className="text-sm">{item.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* [우측 영역] 상세 설정 컨텐츠 */}
        <div className="md:col-span-8">
          <div className="bg-white rounded-[40px] shadow-sm p-12 border border-white/50 h-full min-h-[600px] animate-in fade-in slide-in-from-right-3 duration-500">
            
            {/* 1. 기본 정보 */}
            {activeMenu === '기본정보' && (
              <div className="h-full flex flex-col">
                <div className="flex justify-between items-center mb-10">
                  <h2 className="text-2xl font-black text-gray-900">기본 정보</h2>
                </div>

                <div className="space-y-6">
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">닉네임</span>
                    <span className="text-base font-black text-gray-800">{userProfile?.name.split('(')[0]}</span>
                  </div>
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">프로필 ID</span>
                    <span className="text-xs font-mono text-gray-500">{userProfile?.id}</span>
                  </div>
                  <div className="flex justify-between items-center p-6 bg-slate-50/50 rounded-[28px] border border-transparent hover:border-slate-100 transition-all">
                    <span className="text-sm text-gray-400 font-black">관계</span>
                    <div className="flex items-center gap-2 bg-blue-500/10 px-3 py-1.5 rounded-full border border-blue-500/20">
                      <span className="text-sm font-black text-blue-700 uppercase tracking-tighter">{relationLabels[userProfile?.relation_type] || userProfile?.relation_type}</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto pt-10 flex gap-4">
                  <button onClick={handleLogout} className="flex-1 bg-white border-2 border-slate-100 text-gray-400 py-5 rounded-[28px] text-sm font-black hover:bg-slate-50 hover:text-gray-600 transition-all active:scale-[0.98]">
                    로그아웃
                  </button>
                </div>
              </div>
            )}

            {/* 2. 건강 정보 */}
            {activeMenu === '건강정보' && (
              <div className="h-full flex flex-col">
                <div className="flex justify-between items-center mb-10">
                  <h2 className="text-2xl font-black text-gray-900">건강 정보</h2>
                  {!isEditingHealth ? (
                    <button 
                      onClick={() => {
                        setCondStr(userProfile?.health_survey?.conditions?.join(',') || '')
                        setAllerStr(userProfile?.health_survey?.allergies?.join(',') || '')
                        setIsEditingEditingHealth(true)
                      }}
                      className="text-xs font-black text-blue-500 bg-blue-50 px-5 py-2.5 rounded-2xl hover:bg-blue-100 transition-all">
                      수정하기
                    </button>
                  ) : (
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setIsEditingEditingHealth(false)}
                        className="text-xs font-black text-gray-400 bg-gray-50 px-5 py-2.5 rounded-2xl hover:bg-gray-100 transition-all">
                        취소
                      </button>
                      <button 
                        onClick={handleUpdateHealth}
                        className="text-xs font-black text-white bg-blue-500 px-5 py-2.5 rounded-2xl hover:bg-blue-600 transition-all">
                        저장하기
                      </button>
                    </div>
                  )}
                </div>

                {isEditingHealth ? (
                  <div className="space-y-8">
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <label className="text-xs font-black text-gray-400 mb-2 block px-1">나이</label>
                        <input 
                          type="number" 
                          value={healthForm.age}
                          onChange={(e) => setHealthForm({...healthForm, age: e.target.value})}
                          className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-black text-gray-400 mb-2 block px-1">성별</label>
                        <select 
                          value={healthForm.gender}
                          onChange={(e) => setHealthForm({...healthForm, gender: e.target.value})}
                          className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                        >
                          <option value="MALE">남성</option>
                          <option value="FEMALE">여성</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-black text-gray-400 mb-3 block px-1">보유 질환 (쉼표로 구분)</label>
                      <input 
                        type="text" 
                        value={condStr}
                        onChange={(e) => setCondStr(e.target.value.replace(/\s/g, ''))}
                        placeholder="고혈압,당뇨 등"
                        className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-black text-gray-400 mb-3 block px-1">알레르기 (쉼표로 구분)</label>
                      <input 
                        type="text" 
                        value={allerStr}
                        onChange={(e) => setAllerStr(e.target.value.replace(/\s/g, ''))}
                        placeholder="페니실린,아스피린 등"
                        className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-6">
                    <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">나이</p>
                      <p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.age || '-'}세</p>
                    </div>
                    <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">성별</p>
                      <p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.gender === 'MALE' ? '남성' : '여성'}</p>
                    </div>
                    <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">보유 질환</p>
                      <p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.conditions?.join(', ') || '없음'}</p>
                    </div>
                    <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100">
                      <p className="text-xs font-black text-gray-400 mb-2">특이 알레르기</p>
                      <p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.allergies?.join(', ') || '없음'}</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 3. 가족 관리 */}
            {activeMenu === '가족관리' && (
              <div className="h-full flex flex-col">
                <div className="flex justify-between items-center mb-10">
                  <h2 className="text-2xl font-black text-gray-900">가족 관리</h2>
                  <button 
                    onClick={() => setShowAddFamily(true)}
                    className="text-xs font-black text-white bg-blue-500 px-5 py-2.5 rounded-2xl hover:bg-blue-600 shadow-lg shadow-blue-100 transition-all">
                    + 가족 추가
                  </button>
                </div>

                {family.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {family.map((member) => (
                      <div key={member.id} className="p-6 bg-slate-50 rounded-[32px] border border-transparent hover:bg-white hover:border-slate-100 hover:shadow-2xl hover:shadow-slate-200 transition-all group flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center text-2xl shadow-sm group-hover:bg-blue-50 transition-colors">
                            👤
                          </div>
                          <div>
                            <p className="text-lg font-black text-gray-800">{member.name}</p>
                            <p className="text-xs font-bold text-gray-400 mt-1 uppercase tracking-widest">{relationLabels[member.relation_type] || member.relation_type}</p>
                          </div>
                        </div>
                        <button className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all shadow-sm">
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-20 bg-slate-50/50 rounded-[40px] border border-dashed border-slate-200 flex flex-col items-center justify-center">
                    <EmptyState 
                      title="등록된 가족이 없어요" 
                      message="가족의 복약도 함께 관리해보세요!" 
                      actionLabel="가족 추가하기"
                      onAction={() => setShowAddFamily(true)}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 가족 추가 모달 */}
      {showAddFamily && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100] flex items-center justify-center p-6">
          <div className="bg-white rounded-[40px] w-full max-w-md p-10 animate-in zoom-in-95 duration-300">
            <h3 className="text-2xl font-black text-gray-900 mb-8">가족 추가하기</h3>
            <div className="space-y-6">
              <div>
                <label className="text-xs font-black text-gray-400 mb-2 block px-1">이름</label>
                <input 
                  type="text" 
                  value={familyForm.name}
                  onChange={(e) => setFamilyForm({...familyForm, name: e.target.value})}
                  placeholder="가족의 성함을 입력하세요"
                  className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                />
              </div>
              <div>
                <label className="text-xs font-black text-gray-400 mb-2 block px-1">관계</label>
                <select 
                  value={familyForm.relation_type}
                  onChange={(e) => setFamilyForm({...familyForm, relation_type: e.target.value})}
                  className="w-full bg-slate-50 border-none rounded-2xl p-4 text-sm font-bold focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                >
                  <option value="PARENT">부모</option>
                  <option value="CHILD">자녀</option>
                  <option value="SPOUSE">배우자</option>
                  <option value="OTHER">기타</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-10">
              <button 
                onClick={() => setShowAddFamily(false)}
                className="flex-1 py-4 rounded-2xl text-sm font-black text-gray-400 bg-gray-50 hover:bg-gray-100 transition-all">
                취소
              </button>
              <button 
                onClick={handleAddFamily}
                className="flex-1 py-4 rounded-2xl text-sm font-black text-white bg-blue-500 hover:bg-blue-600 shadow-lg shadow-blue-100 transition-all">
                추가 완료
              </button>
            </div>
          </div>
        </div>
      )}

      <BottomNav />
    </main>
  )
}
