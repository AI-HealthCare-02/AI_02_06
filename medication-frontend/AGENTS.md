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
├── out/                  # Static Export 빌드 결과물
├── public/               # Static Assets
└── package.json
```

## CRITICAL: JavaScript Only

**TypeScript를 사용하지 않습니다. 모든 파일은 `.jsx` 확장자를 사용합니다.**

- `.tsx` 파일 생성 금지
- `.ts` 파일 생성 금지
- 타입 어노테이션 (`: string`, `: number`, `: any` 등) 사용 금지
- 제네릭 타입 (`<T>`, `Array<string>` 등) 사용 금지
- `interface`, `type` 키워드 사용 금지

## Deployment: Static Export

Next.js를 **Static Export** 모드로 빌드합니다.

```javascript
// next.config.mjs
const nextConfig = {
  output: "export",        // 정적 파일만 생성
  trailingSlash: true,     // /page -> /page/index.html
  images: { unoptimized: true },
}
```

### 빌드 및 배포
```bash
# 빌드
npm run build
# -> out/ 폴더에 정적 파일 생성

# 배포
# Nginx가 out/ 폴더를 직접 서빙
```

### Static Export 제약사항
- `getServerSideProps` 사용 불가
- `middleware.ts` 사용 불가
- Next.js API Routes 사용 불가
- Image Optimization 사용 불가 (unoptimized: true)

## Technology Stack

- **Framework**: Next.js 16.2.2 (App Router, Static Export)
- **React**: 19.2.4
- **Styling**: Tailwind CSS v4
- **HTTP**: Axios with RTR interceptors
- **Notifications**: react-hot-toast

## Coding Conventions

### File Naming (JavaScript Only)
- Pages: `page.jsx`
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
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || '',
  withCredentials: true,  // HttpOnly Cookie 전송
})
```

### 환경별 API URL (루트 .env에서 설정)
```bash
# 로컬 개발 (ENV=local 또는 ENV=dev)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Docker 통합 / 프로덕션
NEXT_PUBLIC_API_BASE_URL=
# -> 비워두면 Nginx 프록시 사용 (/api/... -> FastAPI)
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
- `.tsx`, `.ts` 파일 생성 금지 (JavaScript Only)
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
인증 검증은 FastAPI에서 처리합니다.
- 인증 필요 API 호출 시 401 응답 -> 로그인 페이지로 리다이렉트
- 클라이언트에서 인증 상태 확인 후 UI 분기

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

## Development

### 로컬 개발
```bash
# 1. 루트 .env 설정 (환경변수 통합 관리)
# 프로젝트 루트에서 cp .env.example .env 후 필수 값 입력

# 2. 개발 서버 실행 (루트 .env 자동 로드)
npm run dev
# -> http://localhost:3000

# 3. 백엔드는 Docker로 실행
docker compose up fastapi redis
```

### 빌드 테스트
```bash
npm run build
npx serve out
# -> http://localhost:3000 에서 정적 파일 테스트
```
