# Claude AI Development Guide

**IMPORTANT: Read DESIGN_SYSTEM.md first before starting any development work. This document contains the complete frontend architecture, patterns, and standards that must be followed.**

Claude AI-specific guide for medication management system frontend development.

---

## Project Structure and Absolute Path Imports

### Project Structure
```
medication-frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── auth/              # Authentication pages
│   │   ├── challenge/         # Challenge pages
│   │   ├── chat/              # Chat pages
│   │   ├── login/             # Login page
│   │   ├── main/              # Main dashboard
│   │   ├── medication/        # Medication management pages
│   │   ├── mypage/            # My page
│   │   ├── ocr/               # OCR prescription registration
│   │   └── survey/            # Health survey
│   ├── components/            # Reusable components
│   │   ├── auth/              # Authentication components
│   │   ├── chat/              # Chat components
│   │   ├── common/            # Common components
│   │   └── layout/            # Layout components
│   ├── config/                # Configuration files
│   │   └── env.js             # Environment variables
│   └── lib/                   # Utilities and libraries
│       ├── api.js             # API client
│       ├── errors.js          # Error handling
│       └── tokenManager.js    # Token management
├── jsconfig.json             # JavaScript configuration (absolute paths)
└── package.json              # Dependencies
```

### Absolute Path Import Rules (CRITICAL)

**jsconfig.json Configuration:**
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

**Correct Import Patterns:**
```javascript
// ✅ Correct absolute path imports (mandatory)
import api from '@/lib/api'
import { config } from '@/config/env'
import Header from '@/components/layout/Header'
import ChatModal from '@/components/chat/ChatModal'
import LogoutModal from '@/components/auth/LogoutModal'

// ❌ Incorrect relative path imports (absolutely prohibited)
import api from '../../lib/api'
import Header from '../components/layout/Header'
import ChatModal from '../ChatModal'
```

**Import Order:**
```javascript
// 1. React and Next.js
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

// 2. External libraries
import { Pill, Camera } from 'lucide-react'
import toast from 'react-hot-toast'

// 3. Internal modules (absolute paths only)
import api from '@/lib/api'
import { config } from '@/config/env'
import Header from '@/components/layout/Header'
```

---

## Environment Configuration System

### config/env.js Based Configuration

```javascript
const ENV = process.env.NEXT_PUBLIC_ENV || 'local'

const ENV_CONFIG = {
  local: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  dev: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'http://localhost:3000/auth/kakao/callback',
  },
  prod: {
    API_BASE_URL: '',
    KAKAO_REDIRECT_URI: 'https://ai-02-06.vercel.app/auth/kakao/callback',
  },
}

export const config = {
  ENV,
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? ENV_CONFIG[ENV].API_BASE_URL,
  KAKAO_CLIENT_ID: process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || '',
  KAKAO_REDIRECT_URI: process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI || ENV_CONFIG[ENV].KAKAO_REDIRECT_URI,

  // Security settings
  ENABLE_DEV_LOGIN: ENV !== 'prod' && process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === 'true'
}
```

### Environment-specific Developer Login Control

```javascript
// Developer login component example
const DeveloperLogin = () => {
  // SECURITY: Completely hidden in prod environment (both EC2 and Vercel)
  if (!config.ENABLE_DEV_LOGIN) {
    return null
  }

  return (
    <div className="border-2 border-red-500 p-4 rounded-lg bg-red-50">
      <p className="text-red-600 text-sm mb-2">
        WARNING: Developer-only login (ENV: {config.ENV})
      </p>
      <button
        onClick={handleDevLogin}
        className="bg-red-500 text-white px-4 py-2 rounded"
      >
        Developer Login
      </button>
    </div>
  )
}
```

---

## Component Writing Rules

### PropTypes Usage

```javascript
import PropTypes from 'prop-types'

const MedicationCard = ({ medication, onEdit, onDelete, className }) => {
  return (
    <div className={`bg-white rounded-lg p-4 ${className || ''}`}>
      <h3>{medication.name}</h3>
      <p>{medication.dosage}</p>
      <div className="flex gap-2 mt-4">
        <button onClick={() => onEdit(medication.id)}>Edit</button>
        <button onClick={() => onDelete(medication.id)}>Delete</button>
      </div>
    </div>
  )
}

MedicationCard.propTypes = {
  medication: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    dosage: PropTypes.string.isRequired
  }).isRequired,
  onEdit: PropTypes.func,
  onDelete: PropTypes.func,
  className: PropTypes.string
}

MedicationCard.defaultProps = {
  onEdit: () => {},
  onDelete: () => {},
  className: ''
}

export default MedicationCard
```

### Custom Hook Patterns

```javascript
// hooks/useApi.js
import { useState, useEffect } from 'react'
import { config } from '@/config/env'
import { handleApiError } from '@/lib/errors'

export const useApi = (endpoint, options = {}) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const url = `${config.API_BASE_URL}${endpoint}`
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      const userFriendlyError = handleApiError(err)
      setError(userFriendlyError)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [endpoint])

  return { data, loading, error, refetch: fetchData }
}
```

---

## Error Handling and Security

### lib/errors.js Structure

