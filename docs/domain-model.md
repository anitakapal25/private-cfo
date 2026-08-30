# Financial Freedom Copilot - Domain Model

**Status:** Conceptual target model; not every entity is implemented  
**Last reviewed:** 2026-08-30  
**Authority:** ORM models and Alembic migrations define the current executable model.

## Overview
This document defines the core domain model for Financial Freedom Copilot (ArthaOS), representing the financial life of an Indian salaried employee seeking financial freedom. The model is designed to be comprehensive yet focused on the essential elements needed for financial planning, simulation, and goal tracking.

## Core Entities

### 1. User
The central entity representing an individual using the system.

**Attributes:**
- `user_id`: Unique identifier (UUID)
- `created_at`: Timestamp of account creation
- `updated_at`: Timestamp of last profile update
- `is_active`: Boolean indicating active status
- `date_of_user_birth`: Date of birth (for age calculations)
- `gender`: Optional demographic information
- `marital_status`: Marital status (single, married, divorced, widowed)
- `dependents_count`: Number of financial dependents
- `residential_status`: Resident Indian/NRI/etc. (for tax purposes)
- `pan_number`: Masked/stored securely (Permanent Account Number)
- `aadhaar_linked`: Boolean indicating if Aadhaar is linked (stored securely)
- `employment_status`: Employed/unemployed/self-employed/retired
- `primary_occupation`: Job title or profession
- **Relationships:**
  - Has one Profile
  - Has many Income sources
  - Has many Expense categories
  - Has many Assets
  - Has many Liabilities
  - Has many Insurance policies
  - Has many Goals
  - Has one FinancialFreedomTarget
  - Has many Documents
  - Has many FinancialActions
  - Has many Calculations (audit trail)
  - Has AuditHistory

### 2. Profile
Basic demographic and contact information.

**Attributes:**
- `profile_id`: Unique identifier
- `user_id`: Foreign key to User
- `full_name`: User's full name
- `email_address`: Primary email (verified)
- `phone_number`: Primary phone number (verified)
- `address_line1`: Street address
- `address_line2`: Additional address info
- `city`: City
- `state`: State
- `postal_code`: PIN code
- `country`: Country (default: India)
- `preferred_language`: Language for communication
- `timezone`: User's timezone
- `created_at`: Timestamp
- `updated_at`: Timestamp

### 3. Income
Represents money flowing into the user's financial system.

**Attributes:**
- `income_id`: Unique identifier
- `user_id`: Foreign key to User
- `source_type`: Enum [salary, bonus, freelance, rental, interest, dividend, pension, other]
- `source_name`: Descriptive name (e.g., "ABC Company Salary")
- `amount`: Monthly amount (Decimal)
- `currency`: Currency code (INR default)
- `frequency`: Enum [monthly, quarterly, annually, one-time]
- `is_taxable`: Boolean indicating taxability
- `tax_withheld`: Amount of tax already deducted (TDS)
- `start_date`: When this income began
- `end_date`: When this income ended (null for ongoing)
- `growth_rate`: Expected annual growth rate (Decimal)
- `is_active`: Boolean indicating current status
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Amount must be non-negative; dates must be logical

### 4. Expense
Represents money flowing out of the user's financial system.

**Attributes:**
- `expense_id`: Unique identifier
- `user_id`: Foreign key to User
- `category`: Enum [housing, food, transportation, utilities, healthcare, entertainment, education, personal care, insurance, loan_emis, investments, taxes, other]
- `subcategory`: More specific categorization (e.g., under "food": groceries, dining_out)
- `description`: Detailed description
- `amount`: Monthly amount (Decimal)
- `currency`: Currency code (INR default)
- `frequency`: Enum [monthly, quarterly, annually, one-time]
- `is_essential`: Boolean indicating necessity vs. discretionary
- `is_inflation_linked`: Boolean indicating if expense grows with inflation
- `inflation_rate`: Custom inflation rate if different from general (Decimal)
- `start_date`: When this expense began
- `end_date`: When this expense ended (null for ongoing)
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Amount must be non-negative

### 5. Asset
Represents resources owned by the user that have economic value.

