# Financial Freedom Copilot - Database Model

**Status:** Target/reference schema with known drift  
**Last reviewed:** 2026-08-30  
**Authority:** Alembic migrations are authoritative. Calculation, financial-action and audit-history persistence described here is not yet implemented.

## Overview
This document defines the database schema for Financial Freedom Copilot (ArthaOS), translating the domain model into a relational database structure optimized for financial data storage, retrieval, and security. The design prioritizes data integrity, query performance, and compliance with financial data protection requirements.

## Database Choice: PostgreSQL 15+

### Rationale
- ACID compliance essential for financial data integrity
- Row-level security for fine-grained access control
- JSONB support for flexible document storage and extracted data
- Strong encryption capabilities
- Excellent performance for complex financial calculations
- Extensive indexing options
- Point-in-time recovery and logical replication
- Strong community and enterprise support

## Schema Design Principles

### 1. Privacy and Security
- Sensitive data encrypted at rest using pgcrypto or application-level encryption
- No storage of full PAN, Aadhaar, or complete account numbers
- Masking of sensitive identifiers (showing only last 4 digits)
- Separate tables for highly sensitive data with additional access controls
- Audit logging of all data access and modifications

### 2. Data Integrity
- Constraints to ensure logical consistency (check constraints, foreign keys)
- Proper data types for monetary values (numeric/decimal)
- Timestamps for tracking creation and modification
- UUIDs for primary keys to prevent enumeration
- Cascading deletes where appropriate, restricted where not

### 3. Performance
- Strategic indexing on frequently queried columns
- Partitioning considerations for large tables (audit logs, calculations)
- Materialized views for expensive aggregated calculations
- Connection pooling ready design
- Read replicas for reporting and analytics workloads

### 4. Extensibility
- Modular table design allowing for easy addition of new columns
- JSONB fields for flexible storage of variable-format data (extracted document data)
- Enum types for categorical data with clear migration paths
- Separate schemas for different functional areas if needed

## Schema Organization

### Core Schemas
- `financial`: Core financial data (users, accounts, transactions)
- `documents`: Document management and extraction data
- `goals`: Financial goal tracking
- `calculations`: Calculation audit trail
- `audit`: Security and compliance auditing
- `lookup`: Reference data and enumerations

## Detailed Table Definitions

### 1. Core User Tables

#### financial.users
```sql
CREATE TABLE financial.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_of_birth DATE NOT NULL,
    gender CHAR(1), -- 'M', 'F', 'O' (other), or NULL
    marital_status VARCHAR(20), -- 'single', 'married', 'divorced', 'widowed'
    dependents_count INTEGER NOT NULL DEFAULT 0 CHECK (dependents_count >= 0),
    residential_status VARCHAR(20) NOT NULL DEFAULT 'resident_indian', -- 'resident_indian', 'nri', 'ocio', etc.
    pan_last_four CHAR(4), -- Last 4 digits of PAN for reference only
    aadhaar_last_four CHAR(4), -- Last 4 digits of Aadhaar for reference only
    employment_status VARCHAR(20) NOT NULL, -- 'employed', 'unemployed', 'self_employed', 'retired'
    primary_occupation VARCHAR(100),
    -- Email and phone handled in profile table for normalization
    CONSTRAINT chk_gender CHECK (gender IN ('M', 'F', 'O') OR gender IS NULL),
    CONSTRAINT chk_marital_status CHECK (marital_status IN ('single', 'married', 'divorced', 'widowed')),
    CONSTRAINT chk_residential_status CHECK (residential_status IN ('resident_indian', 'nri', 'ocio')),
    CONSTRAINT chk_employment_status CHECK (employment_status IN ('employed', 'unemployed', 'self_employed', 'retired'))
);

-- Indexes
CREATE INDEX idx_users_dob ON financial.users(date_of_birth);
CREATE INDEX idx_users_active ON financial.users(is_active) WHERE is_active = TRUE;
```

