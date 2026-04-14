# GitHub Secrets 설정 가이드

GitHub Actions에서 EC2 자동 배포를 위한 Secrets 설정 방법입니다.

## 필요한 Secrets

| Secret 이름 | 값 | 설명 |
|-------------|-----|------|
| `EC2_HOST` | `52.78.62.12` | EC2 퍼블릭 IP |
| `EC2_USER` | `ubuntu` | SSH 사용자명 |
| `EC2_SSH_KEY` | (SSH 프라이빗 키 내용) | downforce-key.pem 내용 |

## 설정 방법

### 1. GitHub 레포지토리 Settings 접속

```
GitHub 레포지토리 → Settings → Secrets and variables → Actions
```

![Secrets 위치](https://docs.github.com/assets/cb-28266/mw-1440/images/help/repository/repo-actions-settings.webp)

### 2. New repository secret 클릭

### 3. Secrets 추가

#### EC2_HOST
```
Name: EC2_HOST
Secret: 52.78.62.12
```

#### EC2_USER
```
Name: EC2_USER
Secret: ubuntu
```

#### EC2_SSH_KEY (중요)

1. 로컬에서 `downforce-key.pem` 파일 내용 복사:

**Windows (PowerShell):**
```powershell
Get-Content .\downforce-key.pem | Set-Clipboard
```

**Mac/Linux:**
```bash
cat downforce-key.pem | pbcopy  # Mac
cat downforce-key.pem | xclip   # Linux
```

2. GitHub에 붙여넣기:
```
Name: EC2_SSH_KEY
Secret: (복사한 키 내용 붙여넣기)
```

**주의**: 키 내용은 아래와 같은 형식이어야 합니다:
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...
-----END RSA PRIVATE KEY-----
```

## 설정 확인

Secrets가 제대로 설정되면 아래처럼 보입니다:

```
Repository secrets (3)

EC2_HOST        Updated 방금 전
EC2_USER        Updated 방금 전
EC2_SSH_KEY     Updated 방금 전
```

## 보안 주의사항

1. **SSH 키 관리**
   - 가능하면 배포 전용 SSH 키를 별도로 생성하는 것이 좋습니다
   - 기존 키를 사용해도 되지만, 유출 시 위험이 있습니다

2. **접근 권한**
   - Secrets는 레포지토리 Admin만 설정/확인 가능
   - Actions 로그에는 `***`로 마스킹됨

3. **Fork 보안**
   - Fork된 레포지토리에서는 Secrets에 접근 불가

## (선택) 배포 전용 SSH 키 생성

더 안전하게 하려면 배포 전용 키를 생성:

```bash
# 로컬에서 새 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -C "github-actions-deploy"

# EC2에 공개키 추가
ssh -i downforce-key.pem ubuntu@52.78.62.12
echo "공개키내용" >> ~/.ssh/authorized_keys

# GitHub Secrets에는 deploy_key (프라이빗 키) 등록
```

## (선택) Discord/Slack 알림 추가

배포 실패 시 알림을 받으려면:

### Discord Webhook
1. Discord 서버 → 채널 설정 → 연동 → 웹후크 생성
2. 웹후크 URL 복사
3. GitHub Secrets에 `DISCORD_WEBHOOK` 추가
4. `deploy.yml`의 notify-failure 단계 주석 해제

### Slack Webhook
1. Slack App 생성 → Incoming Webhooks 활성화
2. 웹후크 URL 복사
3. GitHub Secrets에 `SLACK_WEBHOOK` 추가

## 테스트

설정 완료 후 테스트:

1. 아무 파일이나 수정
2. main 브랜치에 push
3. GitHub → Actions 탭에서 워크플로우 실행 확인
4. 배포 성공/실패 확인

## 문제 해결

### "Permission denied (publickey)" 에러
- EC2_SSH_KEY 값이 올바른지 확인
- 키 내용 앞뒤 공백 제거
- `-----BEGIN` ~ `-----END` 전체가 포함되어야 함

### "Host key verification failed" 에러
- 첫 배포 전 수동으로 한 번 SSH 접속하여 호스트 키 등록
- 또는 deploy.yml에 `StrictHostKeyChecking=no` 옵션 추가 (보안상 비추천)

### 테스트는 통과하는데 배포 실패
- EC2에 Docker가 설치되어 있는지 확인
- EC2에 프로젝트가 clone되어 있는지 확인
- EC2 Security Group에서 22번 포트(SSH) 허용 확인