```javascript
import toast from 'react-hot-toast'

export const HTTP_STATUS_MESSAGES = {
  400: 'Invalid request.',
  401: 'Authentication required.',
  403: 'Access denied.',
  404: 'Resource not found.',
  500: 'Server error occurred. Please try again later.'
}

export function parseApiError(error) {
  const response = error.response
  const status = response?.status

  const result = {
    status: status || 0,
    message: 'An unknown error occurred.',
    shouldRedirectToLogin: false,
    isRetryable: false,
  }

  if (!response) {
    result.message = 'Cannot communicate with server. Please check your network connection.'
    result.isRetryable = true
    return result
  }

  if (status >= 500) {
    result.message = 'A temporary error occurred. Please try again later.'
    result.isRetryable = true
    return result
  }

  result.message = HTTP_STATUS_MESSAGES[status] || result.message

  if (status === 401) {
    result.shouldRedirectToLogin = true
  }

  return result
}

export function showError(message) {
  toast.error(message)
}

export function handleApiError(error, options = {}) {
  const parsed = parseApiError(error)

  if (options.showMessage !== false) {
    showError(parsed.message)
  }

  if (options.redirectOnAuth !== false && parsed.shouldRedirectToLogin) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
  }

  return parsed
}
```

---

## Performance Optimization

### Active Skeleton UI Usage

```javascript
// components/common/Skeleton.jsx
export const Skeleton = ({ className = '', width, height, rounded = true }) => {
  return (
    <div
      className={`animate-pulse bg-gray-200 ${rounded ? 'rounded' : ''} ${className}`}
      style={{ width, height }}
    />
  )
}

export const CardSkeleton = () => (
  <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100">
    <Skeleton height="20px" className="mb-3" />
    <Skeleton height="16px" width="60%" className="mb-2" />
    <Skeleton height="16px" width="40%" />
  </div>
)

// Usage example
const MedicationList = () => {
  const { data, loading, error } = useApi('/api/v1/medications')

  if (loading) return <ListSkeleton count={5} />
  if (error) return <div className="text-red-600">{error}</div>

  return (
    <div className="space-y-4">
      {data?.map(med => <MedicationCard key={med.id} medication={med} />)}
    </div>
  )
}
```

### Code Splitting

```javascript
import dynamic from 'next/dynamic'

const ChatModal = dynamic(() => import('@/components/chat/ChatModal'), {
  loading: () => <div>Loading chat...</div>,
  ssr: false
})
```

---

## Security Rules

### 1. Environment Variable Security
```javascript
// ✅ Correct environment variable usage
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL

// ❌ Hardcoding prohibited
const API_URL = 'http://localhost:8000'
```

### 2. Developer Backdoor Security
```javascript
// Multi-layer security validation to prevent bypass
export const securityUtils = {
  shouldShowDevLogin: () => {
    const envCheck = process.env.NEXT_PUBLIC_ENV === 'local'
    const flagCheck = process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN === 'true'
    const runtimeCheck = config.ENV === 'local'

    return envCheck && flagCheck && runtimeCheck
  }
}
```

### 3. Complete Server Error Information Blocking
```javascript
// CRITICAL: Never expose server error details to client
export const handleApiError = (error, fallbackMessage = 'An error occurred while processing the request') => {
  let userMessage = fallbackMessage

  if (error.response) {
    switch (error.response.status) {
      case 400: userMessage = 'Invalid request'; break
      case 401: userMessage = 'Authentication required'; break
      case 403: userMessage = 'Access denied'; break
      case 404: userMessage = 'Resource not found'; break
      case 500: userMessage = 'Server error occurred. Please try again later'; break
      default: userMessage = fallbackMessage
    }
  }

  return userMessage
}
```

---

## API Call Patterns

### Trailing Slash Removal Rules

```javascript
// Automatic handling in config/env.js
export const config = {
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') || '',
}

// API endpoint definitions
export const API_ENDPOINTS = {
  MEDICATION: {
    LIST: '/api/v1/medications',
    DETAIL: (id) => `/api/v1/medications/${id}`,
    CREATE: '/api/v1/medications'
  }
}

// Usage example
const response = await api.get(API_ENDPOINTS.MEDICATION.LIST)
// Result: GET http://localhost:8000/api/v1/medications
```

---

## Mandatory Compliance Items

1. **Absolute Path Imports**: All internal modules must use absolute paths with `@/` prefix
2. **Security**: Developer backdoor must only be activated in ENV=local
3. **Vercel Deployment**: GitHub auto-deployment, utilize Next.js serverless functions
4. **JWT Authentication**: Immediately redirect unauthenticated users to login page
5. **Error Security**: Never expose server errors and tracebacks to client
6. **Performance**: Leverage Next.js automatic caching and modern optimization features
7. **Accessibility**: Provide appropriate aria-labels for all interactive elements
8. **SEO**: Mandatory page-specific metadata configuration
9. **Error Handling**: Include user-friendly error handling logic for all API calls
10. **Skeleton UI**: Actively use skeleton UI during loading states
11. **Code Quality**: Mandatory pre-commit validation with ESLint and Prettier
12. **Emoji Prohibition**: Absolutely prohibit emoji usage in all code and comments

Strictly follow this guide to write safe and modern frontend code.