#### financial.profiles
```sql
CREATE TABLE financial.profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(200) NOT NULL,
    email_address VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(10),
    country VARCHAR(50) NOT NULL DEFAULT 'India',
    preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_profile_user UNIQUE (user_id),
    CONSTRAINT uq_profile_email UNIQUE (email_address),
    CONSTRAINT uq_profile_phone UNIQUE (phone_number)
);

-- Indexes
CREATE INDEX idx_profiles_user ON financial.profiles(user_id);
CREATE INDEX idx_profiles_email ON financial.profiles(email_address);
CREATE INDEX idx_profiles_phone ON financial.profiles(phone_number);
```

### 2. Financial Data Tables

#### financial.income_sources
```sql
CREATE TABLE financial.income_sources (
    income_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL, -- salary, bonus, freelance, rental, interest, dividend, pension, other
    source_name VARCHAR(200) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    frequency VARCHAR(10) NOT NULL, -- monthly, quarterly, annually, one-time
    is_taxable BOOLEAN NOT NULL DEFAULT TRUE,
    tax_withheld NUMERIC(15, 2) NOT NULL DEFAULT 0 CHECK (tax_withheld >= 0),
    start_date DATE NOT NULL,
    end_date DATE, -- NULL for ongoing
    growth_rate NUMERIC(5, 4) DEFAULT 0, -- e.g., 0.08 for 8%
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_income_source_type CHECK (source_type IN ('salary', 'bonus', 'freelance', 'rental', 'interest', 'dividend', 'pension', 'other')),
    CONSTRAINT chk_income_frequency CHECK (frequency IN ('monthly', 'quarterly', 'annually', 'one-time')),
    CONSTRAINT chk_income_dates CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT chk_tax_withheld CHECK (tax_withheld <= amount) -- Simplified check
);

-- Indexes
CREATE INDEX idx_income_user_active ON financial.income_sources(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_income_source_type ON financial.income_sources(source_type);
CREATE INDEX idx_income_dates ON financial.income_sources(start_date, end_date);
```

#### financial.expenses
```sql
CREATE TABLE financial.expenses (
    expense_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    subcategory VARCHAR(100),
    description TEXT,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    frequency VARCHAR(10) NOT NULL,
    is_essential BOOLEAN NOT NULL,
    is_inflation_linked BOOLEAN NOT NULL DEFAULT TRUE,
    inflation_rate NUMERIC(5, 4), -- Custom inflation rate if different from general
    start_date DATE NOT NULL,
    end_date DATE, -- NULL for ongoing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_expense_category CHECK (category IN ('housing', 'food', 'transportation', 'utilities', 'healthcare', 'entertainment', 'education', 'personal_care', 'insurance', 'loan_emis', 'investments', 'taxes', 'other')),
    CONSTRAINT chk_expense_frequency CHECK (frequency IN ('monthly', 'quarterly', 'annually', 'one-time')),
    CONSTRAINT chk_expense_dates CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT chk_inflation_rate CHECK (inflation_rate IS NULL OR (inflation_rate >= 0 AND inflation_rate <= 0.20)) -- Reasonable bound
);

-- Indexes
CREATE INDEX idx_expense_user_active ON financial.expenses(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_expense_category ON financial.expenses(category);
CREATE INDEX idx_expense_dates ON financial.expenses(start_date, end_date);
```

