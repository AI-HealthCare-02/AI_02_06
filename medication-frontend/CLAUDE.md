# Claude Guide - Frontend (Next.js)

## Your Role

프론트엔드의 복잡한 상태 관리, 아키텍처 결정, 컴포넌트 설계를 담당합니다.

## CRITICAL: JavaScript Only

**TypeScript를 사용하지 않습니다. 모든 파일은 `.jsx` 확장자를 사용합니다.**

- `.tsx` 파일 생성 금지
- `.ts` 파일 생성 금지
- 타입 어노테이션 (`: string`, `: number`, `: any` 등) 사용 금지
- 제네릭 타입 (`<T>`, `Array<string>` 등) 사용 금지
- `interface`, `type` 키워드 사용 금지

```javascript
// BAD - TypeScript 문법
const getUser = (id: string) => { ... }
const [data, setData] = useState<User | null>(null)

// GOOD - JavaScript 문법
const getUser = (id) => { ... }
const [data, setData] = useState(null)
```

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
3. 성능 최적화 포인트

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

## Complex Patterns

### Custom Hook for API
```javascript
function useApi(url) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
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
```javascript
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

- [ ] `.jsx` 확장자를 사용했는가?
- [ ] TypeScript 문법이 포함되지 않았는가?
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
- 리팩토링: Before/After 비교