**Attributes:**
- `asset_id`: Unique identifier
- `user_id`: Foreign key to User
- `asset_type`: Enum [cash, savings_account, fixed_deposit, recurring_deposit, epf, ppf, nps, mutual_funds, stocks, bonds, gold, real_estate, vehicle, other_investments]
- `account_name`: Descriptive name (e.g., "SBI Savings Account")
- `institution_name`: Bank or financial institution
- `account_number_masked`: Last 4 digits only for security
- `current_value`: Present market value (Decimal)
- `currency`: Currency code (INR default)
- `purchase_date`: Date of acquisition
- `expected_return_rate`: Annual expected return (Decimal)
- `risk_level`: Enum [low, medium, high]
- `liquidity`: Enum [high, medium, low] (how quickly convertible to cash)
- `is_joint_owned`: Boolean indicating joint ownership
- `joint_owner_details`: Information about co-owners (if applicable)
- `nominee_details`: Information about nominee
- `maturity_date`: For fixed-term instruments
- `is_active`: Boolean indicating if still held
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Value must be non-negative

### 6. Liability
Represents debts or obligations owed by the user.

**Attributes:**
- `liability_id`: Unique identifier
- `user_id`: Foreign key to User
- `liability_type`: Enum [home_loan, personal_loan, car_loan, education_loan, credit_card_due, personal_loan, business_loan, other]
- `lender_name`: Name of lending institution
- `account_number_masked`: Last 4 digits only for security
- `principal_outstanding`: Remaining principal amount (Decimal)
- `currency`: Currency code (INR default)
- `interest_rate`: Annual interest rate (Decimal)
- `interest_type`: Enum [fixed, floating, reducing_balance]
- `emi_amount`: Monthly EMI amount (Decimal)
- `total_emis`: Total number of EMIs
- `emis_paid`: Number of EMIs already paid
- `start_date`: Loan initiation date
- `end_date`: Expected completion date
- `prepayment_penalty`: Details about prepayment charges
- `is_tax_deductible`: Boolean indicating tax benefits (e.g., home loan interest)
- `is_active`: Boolean indicating if still owed
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Amounts must be non-negative; dates must be logical

### 7. Insurance
Represents insurance policies held by the user.

**Attributes:**
- `insurance_id`: Unique identifier
- `user_id`: Foreign key to User
- `insurance_type`: Enum [life_term, life_endowment, health_individual, health_family, critical_illness, personal_accident, property, vehicle, other]
- `policy_number_masked`: Masked policy number for reference
- `provider_name`: Insurance company name
- `sum_assured`: Coverage amount (Decimal)
- `currency`: Currency code (INR default)
- `premium_amount`: Premium payment amount (Decimal)
- `premium_frequency`: Enum [monthly, quarterly, semi-annual, annual]
- `start_date`: Policy start date
- `end_date`: Policy end date
- `maturity_date`: For endowment policies
- `beneficiaries`: List of beneficiaries with relationships
- `nominee_details`: Policy nominee information
- `riders`: Additional coverage riders
- `is_active`: Boolean indicating if policy is in force
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Dates must be logical; amounts non-negative

### 8. Goal
Represents specific financial objectives the user wants to achieve.

**Attributes:**
- `goal_id`: Unique identifier
- `user_id`: Foreign key to User
- `goal_type`: Enum [emergency_fund, home_purchase, education, retirement, vehicle_purchase, vacation, debt_free, wealth_creation, other]
- `goal_name`: Descriptive name (e.g., "Down Payment for Home")
- `target_amount`: Required amount to achieve goal (Decimal)
- `currency`: Currency code (INR default)
- `target_date`: Date by which goal should be achieved
- `priority`: Enum [high, medium, low]
- `current_amount`: Amount already saved toward goal (Decimal)
- `monthly_contribution`: Planned monthly savings toward goal (Decimal)
- `expected_return`: Expected return on goal-specific investments (Decimal)
- `inflation_adjusted`: Boolean indicating if target amount adjusts for inflation
- `notes`: Additional details or constraints
- `is_active`: Boolean indicating if goal is currently pursued
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Target date must be in future; amounts non-negative

### 9. FinancialFreedomTarget
Represents the user's definition of financial freedom.