#### financial.assets
```sql
CREATE TABLE financial.assets (
    asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    asset_type VARCHAR(30) NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    institution_name VARCHAR(200),
    account_number_masked CHAR(4), -- Last 4 digits only
    current_value NUMERIC(15, 2) NOT NULL CHECK (current_value >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    purchase_date DATE,
    expected_return_rate NUMERIC(5, 4), -- e.g., 0.10 for 10%
    risk_level VARCHAR(10), -- low, medium, high
    liquidity VARCHAR(10), -- high, medium, low
    is_joint_owned BOOLEAN NOT NULL DEFAULT FALSE,
    joint_owner_details JSONB, -- Store structured info about co-owners
    nominee_details JSONB, -- Store nominee information
    maturity_date DATE, -- For fixed-term instruments
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_asset_type CHECK (asset_type IN ('cash', 'savings_account', 'fixed_deposit', 'recurring_deposit', 'epf', 'ppf', 'nps', 'mutual_funds', 'stocks', 'bonds', 'gold', 'real_estate', 'vehicle', 'other_investments')),
    CONSTRAINT chk_asset_risk CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high')),
    CONSTRAINT chk_asset_liquidity CHECK (liquidity IS NULL OR liquidity IN ('high', 'medium', 'low')),
    CONSTRAINT chk_asset_dates CHECK (maturity_date IS NULL OR maturity_date >= purchase_date)
);

-- Indexes
CREATE INDEX idx_asset_user_active ON financial.assets(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_asset_type ON financial.assets(asset_type);
CREATE INDEX idx_asset_institution ON financial.assets(institution_name);
```

#### financial.liabilities
```sql
CREATE TABLE financial.liabilities (
    liability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    liability_type VARCHAR(30) NOT NULL,
    lender_name VARCHAR(200) NOT NULL,
    account_number_masked CHAR(4), -- Last 4 digits only
    principal_outstanding NUMERIC(15, 2) NOT NULL CHECK (principal_outstanding >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    interest_rate NUMERIC(5, 4) NOT NULL CHECK (interest_rate >= 0),
    interest_type VARCHAR(10) NOT NULL, -- fixed, floating, reducing_balance
    emi_amount NUMERIC(15, 2) NOT NULL CHECK (emi_amount >= 0),
    total_emis INTEGER NOT NULL CHECK (total_emis > 0),
    emis_paid INTEGER NOT NULL CHECK (emis_paid >= 0 AND emis_paid <= total_emis),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    prepayment_penalty_details JSONB, -- Store prepayment terms
    is_tax_deductible BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_liability_type CHECK (liability_type IN ('home_loan', 'personal_loan', 'car_loan', 'education_loan', 'credit_card_due', 'business_loan', 'other')),
    CONSTRAINT chk_interest_type CHECK (interest_type IN ('fixed', 'floating', 'reducing_balance')),
    CONSTRAINT chk_liability_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_emis_paid CHECK (emis_paid <= total_emis)
);

-- Indexes
CREATE INDEX idx_liability_user_active ON financial.liabilities(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_liability_type ON financial.liabilities(liability_type);
CREATE INDEX idx_liability_lender ON financial.liabilities(lender_name);
```

#### financial.insurance_policies
```sql
CREATE TABLE financial.insurance_policies (
    insurance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    insurance_type VARCHAR(30) NOT NULL,
    policy_number_masked VARCHAR(20), -- Masked policy number for reference
    provider_name VARCHAR(200) NOT NULL,
    sum_assured NUMERIC(15, 2) NOT NULL CHECK (sum_assured >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    premium_amount NUMERIC(10, 2) NOT NULL CHECK (premium_amount >= 0),
    premium_frequency VARCHAR(10) NOT NULL, -- monthly, quarterly, semi-annual, annual
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    maturity_date DATE, -- For endowment policies
    beneficiaries JSONB, -- Array of beneficiary objects with relationship and percentage
    nominee_details JSONB,
    riders JSONB, -- Array of rider objects
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_insurance_type CHECK (insurance_type IN ('life_term', 'life_endowment', 'health_individual', 'health_family', 'critical_illness', 'personal_accident', 'property', 'vehicle', 'other')),
    CONSTRAINT chk_premium_frequency CHECK (premium_frequency IN ('monthly', 'quarterly', 'semi-annual', 'annual')),
    CONSTRAINT chk_insurance_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_maturity_date CHECK (maturity_date IS NULL OR maturity_date >= start_date)
);

-- Indexes
CREATE INDEX idx_insurance_user_active ON financial.insurance_policies(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_insurance_type ON financial.insurance_policies(insurance_type);
CREATE INDEX idx_insurance_provider ON financial.insurance_policies(provider_name);
```

