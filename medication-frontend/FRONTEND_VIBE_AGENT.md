# FRONTEND VIBE AGENT - Downforce 프론트엔드 협업 가이드

> 역할: UI/UX 디자이너 겸 프론트엔드 담당자용 에이전트
> 핵심 원칙: 엄격함보다 속도와 유저 경험(UX)에 집중

> **코드 규칙 및 아키텍처 원칙**: [CLAUDE.md](./CLAUDE.md) 참조
> **프레임워크 규칙 및 API 패턴**: [AGENTS.md](./AGENTS.md) 참조

---

## 1. 디렉토리 구조

```
medication-frontend/src/
├── app/
│   ├── main/page.jsx          # 메인 대시보드
│   ├── medication/page.jsx    # 약품 목록
│   ├── challenge/page.jsx     # 챌린지 (API 연결 완료)
│   ├── chat/page.jsx          # AI 상담 채팅 (더미)
│   ├── ocr/page.jsx           # 처방전 촬영
│   ├── ocr/loading/page.jsx   # OCR 로딩
│   ├── ocr/result/page.jsx    # OCR 결과 (더미)
│   ├── survey/page.jsx        # 건강 설문
│   ├── mypage/page.jsx        # 마이페이지
│   └── auth/kakao/callback/page.jsx
├── components/
│   ├── Navigation.jsx         # 상단 네비게이션
│   ├── BottomNav.jsx          # 하단 네비게이션 (모바일)
│   ├── Header.jsx             # 페이지 헤더
│   ├── EmptyState.jsx         # 빈 상태 UI
│   └── LogoutModal.jsx        # 로그아웃 확인 모달
└── lib/
    ├── api.js                 # axios 인스턴스 (항상 이걸로 요청)
    ├── tokenManager.js        # RTR 토큰 갱신 처리
    └── errors.js              # 에러 파싱 및 토스트 처리
```

---

## 2. API 연결 현황 (더미 데이터 목록)

| 페이지 | 더미 항목 | 연결해야 할 API |
|--------|---------|--------------|
| main/page.jsx | 오늘 복약 현황 | `GET /api/v1/intake-logs/?profile_id=...&target_date=오늘` |
| main/page.jsx | 챌린지 진행 상황 | `GET /api/v1/challenges/?profile_id=...&active_only=true` |
| main/page.jsx | ChatModal 챗봇 응답 | `POST /api/v1/messages/ask` |
| medication/page.jsx | 약물 상세 정보 전체 | `GET /api/v1/medications/{id}` |
| chat/page.jsx | AI 챗봇 응답 전체 | `POST /api/v1/messages/ask` |
| ocr/result/page.jsx | OCR 인식 결과 | sessionStorage 파싱 개선 |
| ocr/loading/page.jsx | OCR 업로드 버그 | `api` import 누락 수정 |
| mypage/page.jsx | 연속 복약 통계 "3일째" | intake-logs 집계 |
| Navigation.jsx | ChatModal 챗봇 응답 | `POST /api/v1/messages/ask` |

---

## 3. API 엔드포인트 치트시트

```javascript
// 프로필 목록 (항상 먼저 호출해서 profile_id 얻기)
api.get('/api/v1/profiles/')
// -> profiles.find(p => p.relation_type === 'SELF') || profiles[0]

// 오늘 복약 기록
api.get('/api/v1/intake-logs/', { params: { profile_id, target_date: '2026-04-13' } })

// 복용 완료/스킵 처리
api.post(`/api/v1/intake-logs/${logId}/take`)
api.post(`/api/v1/intake-logs/${logId}/skip`)

// 약품 목록
api.get('/api/v1/medications/', { params: { profile_id, active_only: true } })

// 챌린지 목록
api.get('/api/v1/challenges/', { params: { profile_id } })

// AI 챗봇 질문 + 응답
api.post('/api/v1/messages/ask', { session_id, content: '사용자 메시지' })
// -> { user_message: {...}, assistant_message: {...} }

// 채팅 세션 생성
api.post('/api/v1/chat-sessions/', { profile_id, title: '복약 상담' })

// OCR 업로드
api.post('/api/v1/ocr/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
```