**Attributes:**
- `ff_target_id`: Unique identifier
- `user_id`: Foreign key to User (one-to-one)
- `target_age`: Age at which user desires financial freedom
- `target_lifestyle_expenses`: Monthly expenses desired at financial freedom (Decimal)
- `currency`: Currency code (INR default)
- `inflation_assumption`: Expected inflation rate until target age (Decimal)
- `return_assumption`: Expected investment return rate until target age (Decimal)
- `current_age`: Calculated from date_of_birth (derived, not stored)
- `years_to_target`: Calculated difference (derived)
- `required_corpus`: Calculated corpus needed (derived)
- `current_projected_corpus`: Projected corpus at target age based on current trajectory (derived)
- `freedom_gap`: Difference between required and projected corpus (derived)
- `projected_freedom_age`: Age at which financial freedom will be achieved with current trajectory (derived)
- `assumptions_documents`: References to documents justifying assumptions
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Target age must be > current age; amounts non-negative; rates reasonable

### 10. Document
Represents uploaded financial documents.

**Attributes:**
- `document_id`: Unique identifier
- `user_id`: Foreign key to User
- `document_type`: Enum [salary_slip, form_16, bank_statement, epf_statement, mutual_fund_statement, insurance_policy, loan_statement, tax_return, investment_statement, other]
- `original_filename`: Name of file as uploaded
- `storage_path`: Encrypted storage location/reference
- `file_size`: Size in bytes
- `mime_type`: MIME type of file
- `checksum_sha256`: Cryptographic hash for integrity verification
- `upload_timestamp`: When document was uploaded
- `extraction_status`: Enum [pending, processing, completed, failed, needs_review]
- `extraction_confidence`: Overall confidence score (0-1 Decimal)
- `verification_status`: Enum [unverified, partially_verified, verified, disputed]
- `extracted_data`: JSON blob of structured data extracted (validated against schemas)
- `page_count`: Number of pages (for PDFs)
- `is_encrypted`: Boolean indicating if file is stored encrypted
- `encryption_key_id`: Reference to encryption key used
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Relationships:** May have many ExtractedField entries

### 11. ExtractedField
Individual data points extracted from documents.

**Attributes:**
- `extracted_field_id`: Unique identifier
- `document_id`: Foreign key to Document
- `field_name`: Standardized name of field (e.g., "monthly_gross_salary", "epf_employee_contribution")
- `field_category`: Enum [income, deduction, asset_value, liability_amount, insurance_premium, tax_info, other]
- `extracted_value`: Value as extracted (String for flexibility)
- `parsed_value`: Value after parsing to appropriate type (Decimal, Date, etc.)
- `data_type`: Enum [currency, date, percentage, text, integer]
- `source_location`: Page number, table/cell reference if available
- `extraction_method`: Enum [ocr, template_matching, rule_based, ml_model]
- `confidence_score`: Confidence in this specific extraction (0-1 Decimal)
- `verified_by_user`: Boolean indicating user confirmation
- `user_corrected_value`: Value if user corrected extraction
- `verification_timestamp`: When verification/correction happened
- `created_at`: Timestamp
- `updated_at`: Timestamp
- **Validation:** Must relate to valid financial field; data type consistency

### 12. FinancialAction
Recommended actions for the user to improve financial health.

**Attributes:**
- `action_id`: Unique identifier
- `user_id`: Foreign key to User
- `action_type`: Enum [build_emergency_fund, reduce_debt, increase_savings, review_insurance, optimize_tax, update_documents, goal_review, spending_analysis, investment_review, other]
- `title`: Short description of action
- `description`: Detailed explanation
- `priority`: Enum [high, medium, low] (based on impact and urgency)
- `reason`: Explanation why this action is recommended
- `source_calculation`: Reference to which calculation/metric triggered this action
- `evidence`: Supporting data or calculations
- `due_date`: Suggested completion date
- `status`: Enum [pending, in_progress, completed, dismissed, overdue]
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `completed_at`: Timestamp when completed (if applicable)
- **Relationships:** May link to specific Goals, Assets, Liabilities

### 13. Calculation
Audit trail of financial calculations performed.