### 3. Goals and Financial Freedom Target

#### financial.goals
```sql
CREATE TABLE financial.goals (
    goal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    goal_type VARCHAR(30) NOT NULL,
    goal_name VARCHAR(200) NOT NULL,
    target_amount NUMERIC(15, 2) NOT NULL CHECK (target_amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    target_date DATE NOT NULL,
    priority VARCHAR(10) NOT NULL, -- high, medium, low
    current_amount NUMERIC(15, 2) NOT NULL DEFAULT 0 CHECK (current_amount >= 0),
    monthly_contribution NUMERIC(10, 2) NOT NULL DEFAULT 0 CHECK (monthly_contribution >= 0),
    expected_return NUMERIC(5, 4) DEFAULT 0, -- e.g., 0.08 for 8%
    inflation_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_goal_type CHECK (goal_type IN ('emergency_fund', 'home_purchase', 'education', 'retirement', 'vehicle_purchase', 'vacation', 'debt_free', 'wealth_creation', 'other')),
    CONSTRAINT chk_goal_priority CHECK (priority IN ('high', 'medium', 'low')),
    CONSTRAINT chk_goal_dates CHECK (target_date > CURRENT_DATE),
    CONSTRAINT chk_goal_amounts CHECK (current_amount <= target_amount)
);

-- Indexes
CREATE INDEX idx_goal_user_active ON financial.goals(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_goal_type ON financial.goals(goal_type);
CREATE INDEX idx_goal_target_date ON financial.goals(target_date);
CREATE INDEX idx_goal_priority ON financial.goals(priority);
```

#### financial.financial_freedom_targets
```sql
CREATE TABLE financial.financial_freedom_targets (
    ff_target_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    target_age INTEGER NOT NULL CHECK (target_age > 0 AND target_age <= 100),
    target_lifestyle_expenses NUMERIC(15, 2) NOT NULL CHECK (target_lifestyle_expenses > 0),
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    inflation_assumption NUMERIC(5, 4) NOT NULL CHECK (inflation_assumption >= 0 AND inflation_assumption <= 0.20), -- 0-20%
    return_assumption NUMERIC(5, 4) NOT NULL CHECK (return_assumption >= -0.50 AND return_assumption <= 0.50), -- -50% to +50%
    current_age INTEGER GENERATED ALWAYS AS (
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, (SELECT date_of_birth FROM financial.users WHERE user_id = financial_freedom_targets.user_id)))
    ) STORED,
    years_to_target INTEGER GENERATED ALWAYS AS (target_age - current_age) STORED,
    required_corpus NUMERIC(15, 2), -- Calculated: present value of target lifestyle expenses
    current_projected_corpus NUMERIC(15, 2), -- Calculated: future value of current trajectory
    freedom_gap NUMERIC(15, 2), -- Calculated: required_corpus - current_projected_corpus
    projected_freedom_age INTEGER, -- Calculated: age when projected corpus meets required corpus
    assumptions_documents JSONB, -- Array of document IDs justifying assumptions
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ff_target_age CHECK (target_age > 
        (SELECT EXTRACT(YEAR FROM AGE(CURRENT_DATE, date_of_birth)) 
         FROM financial.users 
         WHERE user_id = financial_freedom_targets.user_id)
    ),
    CONSTRAINT chk_ff_years_positive CHECK (years_to_target > 0)
);

-- Indexes
CREATE INDEX idx_ff_user ON financial.financial_freedom_targets(user_id);
CREATE INDEX idx_ff_target_age ON financial.financial_freedom_targets(target_age);
```

