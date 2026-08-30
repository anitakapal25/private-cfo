# Financial Freedom Copilot - Phase 3 Testing Guide

This guide will help you test all Phase 3 features once the server is running.

## Prerequisites

1. Server must be running on `http://localhost:8000`
2. Test data should be seeded (run `python backend/seed_data.py`)
3. Encryption key must be set (handled automatically when starting server)

## Starting the Server

From the project root directory:
```bash
# Navigate to backend directory
cd backend

# Set encryption key (will be auto-generated each time)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test Users

Use these credentials to test different roles:

| Email | Password | Role |
|-------|----------|------|
| test@example.com | testpassword123 | user |
| advisor@example.com | advisorpassword123 | advisor |
| admin@example.com | adminpassword123 | admin |

## Authentication

### 1. Login
```bash
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123"
```
Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Get Current User Info
```bash
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

### 3. Logout
```bash
curl -X POST "http://localhost:8000/api/auth/logout" \
  -H "Authorization: Bearer <access_token>"
```

## Phase 3 Feature Testing

### A. Financial Advisor Consent API

#### 1. Advisor Requests Consent
```bash
curl -X POST "http://localhost:8000/api/advisor/request-consent" \
  -H "Authorization: Bearer <advisor_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "<test_user_id>",
    "scope": "read_only"
  }'
```

#### 2. Advisor Views Clients Who Granted Consent
```bash
curl -X GET "http://localhost:8000/api/advisor/clients" \
  -H "Authorization: Bearer <advisor_token>"
```

#### 3. Advisor Revokes Consent
```bash
curl -X DELETE "http://localhost:8000/api/advisor/consent/<consent_id>" \
  -H "Authorization: Bearer <advisor_token>"
```

#### 4. Advisor Accesses Client Data (with valid consent)
```bash
curl -X GET "http://localhost:8000/api/advisor/client-data/<client_id>" \
  -H "Authorization: Bearer <advisor_token>"
```

### B. Investment Platform Connections

#### 1. Create Connection (with encrypted credentials)
```bash
curl -X POST "http://localhost:8000/api/investment-platform/connections" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform_name": "zerodha",
    "platform_display_name": "Zerodha",
    "credentials": {
      "api_key": "test_api_key",
      "api_secret": "test_api_secret"
    },
    "is_active": true
  }'
```

#### 2. List User's Connections
```bash
curl -X GET "http://localhost:8000/api/investment-platform/connections" \
  -H "Authorization: Bearer <user_token>"
```

#### 3. Get Specific Connection
```bash
curl -X GET "http://localhost:8000/api/investment-platform/connections/<connection_id>" \
  -H "Authorization: Bearer <user_token>"
```

#### 4. Update Connection
```bash
curl -X PUT "http://localhost:8000/api/investment-platform/connections/<connection_id>" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform_name": "zerodha",
    "platform_display_name": "Zerodha Updated",
    "credentials": {
      "api_key": "updated_api_key",
      "api_secret": "updated_api_secret"
    },
    "is_active": true
  }'
```

#### 5. Delete Connection
```bash
curl -X DELETE "http://localhost:8000/api/investment-platform/connections/<connection_id>" \
  -H "Authorization: Bearer <user_token>"
```

#### 6. Trigger Manual Sync
```bash
curl -X POST "http://localhost:8000/api/investment-platform/connections/<connection_id>/sync" \
  -H "Authorization: Bearer <user_token>"
```

### C. Account Aggregator (Banking) Connections

#### 1. Create AA Connection
```bash
curl -X POST "http://localhost:8000/api/account-aggregator/connections" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "aa_handle": "yourname@okhdfcbank",
    "credentials": {
      "username": "yourusername",
      "mpin": "1234"
    },
    "is_active": true
  }'
```

#### 2. List AA Connections
```bash
curl -X GET "http://localhost:8000/api/account-aggregator/connections" \
  -H "Authorization: Bearer <user_token>"
```

### D. Community Features

#### 1. Create Community Benchmark (Admin only)
```bash
curl -X POST "http://localhost:8000/api/community/benchmarks" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "age_group": "25-35",
    "income_bracket": "500000-1000000",
    "metric_type": "savings_rate",
    "metric_value": 0.25,
    "unit": "ratio",
    "source": "NSSO Survey 2023",
    "confidence_level": 0.95
  }'
```

#### 2. Get Benchmarks
```bash
curl -X GET "http://localhost:8000/api/community/benchmarks" \
  -H "Authorization: Bearer <user_token>"
```

#### 3. Get User's Benchmark Comparison
```bash
curl -X GET "http://localhost:8000/api/community/my-benchmark-comparison" \
  -H "Authorization: Bearer <user_token>"
```

### E. Employer Wellness Programs

#### 1. Create Wellness Program (Admin only)
```bash
curl -X POST "http://localhost:8000/api/wellness-program/programs" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "program_name": "TechCorp Financial Wellness",
    "employer_name": "TechCorp Solutions",
    "description": "Comprehensive financial wellness program for employees",
    "branding": {
      "logo_url": "https://example.com/logo.png",
      "primary_color": "#0066CC",
      "secondary_color": "#00CC66"
    },
    "is_active": true
  }'
```

