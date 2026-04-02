// API 설정

import axios from 'axios'

// 모든 API 요청의 기본 설정
const api = axios.create({
  baseURL: 'http://localhost:8000',  // 영빈님 BE 서버 주소!!
  withCredentials: true,             // 쿠키 자동 포함 (토큰용)
})

export default api