Note: The calculated fields (required_corpus, current_projected_corpus, freedom_gap, projected_freedom_age) would typically be computed by the application layer or database functions rather than stored directly, but are shown here for completeness. In practice, these might be views or computed on-demand.

### 4. Document Management

#### documents.document_storage
```sql
CREATE TABLE documents.document_storage (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    document_type VARCHAR(30) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL, -- Reference to encrypted storage (S3 path, etc.)
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    mime_type VARCHAR(100) NOT NULL,
    checksum_sha256 CHAR(64) NOT NULL, -- Hex encoded SHA-256
    upload_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    extraction_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed, needs_review
    extraction_confidence NUMERIC(3, 2) CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
    verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified', -- unverified, partially_verified, verified, disputed
    extracted_data JSONB, -- Structured data extracted from document
    page_count INTEGER, -- For PDFs
    is_encrypted BOOLEAN NOT NULL DEFAULT TRUE,
    encryption_key_id UUID, -- Reference to encryption key in secrets management
    virus_scan_status VARCHAR(20) DEFAULT 'pending', -- pending, clean, infected
    virus_scan_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_doc_type CHECK (document_type IN ('salary_slip', 'form_16', 'bank_statement', 'epf_statement', 'mutual_fund_statement', 'insurance_policy', 'loan_statement', 'tax_return', 'investment_statement', 'other')),
    CONSTRAINT chk_extraction_status CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed', 'needs_review')),
    CONSTRAINT chk_verification_status CHECK (verification_status IN ('unverified', 'partially_verified', 'verified', 'disputed')),
    CONSTRAINT chk_confidence_range CHECK (extraction_confidence IS NULL OR (extraction_confidence >= 0 AND extraction_confidence <= 1))
);

-- Indexes
CREATE INDEX idx_doc_user ON documents.document_storage(user_id);
CREATE INDEX idx_doc_type ON documents.document_storage(document_type);
CREATE INDEX idx_doc_upload_time ON documents.document_storage(upload_timestamp);
CREATE INDEX idx_doc_extraction_status ON documents.document_storage(extraction_status);
CREATE INDEX idx_doc_verification_status ON documents.document_storage(verification_status);
CREATE UNIQUE INDEX idx_doc_checksum ON documents.document_storage(checksum_sha256);
```

#### documents.extracted_fields
```sql
CREATE TABLE documents.extracted_fields (
    extracted_field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents.document_storage(document_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL, -- Standardized name like 'monthly_gross_salary'
    field_category VARCHAR(20) NOT NULL, -- income, deduction, asset_value, liability_amount, insurance_premium, tax_info, other
    extracted_value TEXT NOT NULL, -- Raw extracted value as string
    parsed_value NUMERIC(20, 6), -- Parsed numeric value (for currency, percentages, etc.)
    parsed_date DATE, -- Parsed date value
    parsed_text TEXT, -- Parsed text value
    data_type VARCHAR(20) NOT NULL, -- currency, date, percentage, text, integer
    source_location VARCHAR(100), -- Page number, table/cell reference if available
    extraction_method VARCHAR(20) NOT NULL, -- ocr, template_matching, rule_based, ml_model
    confidence_score NUMERIC(3, 2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    verified_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    user_corrected_value NUMERIC(20, 6), -- If user corrected the extraction
    user_corrected_date DATE,
    user_corrected_text TEXT,
    verification_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_field_category CHECK (field_category IN ('income', 'deduction', 'asset_value', 'liability_amount', 'insurance_premium', 'tax_info', 'other')),
    CONSTRAINT chk_data_type CHECK (data_type IN ('currency', 'date', 'percentage', 'text', 'integer')),
    CONSTRAINT chk_extraction_method CHECK (extraction_method IN ('ocr', 'template_matching', 'rule_based', 'ml_model')),
    CONSTRAINT chk_parsed_consistency CHECK (
        (data_type = 'currency' AND parsed_value IS NOT NULL) OR
        (data_type = 'date' AND parsed_date IS NOT NULL) OR
        (data_type = 'percentage' AND parsed_value IS NOT NULL) OR
        (data_type = 'text' AND parsed_text IS NOT NULL) OR
        (data_type = 'integer' AND parsed_value IS NOT NULL AND parsed_value = FLOOR(parsed_value))
    )
);

-- Indexes
CREATE INDEX idx_extracted_field_doc ON documents.extracted_fields(document_id);
CREATE INDEX idx_extracted_field_name ON documents.extracted_fields(field_name);
CREATE INDEX idx_extracted_field_category ON documents.extracted_fields(field_category);
CREATE INDEX idx_extracted_field_verified ON documents.extracted_fields(verified_by_user);
```

