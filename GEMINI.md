# Gemini Guide - Project Root

## Your Role

프로젝트 전체의 인프라 및 DevOps 작업을 빠르게 처리합니다.

## Strengths to Leverage

1. **Docker/Compose 설정 생성**: 새 서비스 추가, healthcheck 설정
2. **스크립트 자동화**: 배포 스크립트, CI/CD 워크플로우
3. **보일러플레이트 생성**: 새 서비스 scaffold
4. **문서 템플릿**: README, API 문서 초안

## Task Patterns

### Docker Service 추가 시
```yaml
# 항상 포함할 것:
# 1. healthcheck
# 2. depends_on with condition
# 3. networks
# 4. restart policy (prod: unless-stopped, dev: no)
```

### CI/CD 워크플로우 작성 시
```yaml
# .github/workflows/ 에 생성
# 필수 단계: lint -> test -> build -> deploy
```

## Quick Commands

```bash
# 개발 환경 시작
docker compose up -d

# 프로덕션 배포
docker compose -f docker-compose.prod.yml up -d

# 로그 확인
docker compose logs -f [service]

# 이미지 빌드
docker compose build [service]
```

## Output Format

- 설정 파일: 전체 파일 내용 제공
- 스크립트: 실행 가능한 완전한 코드
- 주석: 간결하게, 핵심만

## Do NOTs

- 프로덕션 compose에 포트 직접 노출하지 않기
- secrets를 파일에 하드코딩하지 않기
- `restart: always` 대신 `unless-stopped` 사용
