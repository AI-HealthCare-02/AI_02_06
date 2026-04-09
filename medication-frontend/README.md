# Downforce - Frontend

AI 기반 지능형 복약 관리 시스템의 프론트엔드입니다.
Next.js 15 (App Router) 기반으로 구성되어 있습니다.

## 기술 스택

- **Framework**: Next.js 15 (App Router)
- **Language**: JavaScript (`.jsx` 전용, TypeScript 사용 안 함)
- **Styling**: Tailwind CSS v4
- **HTTP**: Axios (RTR 인터셉터 포함)
- **Icons**: lucide-react
- **Notifications**: react-hot-toast

## 디렉터리 구조

```
src/
├── app/                  # App Router 페이지
│   ├── layout.jsx        # 루트 레이아웃
│   ├── page.jsx          # 랜딩 페이지
│   ├── login/            # 카카오 OAuth 로그인
│   ├── main/             # 대시보드
│   ├── mypage/           # 마이페이지 (계정/건강/가족 관리)
│   ├── ocr/              # 처방전 OCR 등록
│   ├── medication/       # 복약 가이드
│   ├── challenge/        # 건강 챌린지
│   └── survey/           # 건강 설문
├── components/           # 공유 컴포넌트
│   ├── Navigation.jsx    # 상단 네비게이션
│   ├── BottomNav.jsx     # 하단 모바일 네비게이션
│   ├── LogoutModal.jsx   # 로그아웃/회원탈퇴 모달
│   └── EmptyState.jsx    # 빈 상태 UI
└── lib/
    ├── api.js            # Axios 인스턴스 + 에러 핸들러
    └── tokenManager.js   # RTR 토큰 갱신 관리
```

## 로컬 실행

```bash
cd medication-frontend
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 접속

## Docker 실행

```bash
# 프로젝트 루트에서
docker compose up -d
```

## 코드 규칙

- 파일 확장자는 `.jsx`만 사용 (`.ts`, `.tsx` 금지)
- TypeScript 문법 사용 금지 (`interface`, `type`, `: string` 등)
- 컴포넌트 파일명: `PascalCase.jsx`
- API 호출은 `src/lib/api.js`의 인스턴스만 사용
- 인라인 스타일 금지 (Tailwind CSS 사용)
- 이모지 사용 금지

## 인증 방식

- 카카오 OAuth 로그인 후 JWT를 HttpOnly Cookie로 관리
- API 호출 시 쿠키가 자동 전송됨 (`withCredentials: true`)
- 토큰 만료 시 `lib/tokenManager.js`가 자동으로 갱신 (RTR)