### 5. Financial Actions

#### financial.financial_actions
```sql
CREATE TABLE financial.financial_actions (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    action_type VARCHAR(30) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL, -- high, medium, low
    reason TEXT NOT NULL,
    source_calculation UUID, -- Reference to calculations table if applicable
    evidence JSONB, -- Supporting data or calculations
    due_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, in_progress, completed, dismissed, overdue
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_action_type CHECK (action_type IN ('build_emergency_fund', 'reduce_debt', 'increase_savings', 'review_insurance', 'optimize_tax', 'update_documents', 'goal_review', 'spending_analysis', 'investment_review', 'other')),
    CONSTRAINT chk_action_priority CHECK (priority IN ('high', 'medium', 'low')),
    CONSTRAINT chk_action_status CHECK (status IN ('pending', 'in_progress', 'completed', 'dismissed', 'overdue')),
    CONSTRAINT chk_due_date CHECK (due_date IS NULL OR due_date >= CURRENT_DATE),
    CONSTRAINT chk_completed_date CHECK (completed_at IS NULL OR completed_at >= created_at)
);

-- Indexes
CREATE INDEX idx_action_user ON financial.financial_actions(user_id);
CREATE INDEX idx_action_type ON financial.financial_actions(action_type);
CREATE INDEX idx_action_priority ON financial.financial_actions(priority);
CREATE INDEX idx_action_status ON financial.financial_actions(status);
CREATE INDEX idx_action_due_date ON financial.financial_actions(due_date) WHERE status IN ('pending', 'in_progress');
```

### 6. Calculation Audit Trail

#### financial.calculations
```sql
CREATE TABLE financial.calculations (
    calculation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    calculation_type VARCHAR(30) NOT NULL,
    inputs JSONB NOT NULL, -- Input values used
    assumptions JSONB NOT NULL, -- Assumptions made
    formula_used VARCHAR(200) NOT NULL, -- Description or identifier
    result NUMERIC(20, 6) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    software_version VARCHAR(50) NOT NULL,
    validated_by UUID, -- Reference to validation record or user
    validation_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_calc_type CHECK (calculation_type IN ('net_worth', 'savings_rate', 'debt_to_income', 'emergency_fund_months', 'freedom_number', 'freedom_gap', 'projected_corpus', 'sip_projection', 'loan_emi', 'tax_liability', 'other'))
);

-- Indexes
CREATE INDEX idx_calc_user ON financial.calculations(user_id);
CREATE INDEX idx_calc_type ON financial.calculations(calculation_type);
CREATE INDEX idx_calc_timestamp ON financial.calculations(timestamp);
CREATE INDEX idx_calc_user_type ON financial.calculations(user_id, calculation_type);
```

### 7. Audit and Security Logging

