#!/bin/bash
# =============================================================================
# Project Downforce - AWS EC2 (Ubuntu 24.04) 서버 초기화 스크립트
# 목적: Docker 및 Docker Compose V2 설치, PostgreSQL 컨테이너 자동 시작 환경 구성
# 실행: chmod +x setup_server.sh && sudo ./setup_server.sh
# =============================================================================

set -e

echo "[1/6] 시스템 패키지 업데이트"
sudo apt-get update
sudo apt-get upgrade -y

echo "[2/6] 필수 패키지 설치"
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "[3/6] Docker 공식 GPG 키 추가"
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "[4/6] Docker 저장소 추가"
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "[5/6] Docker Engine 및 Docker Compose V2 설치"
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[6/6] Docker 서비스 활성화 및 시작"
sudo systemctl enable docker
sudo systemctl start docker

# 현재 사용자를 docker 그룹에 추가 (sudo 없이 docker 명령 실행 가능)
sudo usermod -aG docker $USER

echo "============================================="
echo "Docker 설치 완료"
echo "Docker 버전: $(docker --version)"
echo "Docker Compose 버전: $(docker compose version)"
echo "============================================="
echo ""
echo "[중요] docker 그룹 적용을 위해 로그아웃 후 재로그인하거나 다음 명령 실행:"
echo "  newgrp docker"
echo ""
echo "[다음 단계] PostgreSQL 컨테이너 시작:"
echo "  cd /path/to/project && docker compose up -d"