#### 2. List Wellness Programs
```bash
curl -X GET "http://localhost:8000/api/wellness-program/programs" \
  -H "Authorization: Bearer <user_token>"
```

#### 3. Join a Wellness Program
```bash
curl -X POST "http://localhost:8000/api/wellness-program/programs/<program_id>/join" \
  -H "Authorization: Bearer <user_token>"
```

#### 4. Update Participation
```bash
curl -X PUT "http://localhost:8000/api/wellness-program/participations/<participation_id>" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "contribution_amount": 5000.00,
    "contribution_frequency": "monthly",
    "is_active": true
  }'
```

#### 5. Leave a Wellness Program
```bash
curl -X DELETE "http://localhost:8000/api/wellness-program/programs/<program_id>/leave" \
  -H "Authorization: Bearer <user_token>"
```

#### 6. Get User's Participations
```bash
curl -X GET "http://localhost:8000/api/wellness-program/participations" \
  -H "Authorization: Bearer <user_token>"
```

### F. API Webhook System

#### 1. Create Webhook Subscription
```bash
curl -X POST "http://localhost:8000/api/webhook/subscriptions" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/webhook-receiver",
    "events": ["life_event:marriage", "market_condition:stock_drop_10pct"],
    "secret": "your-webhook-secret",
    "headers": {
      "X-Custom-Header": "custom-value"
    }
  }'
```

#### 2. List Webhook Subscriptions
```bash
curl -X GET "http://localhost:8000/api/webhook/subscriptions" \
  -H "Authorization: Bearer <user_token>"
```

#### 3. Get Specific Subscription
```bash
curl -X GET "http://localhost:8000/api/webhook/subscriptions/<subscription_id>" \
  -H "Authorization: Bearer <user_token>"
```

#### 4. Update Subscription
```bash
curl -X PUT "http://localhost:8000/api/webhook/subscriptions/<subscription_id>" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/webhook-receiver-v2",
    "events": ["life_event:marriage", "life_event:birth", "market_condition:stock_drop_10pct"],
    "secret": "updated-secret",
    "headers": {
      "X-Custom-Header": "updated-value"
    }
  }'
```

#### 5. Delete Subscription
```bash
curl -X DELETE "http://localhost:8000/api/webhook/subscriptions/<subscription_id>" \
  -H "Authorization: Bearer <user_token>"
```

#### 6. View Delivery History
```bash
curl -X GET "http://localhost:8000/api/webhook/subscriptions/<subscription_id>/deliveries" \
  -H "Authorization: Bearer <user_token>"
```

### G. Export Capabilities

#### 1. Create Tax Export Template (Admin only)
```bash
curl -X POST "http://localhost:8000/api/export/templates/tax" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "ITR-1 Sahaj",
    "assessment_year": "2026-27",
    "description": "For individuals having income from salaries, one house property, other sources (interest etc.), and having total income upto ₹50 lakh",
    "export_format": "XML",
    "is_active": true
  }'
```

#### 2. List Tax Export Templates
```bash
curl -X GET "http://localhost:8000/api/export/templates/tax" \
  -H "Authorization: Bearer <user_token>"
```

#### 3. Create Tax Export for User
```bash
curl -X POST "http://localhost:8000/api/export/exports/tax" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "<template_id>"
  }'
```

#### 4. List User's Tax Exports
```bash
curl -X GET "http://localhost:8000/api/export/exports/tax" \
  -H "Authorization: Bearer <user_token>"
```

#### 5. Create Loan Application Export
```bash
curl -X POST "http://localhost:8000/api/export/exports/loan" \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "loan_type": "home",
    "loan_amount_requested": 5000000
  }'
```

#### 6. List User's Loan Exports
```bash
curl -X GET "http://localhost:8000/api/export/exports/loan" \
  -H "Authorization: Bearer <user_token>"
```

## Verification Points

1. **Encryption**: When creating investment platform or AA connections, verify that credentials are encrypted in the database (not stored as plain text).

2. **Role-Based Access**: 
   - Regular users should NOT be able to access admin-only endpoints
   - Advisors should only see clients who granted them consent
   - Users should only see their own data

3. **Background Tasks**: Check server logs for background sync messages indicating the investment platform sync is running.

4. **Webhook Delivery**: When triggering events in the app, check if webhook delivery attempts are logged.

5. **Export Files**: Verify that exported tax/loan documents contain correct user data and are properly formatted.

## Troubleshooting

If you encounter issues:

1. Check server logs: `tail -f backend/server.log`
2. Verify database connectivity
3. Ensure encryption key is set correctly
4. Check that all migrations have been applied
5. Verify that the test data has been seeded properly

## Privacy-First Architecture Verification

Throughout testing, confirm that:
1. The LLM (you) never directly accesses or processes sensitive financial data
2. All data operations are performed through appropriate tools/APIs
3. Consent is properly checked before accessing user data (especially for advisor endpoints)
4. Credentials are always encrypted at rest