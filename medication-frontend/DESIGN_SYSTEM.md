# Frontend Design System

Frontend design system and development guide for the medication management system.

---

## Project Structure

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
├── public/                    # Static files
├── jsconfig.json             # JavaScript configuration (absolute paths)
├── next.config.mjs           # Next.js configuration
├── package.json              # Dependencies
└── tailwind.config.js        # Tailwind CSS configuration
```

---

## Import Rules (Absolute Paths)

### jsconfig.json Configuration
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

### Import Patterns
```javascript
// ✅ Correct absolute path imports
import api from '@/lib/api'
import { config } from '@/config/env'
import Header from '@/components/layout/Header'
import ChatModal from '@/components/chat/ChatModal'
import LogoutModal from '@/components/auth/LogoutModal'

// ❌ Incorrect relative path imports (prohibited)
import api from '../../lib/api'
import Header from '../components/layout/Header'
```

### Import Order Rules
```javascript
// 1. React and Next.js
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

// 2. External libraries
import { Pill, Camera, MessageCircle } from 'lucide-react'
import toast from 'react-hot-toast'

// 3. Internal modules (absolute paths only)
import api from '@/lib/api'
import { config } from '@/config/env'
import Header from '@/components/layout/Header'
import ChatModal from '@/components/chat/ChatModal'
```

---

## Component Architecture

### 1. Page Components (app/ folder)
```javascript
// app/main/page.jsx
'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import Header from '@/components/layout/Header'

export default function MainPage() {
  // Page logic
  return (
    <main>
      <Header title="Main" />
      {/* Page content */}
    </main>
  )
}
```

### 2. Layout Components (components/layout/)
```javascript
// components/layout/Navigation.jsx
'use client'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Home, Pill } from 'lucide-react'

export default function Navigation() {
  // Navigation logic
}
```

### 3. Feature Components (components/[feature]/)
```javascript
// components/chat/ChatModal.jsx
'use client'
import { useState, useEffect } from 'react'
import { X, Send } from 'lucide-react'
import api from '@/lib/api'

export default function ChatModal({ onClose, profileId }) {
  // Chat modal logic
}
```

---

## Environment Configuration System

### config/env.js Structure
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
}
```

### Environment-specific Usage
```javascript
import { config } from '@/config/env'

// API calls
const response = await fetch(`${config.API_BASE_URL}/api/v1/medications`)

// Environment-specific branching
if (config.ENV === 'local') {
  // Local development features
}
```

---

## API Client System

### lib/api.js Structure
```javascript
import axios from 'axios'
import { config } from '@/config/env'
import { parseApiError } from './errors'

const api = axios.create({
  baseURL: config.API_BASE_URL,
  withCredentials: true,
  timeout: 10000,
})

// Request/Response interceptors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Token refresh on 401 errors
    // Error parsing and handling
    return Promise.reject(error)
  }
)

export default api
```

### Usage Patterns
```javascript
import api from '@/lib/api'

// GET request
const { data } = await api.get('/api/v1/medications')

// POST request
const response = await api.post('/api/v1/medications', {
  medicine_name: 'Tylenol',
  dosage: '500mg'
})

// Error handling
try {
  const response = await api.get('/api/v1/profiles')
} catch (error) {
  console.error('API call failed:', error.parsed?.message)
}
```

---

## Error Handling System

### lib/errors.js Structure
```javascript
import toast from 'react-hot-toast'

export const HTTP_STATUS_MESSAGES = {
  400: 'Invalid request.',
  401: 'Authentication required.',
  403: 'Access denied.',
  404: 'Resource not found.',
  500: 'Server error occurred.',
}

export function parseApiError(error) {
  // Error parsing logic
  return {
    status: error.response?.status || 0,
    message: 'User-friendly message',
    shouldRedirectToLogin: false,
    isRetryable: false,
  }
}

export function showError(message) {
  toast.error(message)
}
```

### Usage Patterns
```javascript
import { showError, parseApiError } from '@/lib/errors'

try {
  await api.post('/api/v1/medications', data)
} catch (error) {
  const parsed = parseApiError(error)
  showError(parsed.message)

  if (parsed.shouldRedirectToLogin) {
    router.push('/login')
  }
}
```

---

## Styling System

