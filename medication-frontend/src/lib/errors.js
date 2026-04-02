/**
 * API 에러 처리 모듈
 *
 * BE에서 정의된 HTTP 상태 코드 및 에러 코드를 중앙에서 관리합니다.
 */

// HTTP 상태 코드별 기본 메시지
export const HTTP_STATUS_MESSAGES = {
  400: '잘못된 요청입니다.',
  401: '인증이 필요합니다.',
  403: '접근 권한이 없습니다.',
  404: '요청한 리소스를 찾을 수 없습니다.',
  422: '입력값이 올바르지 않습니다.',
  429: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.',
  500: '서버 오류가 발생했습니다.',
  502: '서버와 통신할 수 없습니다.',
  503: '서비스를 일시적으로 사용할 수 없습니다.',
}

// BE에서 정의된 에러 코드별 메시지
export const ERROR_CODE_MESSAGES = {
  // OAuth 관련
  invalid_request: '잘못된 요청입니다.',
  account_disabled: '비활성화된 계정입니다. 고객센터에 문의해주세요.',
  rate_limit_exceeded: '요청 횟수를 초과했습니다. 잠시 후 다시 시도해주세요.',
  network_error: '서버와 통신할 수 없습니다. 네트워크 연결을 확인해주세요.',
  token_exchange_failed: '로그인 처리 중 오류가 발생했습니다.',
  userinfo_failed: '사용자 정보를 가져올 수 없습니다.',

  // 인증 관련
  token_expired: '로그인이 만료되었습니다. 다시 로그인해주세요.',
  invalid_token: '유효하지 않은 인증입니다. 다시 로그인해주세요.',

  // 카카오 에러 코드
  KOE010: '인증 정보가 올바르지 않습니다.',
  KOE320: '인가 코드가 만료되었거나 유효하지 않습니다.',
}

// 에러 코드별 동작 정의
export const ERROR_ACTIONS = {
  // 로그인 페이지로 리다이렉트가 필요한 에러
  REDIRECT_TO_LOGIN: ['token_expired', 'invalid_token'],

  // 재시도 가능한 에러
  RETRYABLE: ['network_error', 'rate_limit_exceeded'],
}

/**
 * API 에러 객체를 파싱하여 사용자 친화적인 메시지를 반환합니다.
 */
export function parseApiError(error) {
  const response = error.response
  const status = response?.status
  const data = response?.data

  // 기본 에러 객체
  const result = {
    status: status || 0,
    code: null,
    message: '알 수 없는 오류가 발생했습니다.',
    shouldRedirectToLogin: false,
    isRetryable: false,
    raw: data,
  }

  // 네트워크 에러 (응답 없음)
  if (!response) {
    result.code = 'network_error'
    result.message = ERROR_CODE_MESSAGES.network_error
    result.isRetryable = true
    return result
  }

  // detail 객체에서 에러 코드 추출
  const detail = data?.detail
  if (detail) {
    // detail이 객체인 경우 { error, error_description }
    if (typeof detail === 'object') {
      result.code = detail.error || detail.error_code
      result.message = detail.error_description
        || ERROR_CODE_MESSAGES[result.code]
        || detail.msg
        || HTTP_STATUS_MESSAGES[status]
        || result.message
    }
    // detail이 문자열인 경우
    else if (typeof detail === 'string') {
      result.message = detail
    }
  } else {
    // detail이 없는 경우 HTTP 상태 코드 기반 메시지
    result.message = HTTP_STATUS_MESSAGES[status] || result.message
  }

  // 에러 코드에 따른 동작 결정
  if (result.code) {
    result.shouldRedirectToLogin = ERROR_ACTIONS.REDIRECT_TO_LOGIN.includes(result.code)
    result.isRetryable = ERROR_ACTIONS.RETRYABLE.includes(result.code)
  }

  // 401은 항상 로그인 페이지로 리다이렉트
  if (status === 401) {
    result.shouldRedirectToLogin = true
  }

  return result
}

/**
 * 에러를 사용자에게 표시합니다.
 * (Toast 라이브러리 연동 시 이 함수를 수정)
 */
export function showError(message) {
  // TODO: Toast 라이브러리 연동 시 교체
  alert(message)
}

/**
 * API 에러를 처리하고 적절한 동작을 수행합니다.
 */
export function handleApiError(error, options = {}) {
  const {
    showMessage = true,
    redirectOnAuth = true,
  } = options

  const parsed = parseApiError(error)

  // 에러 메시지 표시
  if (showMessage) {
    showError(parsed.message)
  }

  // 인증 에러 시 로그인 페이지로 리다이렉트
  if (redirectOnAuth && parsed.shouldRedirectToLogin) {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  return parsed
}