**Attributes:**
- `calculation_id`: Unique identifier
- `user_id`: Foreign key to User
- `calculation_type`: Enum [net_worth, savings_rate, debt_to_income, emergency_fund_months, freedom_number, freedom_gap, projected_corpus, sip_projection, loan_emi, tax_liability, other]
- `inputs`: JSON blob of input values used
- `assumptions`: JSON blob of assumptions made
- `formula_used`: Description or identifier of formula applied
- `result`: Calculated result (Decimal)
- `currency`: Currency code (INR default)
- `timestamp`: When calculation was performed
- `software_version`: Version of calculation engine used
- `validated_by`: Reference to validation (if any)
- `created_at`: Timestamp
- **Relationships:** May link to specific Goals, FinancialFreedomTarget

### 14. AuditHistory
Log of significant changes to user's financial data for security and compliance.

**Attributes:**
- `audit_id`: Unique identifier
- `user_id`: Foreign key to User
- `event_type`: Enum [data_created, data_updated, data_deleted, document_uploaded, document_extracted, goal_set, action_completed, login, password_changed, consent_given, consent_withdrawn]
- `entity_type`: Enum [user, profile, income, expense, asset, liability, insurance, goal, document, financial_action]
- `entity_id`: ID of affected entity
- `change_description": Human-readable description of change
- `changed_fields": JSON blob of specific fields that changed
- `old_values": JSON blob of previous values (if applicable and not sensitive)
- `new_values": JSON blob of new values (if applicable and not sensitive)
- `performed_by": Enum [user, system] - who/what initiated change
- `ip_address": IP address of user (if applicable)
- `user_agent": Browser/client information (if applicable)
- `timestamp": When event occurred
- `created_at": Timestamp

## Value Objects

### Money
Represents a monetary amount with currency.
- `amount`: Decimal value
- `currency`: String ISO 4217 currency code (default: INR)
- Methods for conversion, formatting, arithmetic operations

### DateRange
Represents a period of time.
- `start_date`: Date
- `end_date`: Date (nullable for ongoing periods)
- Methods for duration calculation, overlap detection

### Percentage
Represents a ratio or rate.
- `value`: Decimal value (0.05 for 5%)
- Methods for conversion to/from basis points, formatting

## Enumerations (Enums)

### IncomeSourceType
- salary, bonus, freelance, rental, interest, dividend, pension, other

### ExpenseCategory
- housing, food, transportation, utilities, healthcare, entertainment, education, personal care, insurance, loan_emis, investments, taxes, other

### AssetType
- cash, savings_account, fixed_deposit, recurring_deposit, epf, ppf, nps, mutual_funds, stocks, bonds, gold, real_estate, vehicle, other_investments

### LiabilityType
- home_loan, personal_loan, car_loan, education_loan, credit_card_due, business_loan, other

### InsuranceType
- life_term, life_endowment, health_individual, health_family, critical_illness, personal_accident, property, vehicle, other

### GoalType
- emergency_fund, home_purchase, education, retirement, vehicle_purchase, vacation, debt_free, wealth_creation, other

### PriorityLevel
- high, medium, low

### Frequency
- monthly, quarterly, semi-annual, annually, one-time

### YesNo
- true, false (though Boolean is preferred in most cases)

### DocumentType
- salary_slip, form_16, bank_statement, epf_statement, mutual_fund_statement, insurance_policy, loan_statement, tax_return, investment_statement, other

### ExtractionStatus
- pending, processing, completed, failed, needs_review

### VerificationStatus
- unverified, partially_verified, verified, disputed

### ActionType
- build_emergency_fund, reduce_debt, increase_savings, review_insurance, optimize_tax, update_documents, goal_review, spending_analysis, investment_review, other

### CalculationType
- net_worth, savings_rate, debt_to_income, emergency_fund_months, freedom_number, freedom_gap, projected_corpus, sip_projection, loan_emi, tax_liability, other

### AuditEventType
- data_created, data_updated, data_deleted, document_uploaded, document_extracted, goal_set, action_completed, login, password_changed, consent_given, consent_withdrawn

### AuditEntityType
- user, profile, income, expense, asset, liability, insurance, goal, document, financial_action

## Relationships Summary

### User-Centric Relationships
- User 1:1 Profile
- User 1:many Income
- User 1:many Expense
- User 1:many Asset
- User 1:many Liability
- User 1:many Insurance
- User 1:many Goal
- User 1:1 FinancialFreedomTarget
- User 1:many Document
- User 1:many FinancialAction
- User 1:many Calculation
- User 1:many AuditHistory

### Document Relationships
- Document 1:many ExtractedField

## Derived Fields and Calculations

### Calculated Attributes (not stored directly)
- User.age: Calculated from date_of_birth
- FinancialFreedomTarget.years_to_target: target_age - current_age
- FinancialFreedomTarget.required_corpus: Present value of target lifestyle expenses
- FinancialFreedomTarget.current_projected_corpus: Future value of current assets and savings
- FinancialFreedomTarget.freedom_gap: required_corpus - current_projected_corpus
- FinancialFreedomTarget.projected_freedom_age: Age when projected corpus meets required corpus
- Net Worth: Sum of all assets - Sum of all liabilities
- Monthly Savings: Sum of income - Sum of expenses
- Savings Rate: Monthly Savings / Monthly Income
- Debt-to-Income Ratio: Monthly debt payments / Monthly Gross Income
- Emergency Fund Months: Liquid assets / Monthly essential expenses

## Constraints and Business Rules

### Data Integrity
1. All monetary values must be non-negative (except where logically negative makes sense, like investment returns)
2. Dates must be logically consistent (start before end, birth dates in past, etc.)
3. Percentages and rates must be within reasonable bounds (e.g., 0-100% for returns, though negative allowed for losses)
4. Currency consistency: All amounts in a calculation should use same currency or be converted
5. Document extractions must maintain referential integrity to source documents

### Temporal Constraints
1. No future dates for past events (income start dates, etc.)
2. Retirement age typically between 55-70 (configurable bounds)
3. Loan tenors typically not exceeding 30 years
4. Insurance policy durations reasonable for type

### Financial Logic
1. Emergency fund target typically 3-6 months of essential expenses
2. Savings rate should not exceed 100% (though could temporarily if expenses < income)
3. Debt-to-income ratio ideally below 0.4 (40%)
4. Insurance coverage should be adequate for dependents and liabilities
5. Investment allocation should consider age and risk tolerance

### Privacy and Security
1. Sensitive identifiers (PAN, Aadhaar, full account numbers) never stored in plain text
2. All sensitive data encrypted at rest
3. Access to sensitive data requires explicit authorization
4. Audit trail maintains history of who accessed/modified what

## Extensibility Considerations

### Adding New Entity Types
- Follow pattern of: unique ID, user foreign key, descriptive attributes, timestamps
- Consider if entity should support versioning/history
- Define clear relationships to other entities
- Add appropriate validation rules

### Adding New Enumeration Values
- Ensure backward compatibility
- Update validation logic
- Consider impact on calculations and reports
- Update any hardcoded references in business logic

### Adding New Calculation Types
- Define inputs, assumptions, formula
- Create appropriate Calculation record
- Consider if result should be stored as derived field on entities
- Add to audit trail mechanisms

## Interface Definitions (for Service Layer)

### UserRepository
- findById(userId): User
- findByEmail(email): User
- create(user): User
- update(user): User
- delete(userId): void
- listActive(): List<User>

### FinancialDataRepository
- getIncomeSummary(userId, dateRange): IncomeSummary
- getExpenseSummary(userId, dateRange): ExpenseSummary
- getAssetSummary(userId): AssetSummary
- getLiabilitySummary(userId): LiabilitySummary
- getNetWorth(userId): Money
- getCashFlow(userId, period): CashFlowStatement

### GoalRepository
- getActiveGoals(userId): List<Goal>
- getGoalProgress(goalId): GoalProgress
- updateContribution(goalId, amount): void

### DocumentRepository
- uploadDocument(userId, file): Document
- getDocument(documentId): Document
- updateExtraction(documentId, extractedData): void
- verifyExtraction(documentId, fieldId, verifiedValue): void
- searchDocuments(userId, criteria): List<Document>

### CalculationService
- calculateNetWorth(userId, asOfDate): CalculationResult
- calculateSavingsRate(userId, period): CalculationResult
- calculateFreedomNumber(userId, assumptions): CalculationResult
- projectCorpus(userId, assumptions, years): CalculationResult
- runScenario(userId, scenarioParameters): CalculationResult

This domain model provides a comprehensive foundation for the Financial Freedom Copilot system, capturing all essential financial aspects of an Indian salaried employee while maintaining flexibility for future enhancements.