### Tailwind CSS Class Patterns
```javascript
// Button styles
const buttonStyles = {
  primary: "bg-gray-900 text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition-all cursor-pointer",
  secondary: "bg-white border border-gray-200 text-gray-600 px-6 py-3 rounded-xl font-bold hover:bg-gray-50 transition-all cursor-pointer",
  danger: "bg-red-500 text-white px-6 py-3 rounded-xl font-bold hover:bg-red-600 transition-all cursor-pointer"
}

// Card styles
const cardStyles = "bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-all"

// Modal styles
const modalStyles = "fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 backdrop-blur-sm"
```

### Responsive Design
```javascript
// Mobile-first approach
<div className="w-full md:w-1/2 lg:w-1/3">
  <div className="p-4 md:p-6 lg:p-8">
    <h2 className="text-lg md:text-xl lg:text-2xl font-bold">
      Title
    </h2>
  </div>
</div>
```

---

## State Management Patterns

### Local State (useState)
```javascript
const [medications, setMedications] = useState([])
const [isLoading, setIsLoading] = useState(true)
const [error, setError] = useState(null)
```

### Server State (API calls)
```javascript
useEffect(() => {
  const fetchData = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/api/v1/medications')
      setMedications(response.data)
    } catch (err) {
      setError(err.parsed?.message || 'Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }

  fetchData()
}, [])
```

### Global State (Context API)
```javascript
// contexts/AuthContext.js
import { createContext, useContext, useState } from 'react'

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)

  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```

---

## Performance Optimization

### Code Splitting
```javascript
import dynamic from 'next/dynamic'

// Dynamic loading for heavy components
const ChatModal = dynamic(() => import('@/components/chat/ChatModal'), {
  loading: () => <div>Loading chat...</div>,
  ssr: false
})
```

### Image Optimization
```javascript
import Image from 'next/image'

<Image
  src="/medication-image.jpg"
  alt="Medication image"
  width={300}
  height={200}
  placeholder="blur"
  blurDataURL="data:image/jpeg;base64,..."
/>
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

### 2. Token Management
```javascript
// Use HttpOnly cookies (automatic handling)
// Prohibit storing tokens in localStorage/sessionStorage
```

### 3. Prevent Error Information Exposure
```javascript
// ✅ Show only user-friendly messages
showError('An error occurred while processing the request')

// ❌ Prohibit exposing server error details
console.error(error.stack) // Development environment only
```

---

## Testing Strategy

### Unit Tests
```javascript
// __tests__/components/MedicationCard.test.js
import { render, screen } from '@testing-library/react'
import MedicationCard from '@/components/medication/MedicationCard'

test('renders medication card correctly', () => {
  const medication = {
    id: 1,
    medicine_name: 'Tylenol',
    dosage: '500mg'
  }

  render(<MedicationCard medication={medication} />)
  expect(screen.getByText('Tylenol')).toBeInTheDocument()
})
```

### E2E Tests
```javascript
// cypress/e2e/medication-flow.cy.js
describe('Medication Management Flow', () => {
  it('from prescription registration to medication confirmation', () => {
    cy.visit('/login')
    cy.get('[data-testid=dev-login]').click()
    cy.url().should('include', '/main')

    cy.get('[data-testid=ocr-button]').click()
    cy.get('input[type=file]').selectFile('prescription.jpg')
    cy.get('[data-testid=analyze-button]').click()
  })
})
```

---

## Deployment and CI/CD

### Vercel Deployment Configuration
```javascript
// next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_BASE_URL}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
```

### Environment-specific Deployment
```bash
# Local development
npm run dev

# Production build
npm run build
npm run start

# Vercel deployment
vercel --prod
```

---

## Development Workflow

### 1. New Feature Development
1. Create feature branch
2. Design and implement components
3. Use absolute path imports
4. Implement error handling
5. Write tests
6. Create PR and review

### 2. Code Review Checklist
- [ ] Use absolute path imports
- [ ] Proper error handling
- [ ] Follow security rules
- [ ] Apply performance optimizations
- [ ] Consider accessibility
- [ ] Responsive design

### 3. Pre-deployment Checklist
- [ ] No build errors
- [ ] Environment variables configured
- [ ] API endpoint connection tested
- [ ] Cross-browser testing
- [ ] Mobile responsive testing

Follow this design system to write consistent and maintainable frontend code.