---

## 4. 프로젝트 공통 컴포넌트 사용법

### Header
```jsx
<Header title="페이지 제목" subtitle="서브타이틀 (선택)" showBack={true} />
```

### EmptyState
```jsx
<EmptyState
  title="내용이 없어요"
  message="새로운 항목을 추가해보세요!"
  onAction={() => router.push('/somewhere')}
  actionLabel="추가하기"
/>
```

### 토스트 알림
```javascript
import toast from 'react-hot-toast'
import { showError } from '../../lib/api'

toast.success('성공 메시지')
showError('에러 메시지')
```

### BottomNav 가림 방지
```jsx
<main className="min-h-screen bg-gray-50 pb-24">
```

---

## 5. 페이지 기본 뼈대 (복붙용)

```jsx
'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '../../components/Header'
import BottomNav from '../../components/BottomNav'
import EmptyState from '../../components/EmptyState'
import api, { showError } from '../../lib/api'
import toast from 'react-hot-toast'

export default function FeaturePage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [data, setData] = useState([])
  const [profileId, setProfileId] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true)

        // profile_id 먼저 확보
        const profileRes = await api.get('/api/v1/profiles/')
        const profiles = profileRes.data
        if (!profiles || profiles.length === 0) {
          router.replace('/survey')
          return
        }
        const self = profiles.find(p => p.relation_type === 'SELF') || profiles[0]
        setProfileId(self.id)

        // 실제 데이터 조회
        const res = await api.get('/api/v1/something/', { params: { profile_id: self.id } })
        setData(res.data)
      } catch (err) {
        if (err.response?.status !== 401) {
          showError('데이터를 불러오는데 실패했습니다.')
        }
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [router])

  if (isLoading) {
    return (
      <main className="min-h-screen bg-gray-50 pb-24">
        <Header title="페이지 제목" showBack={true} />
        <div className="max-w-3xl mx-auto px-6 py-6 space-y-4 animate-pulse">
          {[1, 2, 3].map(i => <div key={i} className="bg-white rounded-2xl h-24 w-full" />)}
        </div>
        <BottomNav />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 pb-24">
      <Header title="페이지 제목" showBack={true} />
      <div className="max-w-3xl mx-auto px-6 py-6">
        {data.length === 0 ? (
          <EmptyState title="내용이 없어요" message="새로 추가해보세요!" />
        ) : (
          <div className="space-y-4">
            {data.map(item => (
              <div key={item.id} className="bg-white rounded-2xl shadow-sm p-6">
                {/* 카드 내용 */}
              </div>
            ))}
          </div>
        )}
      </div>
      <BottomNav />
    </main>
  )
}
```

---

## 6. AI 챗봇 연결 패턴

더미 응답을 실제 API로 교체할 때 사용:

```javascript
const handleSend = async () => {
  if (!input.trim() || isLoading) return
  const content = input.trim()
  setInput('')

  setMessages(prev => [...prev, { role: 'user', content }])
  setIsLoading(true)

  try {
    // 세션이 없으면 먼저 생성
    let sid = sessionId
    if (!sid) {
      const sessionRes = await api.post('/api/v1/chat-sessions/', {
        profile_id: profileId,
        title: content.slice(0, 20),
      })
      sid = sessionRes.data.id
      setSessionId(sid)
    }

    const res = await api.post('/api/v1/messages/ask', { session_id: sid, content })
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: res.data.assistant_message.content,
    }])
  } catch (err) {
    if (err.response?.status !== 401) {
      showError(err.parsed?.message || 'AI 응답을 받지 못했습니다.')
    }
  } finally {
    setIsLoading(false)
  }
}
```

---

## 7. 새 피처 추가 체크리스트

- [ ] `profile_id` 먼저 조회한 후 다른 API 호출했는가
- [ ] 401 에러는 조건부 무시했는가 (`status !== 401`)
- [ ] 로딩 상태 (스켈레톤) 처리했는가
- [ ] 빈 상태 (`EmptyState`) 처리했는가
- [ ] `pb-24` 있어서 BottomNav에 안 가리는가

---

> 최종 업데이트: 2026-04-13