#### audit.audit_history
```sql
CREATE TABLE audit.audit_history (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES financial.users(user_id) ON DELETE CASCADE,
    event_type VARCHAR(30) NOT NULL,
    entity_type VARCHAR(30) NOT NULL,
    entity_id UUID NOT NULL,
    change_description TEXT NOT NULL,
    changed_fields JSONB, -- Specific fields that changed
    old_values JSONB, -- Previous values (excluding highly sensitive data)
    new_values JSONB, -- New values (excluding highly sensitive data)
    performed_by VARCHAR(10) NOT NULL, -- 'user' or 'system'
    ip_address INET, -- IP address of user (if applicable)
    user_agent TEXT, -- Browser/client information
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_audit_event_type CHECK (event_type IN ('data_created', 'data_updated', 'data_deleted', 'document_uploaded', 'document_extracted', 'goal_set', 'action_completed', 'login', 'password_changed', 'consent_given', 'consent_withdrawn')),
    CONSTRAINT chk_audit_entity_type CHECK (entity_type IN ('user', 'profile', 'income', 'expense', 'asset', 'liability', 'insurance', 'goal', 'document', 'financial_action')),
    CONSTRAINT chk_performed_by CHECK (performed_by IN ('user', 'system'))
);

-- Indexes
CREATE INDEX idx_audit_user ON audit.audit_history(user_id);
CREATE INDEX idx_audit_timestamp ON audit.audit_history(timestamp);
CREATE INDEX idx_audit_entity ON audit.audit_history(entity_type, entity_id);
CREATE INDEX idx_audit_event_type ON audit.audit_history(event_type);
CREATE INDEX idx_audit_performed_by ON audit.audit_history(performed_by);
```

### 8. Lookup and Reference Tables

#### lookup.enumerations
```sql
CREATE TABLE lookup.enumerations (
    enum_id SERIAL PRIMARY KEY,
    enum_name VARCHAR(50) NOT NULL, -- e.g., 'income_source_type', 'expense_category'
    enum_value VARCHAR(50) NOT NULL, -- e.g., 'salary', 'housing'
    enum_label VARCHAR(100) NOT NULL, -- Human-readable label
    enum_description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_enum_name_value UNIQUE (enum_name, enum_value)
);

-- Indexes
CREATE INDEX idx_enum_name ON lookup.enumerations(enum_name);
CREATE INDEX idx_enum_active ON lookup.enumerations(is_active) WHERE is_active = TRUE;
```

Populate with all enumeration values from the domain model.

## Security Considerations

### Encryption Strategy
1. **Application-Level Encryption**: Highly sensitive fields (when absolutely necessary to store) encrypted before storage
2. **Column-Level Encryption**: Use pgcrypto for specific columns if needed
3. **Tablespace Encryption**: Encrypt entire tablespaces for sensitive data
4. **File System Encryption**: Encrypt storage volumes at infrastructure level
5. **Backup Encryption**: Ensure backups are encrypted

### Data Minimization and Masking
- Store only last 4 digits of PAN, Aadhaar, account numbers
- Never store full sensitive identifiers
- Use reference IDs instead of exposing internal identifiers
- Implement data retention policies for temporary data

### Access Controls
- Row-Level Security (RLS) policies to restrict data access by user_id
- Separate database roles for different application components
- Principle of least privilege for database users
- Regular permission audits

### Audit and Monitoring
- Comprehensive audit logging as shown in schema
- Database activity monitoring for anomalous queries
- Alerting on suspicious access patterns
- Regular security reviews of database configuration

## Performance Optimization

### Indexing Strategy
- Primary keys on UUID columns (PostgreSQL handles UUID indexes efficiently)
- Foreign key indexes for join performance
- Composite indexes for common query patterns
- Indexes on frequently filtered columns (status, dates, types)
- Partial indexes for active records to reduce index size
- Covering indexes for frequent query patterns

### Partitioning Considerations
- **Audit Tables**: Partition by date (monthly or quarterly)
- **Calculation History**: Partition by date or user_id ranges
- **Document Storage**: Consider partitioning by upload date or user_id ranges for very large datasets
- **Financial Transactions**: If adding transaction-level data, partition by date

