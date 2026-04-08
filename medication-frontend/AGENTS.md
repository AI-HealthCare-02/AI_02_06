<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Frontend (Next.js) - AI Assistant Guide

## Architecture

```
medication-frontend/
├── src/
│   ├── app/              # App Router (Pages)
│   │   ├── layout.js     # Root Layout
│   │   ├── page.js       # Landing Page
│   │   ├── login/        # Auth Pages
│   │   ├── main/         # Dashboard
│   │   ├── medication/   # Drug Details
│   │   ├── ocr/          # Prescription OCR
│   │   ├── chat/         # AI Consultation
│   │   ├── challenge/    # Health Challenges
│   │   ├── survey/       # Health Survey
│   │   └── mypage/       # User Settings
│   ├── components/       # Shared Components
│   └── lib/              # Utilities
│       ├── api.js        # Axios + RTR
│       ├── errors.js     # Error Handling
│       └── tokenManager.js
├── middleware.ts         # RS256 JWT 검증
├── public/               # Static Assets
└── package.json
```

## Security Architecture (Zero Trust + RS256)

### Next.js 보안 역할: UI Gatekeeper

Next.js는 서비스의 첫 번째 방어선으로, 비로그인 사용자를 입구에서 차단합니다.

| 항목 | Next.js (Frontend) | FastAPI (Backend) |
|------|-------------------|-------------------|
| **역할** | 세션 인증 Gatekeeper | 리소스 인증 + 최종 인가 |
| **책임** | UI 자산 보호, 입장 통제 | 데이터 무결성, 최후의 보루 |
| **키 유형** | RS256 Public Key | RS256 Private Key |
| **검증 수준** | 서명 유효성 (Authentication) | 재인증 + 소유권 (Authorization) |

> Next.js는 UI 진입을 위한 신분증 확인을, FastAPI는 실제 금고 내부 데이터에 대한 열람 권한 확인을 담당합니다.

### 미들웨어 도입 이유

1. **UX 최적화**: 브라우저 단 리다이렉트 시 발생하는 스켈레톤 UI 깜빡임 차단
2. **공격 표면 축소**: 비로그인 사용자에게 JS 코드(API 주소, 서비스 구조) 노출 방지
3. **리소스 필터링**: 무의미한 가짜 요청이 백엔드까지 도달하지 않도록 경량 필터 역할

### middleware.ts 구현 요구사항

```typescript
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import jwt from 'jsonwebtoken'

const PUBLIC_KEY = process.env.JWT_PUBLIC_KEY!

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token')?.value

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  try {
    // jwt.verify()가 수행하는 검증:
    // 1. 위조 판별 (Signature Verification) - 서명 불일치 시 실패
    // 2. 만료 검증 (Expiration Check) - exp 클레임 초과 시 실패
    // 3. Algorithm Pinning - HS256 교체 공격 차단
    jwt.verify(token, PUBLIC_KEY, { algorithms: ['RS256'] })
    return NextResponse.next()
  } catch {
    // 위조되었거나 만료된 토큰 -> 로그인 페이지로 리다이렉트
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = {
  matcher: ['/main/:path*', '/mypage/:path*', '/medication/:path*']
}
```

### 핵심 보안 키워드

- **RS256**: 비대칭 키 알고리즘 (Public Key로 검증만 가능)
- **HttpOnly Cookie**: XSS 공격으로부터 토큰 보호
- **Zero Trust**: 모든 요청을 의심, 매번 검증
- **Algorithm Pinning**: `algorithms: ['RS256']` 명시로 HS256 교체 공격 차단

## Technology Stack

- **Framework**: Next.js 16.2.2 (App Router)
- **React**: 19.2.4
- **Styling**: Tailwind CSS v4
- **HTTP**: Axios with RTR interceptors
- **Notifications**: react-hot-toast

## Coding Conventions

### File Naming
- Pages: `page.jsx` or `page.tsx`
- Components: `PascalCase.jsx`
- Utilities: `camelCase.js`

### Component Structure
```jsx
// 1. Imports
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

// 2. Component
export default function MyComponent() {
  // 3. Hooks
  const router = useRouter()
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // 4. Effects
  useEffect(() => {
    fetchData()
  }, [])

  // 5. Handlers
  const handleClick = () => {}

  // 6. Render
  if (isLoading) return <Skeleton />

  return <div>...</div>
}
```

### Tailwind Patterns
```jsx
// Button
className="bg-blue-500 text-white px-6 py-3 rounded-xl font-bold
           hover:bg-blue-600 active:scale-[0.98] transition-all"

// Card
className="bg-white rounded-2xl shadow-sm p-6 border border-gray-100"

// Responsive Grid
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
```

## API Integration

### JWT Cookie 기반 인증
```jsx
// Cookie는 브라우저가 자동으로 전송
// withCredentials: true 설정 필요
const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,  // HttpOnly Cookie 전송
})
```

### Data Fetching Pattern
```jsx
useEffect(() => {
  const fetchData = async () => {
    try {
      setIsLoading(true)
      const res = await api.get('/api/v1/items')
      setData(res.data)
    } catch (err) {
      showError(err.parsed?.message || 'Failed to load')
    } finally {
      setIsLoading(false)
    }
  }
  fetchData()
}, [])
```

### Error Handling
```jsx
import { showError } from '@/lib/errors'

try {
  await api.post('/api/v1/items', data)
} catch (err) {
  showError(err)  // Displays toast notification
}
```

## Do NOTs

- `'use client'` 없이 hooks 사용 금지
- API URL 하드코딩 금지 (`/api/v1/...` 사용)
- `console.log` 프로덕션 코드에 남기기 금지
- 인라인 스타일 사용 금지 (Tailwind 사용)
- `any` 타입 사용 금지 (TypeScript 파일)
- localStorage에 JWT 저장 금지 -> HttpOnly Cookie 사용

## State Management

- 전역 상태: 필요 시 React Context
- 서버 상태: useEffect + useState
- 폼 상태: useState
- URL 상태: useSearchParams

## Routing

### Navigation
```jsx
import { useRouter } from 'next/navigation'

const router = useRouter()
router.push('/main')
router.back()
```

### Protected Routes
- 인증 필요 페이지: `/main`, `/mypage`, `/medication` 등 (middleware.ts에서 처리)
- 공개 페이지: `/`, `/login`

## Loading States

```jsx
// Skeleton UI
if (isLoading) {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
    </div>
  )
}
```

## Docker Deployment

Next.js는 **독립 Docker 컨테이너(Node.js 서버)**로 배포합니다.

- Static Export 아님 (middleware.ts 사용을 위해)
- 서버 사이드 보안 제어 가능
- UX 깜빡임 없는 리다이렉트

```dockerfile
# Dockerfile.prod 예시
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV NODE_ENV=production
EXPOSE 3000
CMD ["node", "server.js"]
```
