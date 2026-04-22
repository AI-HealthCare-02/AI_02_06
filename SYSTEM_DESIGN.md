# AI Healthcare System Design

This document covers the technical design specifications for the AI Healthcare System.

---

## Database Design

### Core Table Schema
```sql
-- Account Management
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    kakao_id VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    nickname VARCHAR(50) NOT NULL,
    profile_image TEXT,
    birth_date DATE,
    gender VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Medication Management
CREATE TABLE medications (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    dosage VARCHAR(50),
    frequency VARCHAR(50),
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE intake_logs (
    id SERIAL PRIMARY KEY,
    medication_id INTEGER REFERENCES medications(id) ON DELETE CASCADE,
    taken_at TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'taken',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI Features
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE llm_response_cache (
    id SERIAL PRIMARY KEY,
    input_hash VARCHAR(64) UNIQUE NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Challenge System
CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'medium',
    progress INTEGER DEFAULT 0,
    target INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Indexing Strategy
```sql
-- Performance optimization indexes
CREATE INDEX idx_accounts_kakao_id ON accounts(kakao_id);
CREATE INDEX idx_profiles_account_id ON profiles(account_id);
CREATE INDEX idx_refresh_tokens_account_id ON refresh_tokens(account_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

CREATE INDEX idx_medications_profile_id ON medications(profile_id);
CREATE INDEX idx_intake_logs_medication_id ON intake_logs(medication_id);
CREATE INDEX idx_intake_logs_taken_at ON intake_logs(taken_at);

CREATE INDEX idx_chat_sessions_profile_id ON chat_sessions(profile_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

CREATE INDEX idx_llm_response_cache_input_hash ON llm_response_cache(input_hash);
CREATE INDEX idx_challenges_profile_id ON challenges(profile_id);
```

---

## API Performance Rules and Standards

### Response Time Requirements
- **P95 Latency < 3 seconds**: 95% of requests completed within 3 seconds
- **P99 Latency < 5 seconds**: 99% of requests completed within 5 seconds
- **Average Response Time < 1 second**: Average processing time for general API requests

### Endpoint-Specific Performance Standards

| Endpoint | Target Response Time | Maximum Allowed Time | Notes |
|----------|---------------------|---------------------|-------|
| `/api/v1/health` | < 100ms | < 500ms | Health check |
| `/api/v1/auth/*` | < 500ms | < 2 seconds | Authentication related |
| `/api/v1/profiles/*` | < 300ms | < 1 second | Profile CRUD |
| `/api/v1/medications/*` | < 500ms | < 2 seconds | Medication management |
| `/api/v1/ocr/analyze` | < 10 seconds | < 30 seconds | OCR processing (async) |
| `/api/v1/chat/*` | < 2 seconds | < 5 seconds | Chat responses |

### Performance Monitoring Metrics
- **Throughput**: Requests per second (RPS)
- **Concurrent Connections**: Maximum 100 concurrent request processing
- **Error Rate**: < 1% (based on 5xx errors)
- **Availability**: 99.5% or higher (monthly basis)

### API Design Principles
```yaml
RESTful API Design:
  GET: Data retrieval (idempotency guaranteed)
  POST: New resource creation
  PATCH: Partial updates
  DELETE: Resource deletion

HTTP Status Codes:
  200: Success
  201: Creation success
  400: Bad request
  401: Authentication failure
  403: Unauthorized access
  404: Resource not found
  429: Rate limit exceeded
  500: Server error
```

---

## Asynchronous Processing Performance Optimization

### AI Inference Asynchronization
```python
# OCR + RAG pipeline processing time
Processing stage breakdown:
  - Image preprocessing: Average 0.5 seconds
  - OCR API call: Average 3-8 seconds
  - Text refinement: Average 0.2 seconds
  - Medicine name matching: Average 0.5 seconds
  - Text chunking: Average 0.3 seconds
  - RAG generation: Average 5-15 seconds
  - Post-processing: Average 0.5 seconds
  - Total processing time: Average 10-30 seconds
```

### I/O Operation Optimization Strategy
```python
# Asynchronous processing implementation
async def process_ocr_request(image_data: bytes) -> dict:
    # 1. Asynchronous file storage
    async with aiofiles.open(temp_path, 'wb') as f:
        await f.write(image_data)

    # 2. Asynchronous external API call
    async with httpx.AsyncClient() as client:
        response = await client.post(ocr_api_url, files=files)

    # 3. Asynchronous database storage
    await OCRResult.create(
        user_id=user_id,
        result=response.json(),
        processed_at=datetime.now()
    )

    return response.json()
```

### Resource Usage Efficiency Improvements
- **Memory Usage**: Maintain average 60% or below
- **CPU Usage**: Maintain average 70% or below
- **Concurrent Processing**: FastAPI + Uvicorn worker-based
- **Connection Pool**: PostgreSQL maximum 20 connections
- **Redis Connections**: Maximum 10 connection pool

---

## Security Policies and Rules

### JWT Token Policy
```yaml
Access Token:
  - Validity Period: 60 minutes
  - Algorithm: HS256
  - Claims: user_id, exp, iat, token_type
  - Storage Location: Authorization header
  - Format: "Bearer <token>"

Refresh Token:
  - Validity Period: 14 days
  - Storage Location: HttpOnly cookie
  - Auto Renewal: Upon Access Token expiration
  - Security Options: Secure, SameSite=Strict
  - Hash Storage: SHA-256 hashed before DB storage
```

### Rate Limiting Detailed Rules
```yaml
IP-based Request Limits:
  General GET requests:
    - Limit: 200 requests/60 seconds
    - Burst: 250 requests (within 10 seconds)

  Mutation requests (POST/PATCH/DELETE):
    - Limit: 30 requests/60 seconds
    - Burst: 40 requests (within 10 seconds)

  Authentication endpoints:
    - Limit: 10 requests/60 seconds
    - Burst: None

  OCR requests:
    - Limit: 5 requests/60 seconds
    - Burst: None

Rate Limit Exceeded Handling:
  - HTTP 429 response
  - Retry-After header included
  - Logging and alerting
  - Temporary IP blocking (severe cases)
```

### Security Middleware Configuration
```python
# Attack pattern detection
ATTACK_PATTERNS = [
    (r"\.\.[\\/]", "path_traversal"),
    (r"%00", "null_byte_injection"),
    (r"<script", "xss_attempt"),
    (r"javascript:", "javascript_injection"),
    (r"(union|select|insert|delete|update|drop)\s", "sql_injection")
]

# Security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}
```

### HTTPS and Encryption Policy
```yaml
SSL/TLS Configuration:
  - Supported Versions: TLS 1.2, TLS 1.3
  - Cipher Suites: ECDHE-RSA-AES256-GCM-SHA384
  - Key Exchange: ECDHE (Perfect Forward Secrecy)
  - Certificate: Let's Encrypt (automatic renewal)
  - HSTS: 1 year (includeSubDomains)

Data Encryption:
  - Data at Rest: AES-256 encryption
  - Data in Transit: TLS 1.3
  - Passwords: bcrypt (cost=12)
  - API Keys: Environment variable management
```

---

## AI Model Performance Rules

### Result Consistency Standards
```yaml
Identical Input Test Protocol:
  - Repetition Count: 10 or more times
  - Allowed Variance: Text similarity 95% or higher
  - Response Time Variance: Within ±20%
  - Success Rate: 95% or higher
  - Test Frequency: Weekly
```

### OCR Performance Metrics and Optimization
```yaml
CLOVA OCR Performance:
  Accuracy Targets:
    - Korean Text: 90% or higher
    - Numbers: 95% or higher
    - English Text: 85% or higher

  Processing Time:
    - Average per image: 3-8 seconds
    - Maximum allowed: 30 seconds
    - Timeout: 45 seconds

  Supported Formats:
    - Images: JPG, PNG (max 10MB)
    - Documents: PDF (max 10MB, 5 pages)
    - Resolution: Minimum 300DPI recommended

  Preprocessing Optimization:
    - Image resizing: Maximum 2048x2048
    - Noise reduction: Gaussian blur
    - Contrast enhancement: CLAHE application
```

### RAG Generation Performance Metrics
```yaml
OpenAI GPT Configuration:
  Model Selection:
    - Development: gpt-4o-mini (cost optimization)
    - Production: gpt-4o (quality optimization)

  Token Management:
    - Input Limit: 4000 tokens
    - Output Limit: 2000 tokens
    - Context Window: 128k tokens

  Quality Management:
    - Response Quality: 80% or higher appropriateness by medical review
    - Generation Time: Average 5-15 seconds
    - Hallucination Prevention: Source-based response enforcement
    - Safety Filter: OpenAI Moderation API application
```

### Model A/B Testing Framework
```yaml
A/B Test Configuration:
  Experimental Design:
    - Traffic Split: 50:50 (Control vs Treatment)
    - Test Duration: Minimum 7 days (statistical significance)
    - Sample Size: Minimum 1000 cases

  Evaluation Metrics:
    - Primary Metrics: Response time, accuracy, user satisfaction
    - Secondary Metrics: Token usage, error rate, retry rate

  Statistical Validation:
    - Significance Level: α = 0.05
    - Statistical Power: β = 0.8
    - Effect Size: Minimum 5% improvement

  Deployment Strategy:
    - Canary Deployment: 5% → 25% → 50% → 100%
    - Rollback Condition: Immediate rollback if error rate exceeds 2%
```

---

## User Feedback and Improvement System

### Feedback Collection Architecture
```yaml
Feedback Data Models:
  message_feedbacks:
    - message_id: Message identifier
    - rating: 1-5 score or good/bad
    - feedback_text: Free text feedback
    - category: Accuracy, usefulness, comprehension, etc.
    - created_at: Feedback timestamp

  ocr_corrections:
    - ocr_result_id: OCR result identifier
    - original_text: Original OCR result
    - corrected_text: User-corrected text
    - correction_type: Addition, deletion, modification
    - created_at: Correction timestamp

  usage_analytics:
    - user_id: User identifier
    - action: Performed action
    - context: Action context
    - duration: Time taken
    - success: Success status
```

### Improvement Process Automation
```python
# Feedback analysis pipeline
class FeedbackAnalyzer:
    def analyze_weekly_feedback(self):
        # 1. Collect feedback data
        feedbacks = self.collect_feedback_data()

        # 2. Pattern analysis
        patterns = self.identify_patterns(feedbacks)

        # 3. Priority determination
        priorities = self.calculate_priority_scores(patterns)

        # 4. Generate improvement suggestions
        improvements = self.generate_improvement_suggestions(priorities)

        # 5. Automated notifications
        self.notify_development_team(improvements)

        return improvements
```

### Continuous Improvement KPIs
```yaml
Feedback-Related KPIs:
  Collection Rate:
    - Target: 20% or higher of total interactions
    - Measurement: Daily/weekly/monthly feedback collection rate

  Implementation Rate:
    - Target: 80% or higher review of collected feedback
    - Measurement: Feedback → improvement conversion rate

  Performance Improvement:
    - Target: 5% or higher monthly performance metric improvement
    - Measurement: Accuracy, response time, user satisfaction

  Response Time:
    - Target: Initial review within 48 hours of feedback receipt
    - Measurement: Average response time, SLA compliance rate
```

---

## System Scalability and Capacity Planning

### Current System Capacity Analysis
```yaml
EC2 t3.medium Resource Analysis:
  Hardware Constraints:
    - CPU: 2 vCPU (burst credits: 24 credits/hour)
    - Memory: 4GB RAM
    - Storage: 30GB EBS gp3 (3000 IOPS)
    - Network: Maximum 5 Gbps (burst)

  Expected Processing Capacity:
    - Concurrent Users: 50-100 users
    - Daily API Requests: 10,000-20,000 requests
    - Daily OCR Requests: 500-1,000 requests
    - Daily Chat Messages: 2,000-5,000 messages
    - DB Connections: Maximum 20 concurrent connections
```

### Performance Monitoring and Alerting
```yaml
Monitoring Metrics:
  System Resources:
    - CPU Usage: Warning at 80%+, Critical at 90%+
    - Memory Usage: Warning at 85%+, Critical at 95%+
    - Disk Usage: Warning at 80%+, Critical at 90%+
    - Network I/O: Warning at 80%+ bandwidth utilization

  Application Performance:
    - Response Time: Warning if P95 > 3s sustained
    - Error Rate: Warning at 1%+ sustained, Critical at 5%+
    - Throughput: Warning if 50% decrease from baseline
    - Queue Backlog: Warning if Redis queue exceeds 100 items
```

### Scaling Strategy Roadmap
```yaml
Phased Scaling Plan:
  Phase 1 - Vertical Scaling (Immediate):
    - EC2 Instance: t3.medium → t3.large
    - Memory: 4GB → 8GB
    - Expected Capacity: 200 concurrent users

  Phase 2 - Database Separation (1-2 months):
    - Introduce RDS PostgreSQL
    - Add read-only replicas
    - Optimize connection pooling

  Phase 3 - Horizontal Scaling (3-6 months):
    - Introduce Application Load Balancer
    - Multiple EC2 instances (2-3)
    - ElastiCache Redis cluster
    - Externalize session store

  Phase 4 - Microservices (6-12 months):
    - Separate AI Worker service
    - Introduce API Gateway
    - Service mesh (Istio/Linkerd)
    - Distributed tracing (Jaeger/Zipkin)
```

### Cost Optimization Strategy
```yaml
Cost Efficiency Plan:
  Current Cost Structure:
    - EC2 t3.medium: $30/month
    - EBS 30GB: $3/month
    - Data Transfer: $5/month
    - Total Estimated Cost: $40/month

  Scaling Cost Projections:
    - Phase 1: $80/month (2x performance)
    - Phase 2: $150/month (RDS addition)
    - Phase 3: $300/month (horizontal scaling)
    - Phase 4: $500/month (microservices)

  Cost Optimization Methods:
    - Reserved Instance utilization (30-50% savings)
    - Spot Instance utilization (dev/test environments)
    - CloudWatch-based Auto Scaling
    - Automated cleanup of unused resources
```

---

## Monitoring and Logging Strategy

### Logging Architecture
```yaml
Log Level Policies:
  DEBUG:
    - Purpose: Development environment debugging
    - Content: Function calls, variable values, execution paths
    - Retention: 1 day

  INFO:
    - Purpose: Normal system operation recording
    - Content: API requests/responses, user actions
    - Retention: 7 days

  WARNING:
    - Purpose: Situations requiring attention
    - Content: Performance degradation, retries, threshold approaches
    - Retention: 30 days

  ERROR:
    - Purpose: Error situation recording
    - Content: Exception occurrences, API failures, DB errors
    - Retention: 90 days

  CRITICAL:
    - Purpose: System failure situations
    - Content: Service outages, security breaches
    - Retention: 1 year
```

### Structured Logging Format
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "fastapi",
  "module": "auth.oauth",
  "function": "kakao_login",
  "user_id": "user_12345",
  "request_id": "req_abcd1234",
  "message": "User login successful",
  "duration_ms": 245,
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "endpoint": "/api/v1/auth/kakao/callback"
  }
}
```

### Performance Metrics Collection
```yaml
Application Metrics:
  HTTP Requests:
    - Request count (counter)
    - Response time (histogram)
    - Status code distribution (counter)
    - Endpoint-specific statistics (gauge)

  Database:
    - Query execution time (histogram)
    - Connection pool utilization (gauge)
    - Slow query count (counter)
    - Transaction rollback count (counter)

  AI Models:
    - OCR processing time (histogram)
    - RAG generation time (histogram)
    - Model call success rate (gauge)
    - Token usage (counter)
```

### Alerting and Response System
```yaml
Alert Rules:
  Immediate Alerts (Critical):
    - Service down (5+ minutes)
    - Error rate 10%+
    - Response time P95 > 10 seconds
    - Disk usage 95%+

  Warning Alerts:
    - CPU usage 80%+ (10 minutes)
    - Memory usage 85%+ (5 minutes)
    - Error rate 5%+ (5 minutes)
    - Response time P95 > 5 seconds (5 minutes)

  Informational Alerts:
    - Daily usage reports
    - Weekly performance summaries
    - Monthly cost reports
    - Security event summaries
```