### Materialized Views
- For expensive aggregated calculations (net worth trends, expense categories over time)
- Refresh schedules based on data volatility and query frequency
- Concurrent refresh to avoid locking

### Connection Pooling
- Design schema to work efficiently with connection poolers (PgBouncer)
- Avoid long-running transactions
- Use prepared statements where beneficial

## Maintenance and Operations

### Backup Strategy
- **Logical Backups**: Regular pg_dump of schema and data
- **Physical Backups**: Base archiving or file system snapshots
- **Point-in-Time Recovery**: WAL archiving enabled
- **Backup Testing**: Regular restore tests
- **Geographic Replication**: For disaster recovery

### Maintenance Tasks
- **VACUUM and ANALYZE**: Regular scheduled runs
- **Index Maintenance**: REINDEX as needed based on bloat
- **Statistics Update**: Ensure planner has good statistics
- **Log Rotation**: Manage PostgreSQL log files
- **Extension Updates**: Keep PostgreSQL extensions current

### Scaling Considerations
- **Read Replicas**: For reporting and analytics workloads
- **Connection Pooling**: To handle concurrent user load
- **Caching Layer**: Redis for frequently accessed computed values
- **Database Sharding**: Consider user-id based sharding if single instance limits reached

## Migration and Evolution

### Schema Versioning
- Use migration tools like Flyway or Liquibase
- Maintain migration history table
- Test migrations on copy of production data
- Blue-green deployment strategy for zero-downtime migrations

### Handling Schema Changes
- Backward compatible changes where possible
- Default values for new columns
- Batch updates for large tables during low-traffic periods
- Feature flags for gradual rollout of new functionality

### Data Archiving
- Archive old audit logs to cold storage
- Consider moving inactive user data to archive tables
- Implement GDPR-style data deletion procedures
- Maintain referential integrity during archiving

## Sample Queries

### Net Worth Calculation
```sql
SELECT 
    u.user_id,
    COALESCE(SUM(a.current_value), 0) - COALESCE(SUM(l.principal_outstanding), 0) AS net_worth
FROM financial.users u
LEFT JOIN financial.assets a ON u.user_id = a.user_id AND a.is_active = TRUE
LEFT JOIN financial.liabilities l ON u.user_id = l.user_id AND l.is_active = TRUE
WHERE u.user_id = 'specific-user-uuid'
GROUP BY u.user_id;
```

### Monthly Cash Flow
```sql
SELECT 
    u.user_id,
    COALESCE(SUM(i.amount), 0) - COALESCE(SUM(e.amount), 0) AS monthly_cash_flow
FROM financial.users u
LEFT JOIN financial.income_sources i ON u.user_id = i.user_id AND i.is_active = TRUE AND i.frequency = 'monthly'
LEFT JOIN financial.expenses e ON u.user_id = e.user_id AND e.is_active = TRUE AND e.frequency = 'monthly'
WHERE u.user_id = 'specific-user-uuid'
GROUP BY u.user_id;
```

### Goal Progress
```sql
SELECT 
    g.goal_id,
    g.goal_name,
    g.target_amount,
    g.current_amount,
    ROUND((g.current_amount / g.target_amount) * 100, 2) AS progress_percentage,
    g.target_date,
    AGE(g.target_date, CURRENT_DATE) AS time_remaining
FROM financial.goals g
WHERE g.user_id = 'specific-user-uuid' AND g.is_active = TRUE
ORDER BY g.priority DESC, g.target_date ASC;
```

## Conclusion

This database schema provides a solid foundation for Financial Freedom Copilot, balancing the needs for:
- Data integrity and consistency
- Query performance and scalability
- Privacy and security compliance
- Extensibility for future features
- Auditability and compliance reporting

The design follows database normalization principles while incorporating practical considerations for financial data workloads. Proper indexing, partitioning strategies, and security measures ensure the system can scale effectively while maintaining the trustworthy handling of sensitive financial information.
