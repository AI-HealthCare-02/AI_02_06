'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { User, Activity, Users, Home, Trash2, X, Check, Plus, FileText, LogOut, Pencil } from 'lucide-react'
import EmptyState from '@/components/common/EmptyState'
import BottomNav from '@/components/layout/BottomNav'
import LogoutModal, { useLogout, DeleteAccountModal, useDeleteAccount } from '@/components/auth/LogoutModal'
import api, { handleApiError } from '@/lib/api'
import toast from 'react-hot-toast'
import { useProfile } from '@/contexts/ProfileContext'

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
        <div className="p-8 max-h-[70vh] overflow-y-auto">{children}</div>
        <div className="p-8 pt-4 flex gap-3">
          <button onClick={onClose} className="flex-1 py-4 rounded-2xl bg-gray-50 text-gray-500 font-bold hover:bg-gray-100 transition-all cursor-pointer">취소</button>
          <button onClick={onSave} className="flex-1 py-4 rounded-2xl bg-gray-900 text-white font-black hover:bg-gray-800 transition-all shadow-lg cursor-pointer">저장하기</button>
        </div>
      </div>
    </div>
  )
}

function BasicInfoModal({ info, onClose, onSave }) {
  const [formData, setFormData] = useState({ nickname: info?.name?.split('(')[0] || '' })
  return (
    <Modal title="계정 정보 수정" onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">닉네임</label>
          <input type="text" value={formData.nickname} onChange={(e) => setFormData({ nickname: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 border border-transparent focus:border-gray-200 focus:bg-white rounded-2xl outline-none font-bold text-gray-800 transition-all" />
        </div>
      </div>
    </Modal>
  )
}

function HealthInfoModal({ info, onClose, onSave }) {
  const [formData, setFormData] = useState({
    age: info?.age?.toString() || '',
    gender: info?.gender || 'MALE',
    height: info?.height?.toString() || '',
    weight: info?.weight?.toString() || '',
    is_smoking: info?.is_smoking ?? null,
    is_drinking: info?.is_drinking ?? null,
    conditions: info?.conditions || [],
    allergies: info?.allergies || [],
  })

  const btnSelected = 'bg-gray-900 text-white border-gray-900'
  const btnUnselected = 'bg-white text-gray-400 border-gray-100 hover:border-gray-300'
  const chipSelected = 'bg-gray-900 text-white border-gray-900'
  const chipUnselected = 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'

  return (
    <Modal title="건강 프로필 수정" onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">나이</label>
            <input type="text" inputMode="numeric" value={formData.age} placeholder="예: 30"
              onChange={(e) => {
                const val = e.target.value.replace(/[^0-9]/g, '');
                setFormData({...formData, age: val})
              }}
              className="w-full px-6 py-4 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800" />
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">성별</label>
            <div className="flex gap-2">
              {['MALE', 'FEMALE'].map(g => (
                <button key={g} type="button" onClick={() => setFormData({...formData, gender: g})}
                  className={`flex-1 py-4 rounded-2xl text-sm font-bold border transition-all cursor-pointer ${formData.gender === g ? btnSelected : btnUnselected}`}>
                  {g === 'MALE' ? '남성' : '여성'}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">키 (cm)</label>
            <input type="text" inputMode="decimal" value={formData.height} placeholder="예: 170"
              onChange={(e) => {
                const val = e.target.value.replace(/[^0-9]/g, '');
                setFormData({...formData, height: val})
              }}
              className="w-full px-6 py-4 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800" />
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">몸무게 (kg)</label>
            <input type="text" inputMode="decimal" value={formData.weight} placeholder="예: 65.5"
              onChange={(e) => {
                let val = e.target.value.replace(/[^0-9.]/g, '');
                const parts = val.split('.');
                if (parts.length > 2) val = parts[0] + '.' + parts.slice(1).join('');
                setFormData({...formData, weight: val})
              }}
              className="w-full px-6 py-4 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">흡연 여부</label>
            <div className="flex gap-2">
              {[true, false].map(v => (
                <button key={String(v)} type="button" onClick={() => setFormData({...formData, is_smoking: v})}
                  className={`flex-1 py-4 rounded-2xl text-sm font-bold border transition-all cursor-pointer ${formData.is_smoking === v ? btnSelected : btnUnselected}`}>
                  {v ? '예' : '아니오'}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 mb-2 block ml-1">음주 여부</label>
            <div className="flex gap-2">
              {[true, false].map(v => (
                <button key={String(v)} type="button" onClick={() => setFormData({...formData, is_drinking: v})}
                  className={`flex-1 py-4 rounded-2xl text-sm font-bold border transition-all cursor-pointer ${formData.is_drinking === v ? btnSelected : btnUnselected}`}>
                  {v ? '예' : '아니오'}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-3 block ml-1">기저질환</label>
          <div className="flex flex-wrap gap-2">
            {['고혈압', '당뇨', '고지혈증', '심장질환', '뇌졸중', '천식', '신장질환', '갑상선질환', '없음'].map(item => (
              <button key={item} type="button"
                onClick={() => {
                  let updated
                  if (item === '없음') {
                    updated = formData.conditions.includes(item) ? [] : ['없음']
                  } else {
                    const withoutNone = formData.conditions.filter(c => c !== '없음')
                    updated = withoutNone.includes(item) ? withoutNone.filter(c => c !== item) : [...withoutNone, item]
                  }
                  setFormData({...formData, conditions: updated})
                }}
                className={`px-4 py-2 rounded-full text-xs font-bold transition-all border cursor-pointer ${formData.conditions.includes(item) ? chipSelected : chipUnselected}`}>
                {item}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-3 block ml-1">알레르기</label>
          <div className="flex flex-wrap gap-2">
            {['페니실린', '아스피린', '항생제', '소염제', '없음'].map(item => (
              <button key={item} type="button"
                onClick={() => {
                  let updated
                  if (item === '없음') {
                    updated = formData.allergies.includes(item) ? [] : ['없음']
                  } else {
                    const withoutNone = formData.allergies.filter(a => a !== '없음')
                    updated = withoutNone.includes(item) ? withoutNone.filter(a => a !== item) : [...withoutNone, item]
                  }
                  setFormData({...formData, allergies: updated})
                }}
                className={`px-4 py-2 rounded-full text-xs font-bold transition-all border cursor-pointer ${formData.allergies.includes(item) ? chipSelected : chipUnselected}`}>
                {item}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  )
}

// 가족 관계 선택지 — 7종 (SELF 제외, OTHER 포함). 라벨 = ProfileContext 의 RELATION_LABELS 와 일치.
const FAMILY_RELATION_OPTIONS = [
  { value: 'FATHER', label: '아버지' },
  { value: 'MOTHER', label: '어머니' },
  { value: 'SON', label: '아들' },
  { value: 'DAUGHTER', label: '딸' },
  { value: 'HUSBAND', label: '남편' },
  { value: 'WIFE', label: '아내' },
  { value: 'OTHER', label: '기타' },
]

// relation_type → 기본 gender 매핑 (BE 의 RELATION_DEFAULT_GENDER 와 동기화)
const RELATION_GENDER_DEFAULT = {
  FATHER: 'MALE',
  MOTHER: 'FEMALE',
  SON: 'MALE',
  DAUGHTER: 'FEMALE',
  HUSBAND: 'MALE',
  WIFE: 'FEMALE',
}

function FamilyModal({ member, onClose, onSave }) {
  const [formData, setFormData] = useState(
    member
      ? { name: member.name, relation_type: member.relation_type, gender: member.gender || null }
      : { name: '', relation_type: 'FATHER', gender: 'MALE' }
  )

  // 관계 변경 시 gender 자동 default — 사용자가 별도로 다른 성별을 선택했으면 그 값 유지
  const handleRelationChange = (newRelation) => {
    const defaultGender = RELATION_GENDER_DEFAULT[newRelation] ?? null
    setFormData({ ...formData, relation_type: newRelation, gender: defaultGender })
  }

  return (
    <Modal title={member ? "가족 정보 수정" : "가족 추가하기"} onClose={onClose} onSave={() => onSave(formData)}>
      <div className="space-y-6">
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">이름</label>
          <input type="text" value={formData.name} placeholder="이름을 입력하세요" onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-6 py-4 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800" />
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">관계</label>
          <select
            value={formData.relation_type}
            onChange={(e) => handleRelationChange(e.target.value)}
            className="w-full px-6 py-4 bg-gray-50 rounded-2xl outline-none font-bold text-gray-800 appearance-none"
          >
            {FAMILY_RELATION_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-black text-gray-400 mb-2 block ml-1">성별</label>
          <div className="flex gap-3">
            {['MALE', 'FEMALE'].map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setFormData({ ...formData, gender: g })}
                className={`flex-1 py-4 rounded-2xl text-sm font-bold border transition-all cursor-pointer ${
                  formData.gender === g
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-gray-50 text-gray-500 border-gray-100 hover:bg-gray-100'
                }`}
              >
                {g === 'MALE' ? '남성' : '여성'}
              </button>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  )
}

function MyPageSkeleton() {
  return (
    <div className="max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50">
      <div className="h-32 bg-white rounded-[40px] mb-10 animate-pulse" />
      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-4 space-y-6"><div className="h-64 bg-white rounded-[40px] animate-pulse" /><div className="h-80 bg-white rounded-[40px] animate-pulse" /></div>
        <div className="md:col-span-8"><div className="h-full bg-white rounded-[40px] animate-pulse" /></div>
      </div>
    </div>
  )
}

export default function MyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const {
    selectedProfileId: profileId,
    selectedProfile,
    profiles,
    updateProfile,
    createProfile,
    deleteProfile,
    setSelectedProfileId,
    refetchProfiles,
  } = useProfile()
  const isInitialLoad = useRef(true)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeMenu, setActiveMenu] = useState('기본정보')
  // ProfileContext 의 데이터를 그대로 파생 사용 (single source of truth).
  // mutation 시 ProfileContext 가 in-place 갱신하므로 자동 리렌더.
  const userProfile = selectedProfile
  // 가족 관리 탭 = "내 모든 프로필" 뷰. SELF 도 포함해 표시하되 SELF 를 항상 맨 앞으로.
  const family = [...profiles].sort((a, b) => {
    if (a.relation_type === 'SELF') return -1
    if (b.relation_type === 'SELF') return 1
    return 0
  })
  const [ongoingCount, setOngoingCount] = useState(0)
  const [streakDays, setStreakDays] = useState(0)
  const [todayTakenCount, setTodayTakenCount] = useState(0)
  const [modalType, setModalType] = useState(null)
  const [selectedFamilyMember, setSelectedFamilyMember] = useState(null)

  // 가족 관계 enum 8종 단일 매핑 — gender 합성 없이 라벨 결정
  const relationLabels = {
    SELF: '본인',
    FATHER: '아버지',
    MOTHER: '어머니',
    SON: '아들',
    DAUGHTER: '딸',
    HUSBAND: '남편',
    WIFE: '아내',
    OTHER: '기타',
  }

  useEffect(() => {
    if (!profileId) return
    fetchData()
  }, [profileId])

  // 가족관리 탭은 모든 프로필 상태에서 표시되며 (HEAD 의 옵션 B fix), main 의 강제 탭
  // 전환 useEffect 는 의도와 어긋나 제거.

  // ProfileSwitcher 의 "프로필 추가" 버튼이 ?tab=family 로 진입하면 가족관리 탭 자동 활성화.
  // 활성화 직후 URL 의 ?tab= query 는 router.replace 로 정리 (history 오염 방지).
  useEffect(() => {
    if (searchParams.get('tab') === 'family') {
      setActiveMenu('가족관리')
      router.replace('/mypage')
    }
  }, [searchParams, router])

  // ProfileContext 가 이미 가진 profiles 재사용 — /profiles 와 /profiles/{id} GET 안 함.
  // 페이지 자체에서 GET 하는 건 챌린지/스트릭 같이 ProfileContext 가 모르는 데이터만.
  const fetchData = async () => {
    if (isInitialLoad.current) setIsLoading(true)
    else setIsRefreshing(true)
    try {
      // ProfileContext 가 profile / list 는 이미 fetch — 페이지는 챌린지/스트릭/오늘
      // 복약 같은 Context 외부 데이터만 호출.
      const [challengeRes, streakRes, todayLogsRes] = await Promise.all([
        api.get(`/api/v1/challenges?profile_id=${profileId}`),
        api.get(`/api/v1/intake-logs/streak?profile_id=${profileId}`),
        api.get(`/api/v1/intake-logs?profile_id=${profileId}`),
      ])
      setOngoingCount(challengeRes.data.filter(c => c.challenge_status === 'IN_PROGRESS').length)
      setStreakDays(streakRes.data.streak_days ?? 0)
      setTodayTakenCount((todayLogsRes.data || []).filter(l => l.intake_status === 'TAKEN').length)
    } catch (err) { handleApiError(err) } finally {
      setIsLoading(false)
      setIsRefreshing(false)
      isInitialLoad.current = false
    }
  }

  // mutation 핸들러는 ProfileContext 가 응답으로 in-place 갱신하므로 수동 fetchData 호출 안 함.
  // challenge/streak 데이터는 [profileId] effect 가 selectedProfileId 변경 시 자동 재조회 —
  // 활성 프로필 삭제 시 stale profileId 로 fetchData 가 호출되어 발생하던 404 경합 제거.

  const handleSaveBasic = async (newData) => {
    try {
      await updateProfile(userProfile.id, { name: newData.nickname })
      toast.success('닉네임이 수정되었습니다.')
      if (refetchProfiles) await refetchProfiles()
      setModalType(null)
    } catch (err) { handleApiError(err) }
  }

  const handleSaveHealth = async (newData) => {
    // [추가] 저장 전 최종 범위 검증 로직
    const h = parseInt(newData.height);
    const w = parseFloat(newData.weight);
    if (newData.height && (h < 50 || h > 250)) { toast.error("키는 50~250cm 사이로 입력해주세요."); return; }
    if (newData.weight && (w < 1 || w > 300)) { toast.error("몸무게는 1~300kg 사이로 입력해주세요."); return; }

    try {
      const healthSurvey = {
        age: parseInt(newData.age) || null,
        gender: newData.gender || null,
        height: h || null,
        weight: w || null,
        is_smoking: newData.is_smoking,
        is_drinking: newData.is_drinking,
        conditions: newData.conditions.length > 0 ? newData.conditions : null,
        allergies: newData.allergies.length > 0 ? newData.allergies : null,
      }
      // gender 는 별도 컬럼으로도 저장 (BE 의 Profile.gender) — health_survey.gender 와 dual write
      await updateProfile(userProfile.id, { health_survey: healthSurvey, gender: newData.gender || null })
      toast.success('건강 정보가 업데이트되었습니다.')
      setModalType(null)
    } catch (err) { handleApiError(err) }
  }

  const handleSaveFamily = async (newData) => {
    try {
      // BE 가 RELATION_DEFAULT_GENDER 로 자동 채우므로 gender 미지정 시 null 도 안전.
      // 사용자가 form 에서 성별 토글 변경 시 그 값이 그대로 BE 에 전송되어 우선됨.
      const payload = {
        name: newData.name,
        relation_type: newData.relation_type,
        gender: newData.gender,
      }
      if (selectedFamilyMember) {
        await updateProfile(selectedFamilyMember.id, payload)
        toast.success('가족 정보가 수정되었습니다.')
      } else {
        await createProfile({ ...payload, account_id: userProfile.account_id })
        toast.success('가족이 추가되었습니다.')
      }
      if (refetchProfiles) await refetchProfiles()
      setModalType(null)
      setSelectedFamilyMember(null)
    } catch (err) { handleApiError(err) }
  }

  const handleDeleteFamily = async (id, e) => {
    e.stopPropagation()
    if (!confirm('정말로 삭제하시겠습니까?')) return
    try {
      await deleteProfile(id)
      toast.success('삭제되었습니다.')
    } catch (err) { handleApiError(err) }
  }

  const { showLogoutModal, setShowLogoutModal, handleLogout } = useLogout()
  const { showDeleteModal, setShowDeleteModal, handleDeleteAccount } = useDeleteAccount()

  if (isLoading || !profileId) return <MyPageSkeleton />

  const menuItems = [
    { id: '기본정보', label: '기본 정보', icon: <User size={18} /> },
    { id: '건강정보', label: '건강 정보', icon: <Activity size={18} /> },
    { id: '가족관리', label: '가족 관리', icon: <Users size={18} /> },
  ]

  // 상세 관계 텍스트 — gender 합성 없이 enum 8종 단일 매핑
  const getDetailRelation = (profile) => {
    const rel = profile?.relation_type
    if (rel === 'SELF') return '본인 계정'
    return relationLabels[rel] ?? '가족'
  }

  return (
    <main className={`max-w-[1400px] mx-auto w-full px-8 py-12 min-h-screen bg-slate-50 relative transition-opacity duration-200 ${isRefreshing ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
      <div className="flex justify-between items-end mb-10 bg-white p-10 rounded-[40px] shadow-sm border border-gray-100">
        <div>
          <p className="text-gray-400 text-sm font-bold mb-2">내 설정 및 관리</p>
          <h1 className="text-4xl font-black text-gray-900">마이페이지</h1>
        </div>
        <div className="hidden md:flex items-center gap-10">
          <button onClick={() => router.push('/main')} className="flex items-center gap-2 text-gray-400 font-bold hover:text-gray-900 transition-all cursor-pointer"><Home size={18} /> 홈</button>
          <button className="flex items-center gap-2 text-gray-900 font-black"><User size={18} /> 마이페이지</button>
        </div>
      </div>

      <div className="grid md:grid-cols-12 gap-8">
        <div className="md:col-span-4 space-y-6">
          <div className="bg-white rounded-[40px] shadow-sm p-8 border border-gray-100">
            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-gray-900 rounded-full flex items-center justify-center shadow-lg mb-4 border-4 border-white"><User size={40} className="text-white" /></div>
              <h2 className="text-xl font-black text-gray-900 mb-1">{userProfile?.name.split('(')[0]}님</h2>
              {/* [수정] 상단 프로필 요약 관계 표시 상세화 */}
              <p className="text-gray-400 text-xs font-bold mb-6">{getDetailRelation(userProfile)}</p>
              <div className="grid grid-cols-3 gap-3 w-full">
                <div className="bg-gray-50 p-4 rounded-[24px] border border-gray-100">
                  <p className="text-[10px] font-black text-gray-500 mb-1">연속 복약</p>
                  <p className="text-lg font-black text-gray-800">{streakDays}일째 🔥</p>
                </div>
                <div className={`p-4 rounded-[24px] border ${todayTakenCount > 0 ? 'bg-green-50 border-green-100' : 'bg-gray-50 border-gray-100'}`}>
                  <p className={`text-[10px] font-black mb-1 ${todayTakenCount > 0 ? 'text-green-600' : 'text-gray-500'}`}>오늘 복약</p>
                  <p className="text-lg font-black text-gray-800">{todayTakenCount > 0 ? `${todayTakenCount}종 완료` : '-'}</p>
                </div>
                <div className="bg-orange-50 p-4 rounded-[24px] border border-orange-100">
                  <p className="text-[10px] font-black text-orange-500 mb-1">진행 챌린지</p>
                  <p className="text-lg font-black text-gray-800">{ongoingCount}개 🏆</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-[40px] shadow-sm p-4 border border-gray-100">
            <nav className="flex flex-col space-y-2">
              {menuItems.map((item) => (
                <button key={item.id} onClick={() => setActiveMenu(item.id)} className={`flex items-center gap-4 px-6 py-4 rounded-[24px] transition-all ${activeMenu === item.id ? 'bg-gray-900 text-white font-black shadow-lg' : 'text-gray-500 hover:bg-gray-50 font-bold'}`}>
                  <span>{item.icon}</span><span className="text-sm">{item.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        <div className="md:col-span-8">
          <div className="bg-white rounded-[40px] shadow-sm p-10 border border-gray-100 h-full min-h-[600px]">
            {activeMenu === '기본정보' && (
              <div className="space-y-8 h-full flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">계정 정보</h3>
                  <button onClick={() => setModalType('basic')} className="text-xs font-bold text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer">정보 수정</button>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px]">
                    <span className="text-sm text-gray-400 font-black">닉네임</span>
                    <span className="text-base font-black text-gray-800">{userProfile?.name.split('(')[0]}</span>
                  </div>
                  <div className="flex justify-between items-center p-6 bg-slate-50 rounded-[28px]">
                    <span className="text-sm text-gray-400 font-black">관계</span>
                    <div className="bg-blue-500/10 px-3 py-1.5 rounded-full border border-blue-500/20">
                      {/* [수정] 기본 정보 탭 관계 표시 상세화 */}
                      <span className="text-sm font-black text-blue-700">{getDetailRelation(userProfile).replace('부모님', '부모').replace('계정', '')}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-auto pt-10 space-y-6">
                  <button onClick={() => setShowLogoutModal(true)} className="w-full bg-white border-2 border-gray-100 text-gray-400 py-5 rounded-[28px] text-sm font-black hover:bg-gray-50 cursor-pointer transition-all">로그아웃</button>
                  <div className="flex items-center justify-center">
                    <button onClick={() => setShowDeleteModal(true)} className="text-xs text-gray-300 hover:text-red-400 transition-colors cursor-pointer underline underline-offset-2">회원 탈퇴</button>
                  </div>
                </div>
              </div>
            )}

            {activeMenu === '건강정보' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">건강 프로필</h3>
                  <button onClick={() => setModalType('health')} className="text-xs font-black text-gray-600 hover:bg-gray-100 px-4 py-2 rounded-xl transition-all border border-gray-200 cursor-pointer">수정하기</button>
                </div>
                <div className="grid sm:grid-cols-2 gap-6">
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">나이</p><p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.age ? `${userProfile.health_survey.age}세` : '-'}</p></div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">성별</p><p className="text-xl font-black text-gray-800">{(() => { const g = userProfile?.gender ?? userProfile?.health_survey?.gender; return g === 'MALE' ? '남성' : g === 'FEMALE' ? '여성' : '-' })()}</p></div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">키 / 몸무게</p><p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.height ? `${userProfile.health_survey.height}cm` : '-'} / {userProfile?.health_survey?.weight ? `${userProfile.health_survey.weight}kg` : '-'}</p></div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">흡연 / 음주</p><p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.is_smoking === true ? '흡연' : userProfile?.health_survey?.is_smoking === false ? '비흡연' : '-'} / {userProfile?.health_survey?.is_drinking === true ? '음주' : userProfile?.health_survey?.is_drinking === false ? '비음주' : '-'}</p></div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">보유 질환</p><p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.conditions?.join(', ') || '없음'}</p></div>
                  <div className="p-8 bg-slate-50 rounded-[32px] border border-slate-100"><p className="text-xs font-black text-gray-400 mb-2">특이 알레르기</p><p className="text-xl font-black text-gray-800">{userProfile?.health_survey?.allergies?.join(', ') || '없음'}</p></div>
                </div>
              </div>
            )}

            {activeMenu === '가족관리' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-2xl font-black text-gray-900">함께 관리하는 가족</h3>
                  <button onClick={() => { setSelectedFamilyMember(null); setModalType('family'); }} className="bg-gray-900 text-white px-6 py-3 rounded-2xl text-sm font-black hover:bg-gray-700 cursor-pointer">+ 가족 추가하기</button>
                </div>
                {family.length > 0 ? (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {family.map((member) => {
                      const isSelf = member.relation_type === 'SELF'
                      const isActive = member.id === profileId
                      // 카드 본체 클릭 = 프로필 전환. 편집/삭제는 stopPropagation 으로 분리.
                      const handleSwitchProfile = () => {
                        if (!isActive) setSelectedProfileId(member.id)
                      }
                      const handleEdit = (e) => {
                        e.stopPropagation()
                        if (isSelf) {
                          // 본인 정보 수정은 기본정보 탭의 BasicInfoModal 사용
                          setActiveMenu('기본정보')
                          return
                        }
                        setSelectedFamilyMember(member)
                        setModalType('family')
                      }
                      // 상세 호칭 — relation_type enum 8종 단일 매핑 (gender 합성 없음)
                      const detailLabel = relationLabels[member.relation_type] ?? '가족'
                      return (
                        <div
                          key={member.id}
                          onClick={handleSwitchProfile}
                          className={`relative rounded-[32px] p-8 transition-all flex justify-between items-center group cursor-pointer ${
                            isActive
                              ? 'bg-white shadow-lg ring-2 ring-blue-500'
                              : isSelf
                                ? 'bg-blue-50 hover:bg-blue-100 border border-blue-200'
                                : 'bg-slate-50 hover:bg-white hover:shadow-md'
                          }`}
                        >
                          {isActive && (
                            <span className="absolute top-3 right-3 bg-blue-500 text-white text-[10px] font-black px-2.5 py-1 rounded-full flex items-center gap-1">
                              <Check size={11} />현재 활성
                            </span>
                          )}
                          <div className="flex items-center gap-5">
                            <div className={`w-16 h-16 rounded-[24px] flex items-center justify-center text-2xl font-black transition-all ${isSelf ? 'bg-blue-500 text-white' : 'bg-white text-gray-700 group-hover:bg-gray-900 group-hover:text-white'}`}>{member.name[0]}</div>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-lg font-black text-gray-800">{member.name}</p>
                                {isSelf && <span className="bg-blue-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full">본인</span>}
                              </div>
                              <p className="text-xs font-bold text-gray-400 uppercase">{detailLabel}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleEdit}
                              aria-label={isSelf ? '본인 정보 수정' : '가족 정보 수정'}
                              className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-400 hover:text-gray-900 shadow-sm cursor-pointer"
                            >
                              <Pencil size={16} />
                            </button>
                            {!isSelf && (
                              <button
                                onClick={(e) => handleDeleteFamily(member.id, e)}
                                aria-label="가족 삭제"
                                className="w-10 h-10 bg-white rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 shadow-sm cursor-pointer"
                              >
                                <Trash2 size={18} />
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="py-20 bg-slate-50 rounded-[40px] border border-dashed border-slate-200">
                    <EmptyState title="등록된 가족이 없어요" message="우측 상단의 버튼을 눌러 가족을 추가해보세요!" />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {modalType === 'basic' && <BasicInfoModal info={userProfile} onClose={() => setModalType(null)} onSave={handleSaveBasic} />}
      {modalType === 'health' && <HealthInfoModal info={userProfile?.health_survey} onClose={() => setModalType(null)} onSave={handleSaveHealth} />}
      {modalType === 'family' && <FamilyModal member={selectedFamilyMember} onClose={() => { setModalType(null); setSelectedFamilyMember(null); }} onSave={handleSaveFamily} />}
      {showLogoutModal && <LogoutModal onClose={() => setShowLogoutModal(false)} onConfirm={handleLogout} />}
      {showDeleteModal && <DeleteAccountModal onClose={() => setShowDeleteModal(false)} onConfirm={handleDeleteAccount} />}
      <BottomNav />
    </main>
  )
}
