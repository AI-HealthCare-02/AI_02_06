# Claude Guide - Frontend (Next.js)

## Your Role

프론트엔드의 복잡한 상태 관리, 아키텍처 결정, TypeScript 마이그레이션을 담당합니다.

## Thinking Process

### 새 페이지 구현 시
1. 라우트 구조 결정 (`/feature` vs `/feature/[id]`)
2. 서버/클라이언트 컴포넌트 분리
3. 데이터 페칭 전략 (SSR vs CSR)
4. 로딩/에러 상태 설계
5. 접근성 고려

### 리팩토링 시
1. 재사용 가능한 컴포넌트 식별
2. Custom Hook 추출 가능 여부
3. 타입 안정성 개선
4. 성능 최적화 포인트

## Architecture Decisions

### Why App Router?
- Server Components 기본 지원
- Nested Layouts
- Streaming / Suspense

### Why No Global State Library?
- 현재 규모에서 불필요
- API 상태는 useEffect + useState로 충분
- 필요 시 React Context로 확장

### CSR vs SSR 가이드라인
- **SSR**: SEO 필요, 정적 콘텐츠
- **CSR**: 인증 필요, 동적 데이터

## TypeScript Migration Strategy

### Phase 1: Config
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true
  }
}
```

### Phase 2: Core Types
```typescript
// src/types/api.ts
interface Profile {
  id: string
  name: string
  relation_type: 'SELF' | 'PARENT' | 'CHILD' | 'SPOUSE' | 'OTHER'
}

interface Medication {
  id: string
  medicine_name: string
  intake_times: string[]
}
```

### Phase 3: Component Props
```typescript
interface CardProps {
  title: string
  children: React.ReactNode
  onClick?: () => void
}
```

## Complex Patterns

### Custom Hook for API
```typescript
function useApi<T>(url: string) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    api.get(url)
      .then(res => setData(res.data))
      .catch(setError)
      .finally(() => setIsLoading(false))
  }, [url])

  return { data, error, isLoading }
}
```

### Error Boundary
```typescript
'use client'

class ErrorBoundary extends React.Component {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback />
    }
    return this.props.children
  }
}
```

## Code Quality Checklist

- [ ] TypeScript 타입이 명시적인가?
- [ ] 컴포넌트가 단일 책임을 가지는가?
- [ ] 접근성 속성 (aria-*, role) 적용됐는가?
- [ ] 로딩/에러 상태 처리됐는가?
- [ ] 메모이제이션 필요한가? (useMemo, useCallback)

## Performance Considerations

### Image Optimization
```jsx
import Image from 'next/image'

<Image
  src="/image.png"
  alt="Description"
  width={300}
  height={200}
  priority  // LCP 이미지
/>
```

### Code Splitting
```jsx
import dynamic from 'next/dynamic'

const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <Skeleton />,
  ssr: false
})
```

## Response Format

- 아키텍처 변경: 근거와 트레이드오프 설명
- 타입 정의: 전체 타입 파일 제공
- 리팩토링: Before/After 비교
