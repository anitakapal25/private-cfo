# Financial Freedom Copilot - AI and Tool Architecture

**Status:** Target tool architecture; current agent is a deterministic keyword router  
**Last reviewed:** 2026-08-30  
**Current boundary:** Private agent routes derive `user_id` from the authenticated user. Tool-level policy objects, persistent audit logs, public research tools and LLM evaluation remain planned.

## Overview
This document describes the AI agent and tool architecture for Financial Freedom Copilot (ArthaOS). The architecture follows the principle of having a primary financial agent that interacts with the system through well-defined, secure tools, ensuring that the LLM never has direct access to data or computational resources.

## Core AI Architecture Principles

### 1. Agent as Interface, Not Authority
- The AI agent serves as a conversational interface and reasoning layer
- The agent does not serve as the source of truth for financial calculations or data
- All factual information must come from tools or deterministic calculation engines
- The agent explains, reasons, and guides but does not compute financial truths

### 2. Tool-Mediated Access
- The agent interacts with the system exclusively through predefined tools
- No direct database queries, file access, or external API calls from the agent
- Tools encapsulate all data access, validation, and business logic
- Tool interfaces are strictly typed and validated

### 3. Deterministic Calculation Separation
- Financial calculations are performed by validated deterministic engines
- The agent may call calculation tools but never performs calculations itself
- All assumptions in calculations are explicit and visible
- Calculation results are verifiable and auditable

### 4. Least Privilege Tool Design
- Each tool provides access to only the specific data or function needed
- Tools return minimum necessary data to fulfill requests
- No tool provides unrestricted access to user financial data
- Tools implement appropriate authorization checks

### 5. Public-Private Data Separation
- Tools accessing public financial information are isolated from private data tools
- No tool allows cross-contamination between public research and private data access
- Public research tools cannot access private user financial information
- Clear boundaries prevent prompt injection from affecting data access

### 6. Error Handling and Graceful Degradation
- Tools return structured error responses that the agent can interpret
- The agent handles missing data, calculation errors, and tool failures gracefully
- Uncertainty is communicated clearly to users
- The system provides helpful guidance even when some functionality is unavailable

## Agent Responsibilities

The primary financial agent has these core responsibilities:

### 1. Intent Understanding
- Parse user requests to determine financial planning needs
- Identify what information is required to fulfill the request
- Recognize when clarification is needed
- Distinguish between different types of queries (informational, calculational, action-oriented)

### 2. Tool Orchestration
- Select appropriate tools based on user intent
- Sequence tool calls logically (e.g., get data → calculate → explain)
- Handle tool dependencies and data flow between tools
- Manage asynchronous tool execution where beneficial

### 3. Data Synthesis and Explanation
- Combine information from multiple tools into coherent responses
- Explain calculation results in user-friendly terms
- Translate technical financial concepts into accessible language
- Provide context and benchmarks where helpful

### 4. Guidance and Education
- Offer evidence-based financial education relevant to user's situation
- Explain financial concepts, rules, and strategies
- Reference authoritative sources for financial information
- Avoid giving specific product recommendations without proper licensing

### 5. Action Planning
- Generate specific, actionable recommendations based on financial analysis
- Prioritize actions by impact and urgency
- Connect actions to user goals and financial health metrics
- Provide clear implementation steps for recommended actions

### 6. Uncertainty Management
- Acknowledge when data is missing or uncertain
- Explain limitations of calculations or projections
- Suggest ways to improve data quality or reduce uncertainty
- Distinguish between guaranteed outcomes and probabilistic projections

### 7. Escalation Recognition
- Identify situations requiring human financial professional advice
- Recognize high-risk financial scenarios that need expert review
- Know when to suggest consulting a certified financial planner
- Understand regulatory boundaries of what the system can advise

## Tool Categories and Interfaces

The system provides tools organized by function, each with clear input/output contracts.

### 1. User Profile and Preference Tools

#### get_user_profile()
- **Purpose**: Retrieve basic user profile information
- **Input**: user_id (from authentication context)
- **Output**: 
  ```json
  {
    "user_id": "uuid",
    "date_of_birth": "YYYY-MM-DD",
    "age": integer,
    "marital_status": "string",
    "dependents_count": integer,
    "residential_status": "string",
    "employment_status": "string",
    "primary_occupation": "string",
    "profile": {
      "full_name": "string",
      "email_verified": boolean,
      "phone_verified": boolean,
      "preferred_language": "string",
      "timezone": "string"
    }
  }
  ```
- **Security**: Only returns profile information, no sensitive identifiers
- **Caching**: Profile data can be cached briefly as it changes infrequently

#### get_user_preferences()
- **Purpose**: Retrieve user preferences and settings
- **Input**: user_id
- **Output**: Preferences for notifications, privacy, display, etc.
- **Security**: No financial data exposed

### 2. Financial Data Access Tools

These tools provide aggregated views of financial data without exposing raw sensitive details unnecessarily.

#### get_income_summary(user_id, period_start, period_end)
- **Purpose**: Get summary of user's income
- **Input**: 
  - user_id (from auth context)
  - period_start: ISO date string
  - period_end: ISO date string
- **Output**:
  ```json
  {
    "total_monthly_income": {
      "amount": number,
      "currency": "INR"
    },
    "sources": [
      {
        "source_type": "salary|bonus|freelance|etc",
        "source_name": "string",
        "monthly_amount": number,
        "is_taxable": boolean,
        "growth_rate": number
      }
    ],
    "tax_withheld_monthly": number,
    "net_monthly_income": number,
    "currency": "INR",
    "period": {
      "start": "YYYY-MM-DD",
      "end": "YYYY-MM-DD"
    },
    "data_as_of": "timestamp"
  }
  ```
- **Security**: Returns aggregated and categorized data, not individual transaction details
- **Validation**: Verifies date range is reasonable

#### get_expense_summary(user_id, period_start, period_end)
- **Purpose**: Get summary of user's expenses
- **Input**: Similar to income summary
- **Output**:
  ```json
  {
    "total_monthly_expenses": {
      "amount": number,
      "currency": "INR"
    },
    "essential_monthly_expenses": {
      "amount": number,
      "currency": "INR"
    },
    "discretionary_monthly_expenses": {
      "amount": number,
      "currency": "INR"
    },
    "categories": [
      {
        "category": "housing|food|transportation|etc",
        "monthly_amount": number,
        "is_essential": boolean,
        "subcategory_breakdown": [
          {
            "subcategory": "string",
            "amount": number
          }
        ]
      }
    ],
    "currency": "INR",
    "period": {
      "start": "YYYY-MM-DD",
      "end": "YYYY-MM-DD"
    }
  }
  ```
- **Security**: Aggregated by category, no itemized transaction data

#### get_asset_summary(user_id, include_details=false)
- **Purpose**: Get summary of user's assets
- **Input**:
  - user_id
  - include_details: boolean (if true, returns more granular data but still masked)
- **Output** (simplified):
  ```json
  {
    "total_asset_value": {
      "amount": number,
      "currency": "INR"
    },
    "asset_types": [
      {
        "type": "savings_account|fixed_deposit|mutual_funds|etc",
        "total_value": number,
        "currency": "INR",
        "count": integer,
        "average_return_rate": number
      }
    ],
    "liquidity_breakdown": {
      "high": number, // value of highly liquid assets
      "medium": number,
      "low": number
    },
    "currency": "INR",
    "data_as_of": "timestamp"
  }
  ```
- **Security**: 
  - Never returns full account numbers
  - Masked identifiers only (last 4 digits)
  - Institution names may be included but not full details
  - With include_details=false, returns only aggregated totals by type

#### get_liability_summary(user_id, include_details=false)
- **Purpose**: Get summary of user's liabilities/debts
- **Input**: Similar to asset summary
- **Output**:
  ```json
  {
    "total_liability_outstanding": {
      "amount": number,
      "currency": "INR"
    },
    "total_monthly_emis": {
      "amount": number,
      "currency": "INR"
    },
    "liability_types": [
      {
        "type": "home_loan|personal_loan|car_loan|etc",
        "total_outstanding": number,
        "total_emi": number,
        "currency": "INR",
        "count": integer,
        "average_interest_rate": number,
        "is_tax_deductible": boolean
      }
    ],
    "currency": "INR",
    "data_as_of": "timestamp"
  }
  ```
- **Security**: Same protections as asset summary

#### get_insurance_summary(user_id)
- **Purpose**: Get summary of user's insurance coverage
- **Input**: user_id
- **Output**:
  ```json
  {
    "total_sum_assured": {
      "amount": number,
      "currency": "INR"
    },
    "total_monthly_premiums": {
      "amount": number,
      "currency": "INR"
    },
    "policies": [
      {
        "type": "life_term|health_individual|etc",
        "sum_assured": number,
        "premium_amount": number,
        "premium_frequency": "monthly|quarterly|etc",
        "provider_name": "string",
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "currency": "INR"
      }
    ],
    "currency": "INR",
    "data_as_of": "timestamp"
  }
  ```
- **Security**: Policy numbers masked, no sensitive personal data

### 3. Calculation Tools

These tools interface with the deterministic calculation engine. They never perform calculations themselves but invoke the calculation service.

#### calculate_net_worth(user_id, as_of_date=null)
- **Purpose**: Calculate user's net worth
- **Input**:
  - user_id
  - as_of_date: optional ISO date string (defaults to current date)
- **Output**:
  ```json
  {
    "net_worth": {
      "amount": number,
      "currency": "INR"
    },
    "total_assets": {
      "amount": number,
      "currency": "INR"
    },
    "total_liabilities": {
      "amount": number,
      "currency": "INR"
    },
    "calculation_details": {
      "assets_by_type": [
        {
          "type": "string",
          "value": number
        }
      ],
      "liabilities_by_type": [
        {
          "type": "string",
          "outstanding": number
        }
      ]
    },
    "assumptions": {
      "valuation_method": "current_market_value",
      "currency": "INR",
      "date": "YYYY-MM-DD"
    },
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```
- **Security**: 
  - Only calls authorized calculation functions
  - Input validation performed by calculation service
  - Result includes audit trail ID

#### calculate_savings_rate(user_id, period_months=1)
- **Purpose**: Calculate user's savings rate
- **Input**:
  - user_id
  - period_months: integer (default 1 for current month)
- **Output**:
  ```json
  {
    "savings_rate": number, // decimal (0.15 for 15%)
    "monthly_income": {
      "amount": number,
      "currency": "INR"
    },
    "monthly_expenses": {
      "amount": number,
      "currency": "INR
    },
    "monthly_savings": {
      "amount": number,
      "currency": "INR"
    },
    "calculation_details": {
      "income_sources": [...],
      "expense_categories": [...]
    },
    "assumptions": {
      "period_calculation": "simple_monthly_average",
      "currency": "INR"
    },
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```

#### calculate_freedom_number(user_id, assumptions_override=null)
- **Purpose**: Calculate the financial freedom number (target corpus)
- **Input**:
  - user_id
  - assumptions_override: optional object to override default assumptions
    ```json
    {
      "inflation_rate": number, // e.g., 0.06 for 6%
      "return_rate": number, // e.g., 0.10 for 10%
      "target_age": integer // overrides user's target age if provided
    }
    ```
- **Output**:
  ```json
  {
    "freedom_number": {
      "amount": number,
      "currency": "INR"
    },
    "current_age": integer,
    "target_age": integer,
    "years_to_target": integer,
    "target_monthly_expenses": {
      "amount": number,
      "currency": "INR"
    },
    "assumptions_used": {
      "inflation_rate": number,
      "return_rate": number,
      "target_lifestyle_expenses": {
        "amount": number,
        "currency": "INR"
      }
    },
    "calculation_details": {
      "present_value_calculation": "PV = FV / (1 + r)^n",
      "steps": [...]
    },
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```
- **Security**: 
  - Validates assumptions are within reasonable bounds
  - Never uses user-provided assumptions without validation
  - Overrides only apply if they pass validation

#### calculate_freedom_projection(user_id, contribution_scenario=null)
- **Purpose**: Project corpus at target age based on current trajectory
- **Input**:
  - user_id
  - contribution_scenario: optional object to test different scenarios
    ```json
    {
      "additional_monthly_investment": number,
      "return_rate_adjustment": number, // e.g., -0.02 for 2% lower returns
      "inflation_rate_adjustment": number
    }
    ```
- **Output**:
  ```json
  {
    "projected_corpus_at_target_age": {
      "amount": number,
      "currency": "INR"
    },
    "current_trajectory": {
      "current_monthly_investment": number,
      "expected_return_rate": number,
      "projected_value": number
    },
    "scenarios": [
      {
        "scenario_name": "string",
        "description": "string",
        "projected_value": number,
        "difference_from_base": number
      }
    ],
    "assumptions": {
      "inflation_rate": number,
      "return_rate": number,
      "current_savings_rate": number
    },
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```

#### calculate_freedom_gap(user_id)
- **Purpose**: Calculate the gap between required corpus and projected corpus
- **Input**: user_id
- **Output**:
  ```json
  {
    "freedom_gap": {
      "amount": number,
      "currency": "INR
    },
    "freedom_number": {...}, // from calculate_freedom_number
    "projected_corpus": {...}, // from calculate_freedom_projection base scenario
    "gap_percentage": number, // (gap / freedom_number) * 100
    "months_of_savings_needed": number, // at current savings rate
    "required_monthly_savings_increase": number, // additional monthly needed
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```

#### run_financial_scenario(user_id, scenario_parameters)
- **Purpose**: Run a customizable financial scenario (what-if analysis)
- **Input**:
  - user_id
  - scenario_parameters: object defining what to vary
    ```json
    {
      "scenario_name": "string",
      "variable_changes": {
        "monthly_income_change": number, // percentage or absolute
        "monthly_expenses_change": number,
        "investment_return_change": number,
        "inflation_rate_change": number,
        "additional_investment": number,
        "target_age_change": integer // years to add/subtract
      },
      "duration_years": integer // how far to project
    }
    ```
- **Output**:
  ```json
  {
    "scenario_results": {
      "base_case": {
        "net_worth_projection": [...], // array of yearly values
        "freedom_age": number,
        "corpus_at_freedom_age": number
      },
      "modified_case": {
        "net_worth_projection": [...],
        "freedom_age": number,
        "corpus_at_freedom_age": number
      },
      "comparison": {
        "freedom_age_difference": number,
        "corpus_difference": number,
        "key_drivers": ["string"] // list of what changed most
      }
    },
    "assumptions": {
      "base_case": {...},
      "modified_case": {...}
    },
    "calculation_id": "uuid",
    "timestamp": "ISO timestamp"
  }
  ```
- **Security**:
  - Validates all scenario parameters are within reasonable bounds
  - Prevents extreme values that could cause computational issues
  - Limits scenario complexity to prevent abuse

### 4. Goal Management Tools

#### get_user_goals(user_id, active_only=true)
- **Purpose**: Retrieve user's financial goals
- **Input**:
  - user_id
  - active_only: boolean (default true)
- **Output**:
  ```json
  {
    "goals": [
      {
        "goal_id": "uuid",
        "goal_type": "emergency_fund|home_purchase|etc",
        "goal_name": "string",
        "target_amount": {
          "amount": number,
          "currency": "INR"
        },
        "target_date": "YYYY-MM-DD",
        "priority": "high|medium|low",
        "current_amount": {
          "amount": number,
          "currency": "INR
        },
        "monthly_contribution": {
          "amount": number,
          "currency": "INR
        },
        "progress_percentage": number,
        "months_remaining": number,
        "on_track": boolean,
        "expected_return": number,
        "inflation_adjusted": boolean
      }
    ],
    "summary": {
      "total_goals": integer,
      "active_goals": integer,
      "high_priority_goals": integer,
      "total_target_amount": {
        "amount": number,
        "currency": "INR
      },
      "total_current_amount": {
        "amount": number,
        "currency": "INR
      }
    }
  }
  ```

#### update_goal_progress(goal_id, amount_added, contribution_date=null)
- **Purpose**: Record progress toward a goal
- **Input**:
  - goal_id: UUID
  - amount_added: number (amount contributed since last update)
  - contribution_date: optional ISO date (defaults to today)
- **Output**:
  ```json
  {
    "goal_id": "uuid",
    "previous_amount": {
      "amount": number,
      "currency": "INR
    },
    "added_amount": {
      "amount": number,
      "currency": "INR
    },
    "new_total": {
      "amount": number,
      "currency": "INR
    },
    "progress_percentage": number,
    "updated_at": "ISO timestamp",
    "contribution_recorded": {
      "amount": number,
      "date": "YYYY-MM-DD"
    }
  }
  ```
- **Security**: 
  - Validates goal_id belongs to current user
  - Validates amount is non-negative
  - Validates date is not in future (unless special case)

#### create_goal(user_id, goal_details)
- **Purpose**: Create a new financial goal
- **Input**:
  - user_id (from auth context)
  - goal_details: object
    ```json
    {
      "goal_type": "emergency_fund|home_purchase|etc",
      "goal_name": "string",
      "target_amount": {
        "amount": number,
        "currency": "INR
      },
      "target_date": "YYYY-MM-DD",
      "priority": "high|medium|low",
      "monthly_contribution": {
        "amount": number,
        "currency": "INR
      },
      "expected_return": number,
      "inflation_adjusted": boolean,
      "notes": "string"
    }
    ```
- **Output**:
  ```json
  {
    "goal_id": "uuid",
    "goal": { /* full goal object as returned by get_user_goals */ },
    "created_at": "ISO timestamp",
    "validation_notes": ["string"] // any warnings or suggestions
  }
  ```
- **Security**:
  - Validates all inputs
  - Ensures target_date is in future
  - Validates financial reasonableness (e.g., monthly contribution doesn't exceed income)
  - Returns suggested improvements if applicable

### 5. Document Processing Tools

These tools handle the secure processing of uploaded financial documents.

#### upload_document(user_id, file_metadata, encrypted_file_content)
- **Purpose**: Securely upload a financial document for processing
- **Input**:
  - user_id (from auth context)
  - file_metadata: object
    ```json
    {
      "original_filename": "string",
      "file_size": integer,
      "mime_type": "string",
      "document_type": "salary_slip|form_16|bank_statement|etc"
    }
    ```
  - encrypted_file_content: string (base64 encrypted content, or reference to pre-encrypted storage)
- **Output**:
  ```json
  {
    "document_id": "uuid",
    "upload_timestamp": "ISO timestamp",
    "extraction_status": "pending",
    "document": {
      "document_id": "uuid",
      "original_filename": "string",
      "document_type": "string",
      "upload_timestamp": "ISO timestamp",
      "file_size": integer,
      "mime_type": "string"
    },
    "next_steps": [
      "Document will be processed in secure sandbox",
      "You will be notified when extraction is complete",
      "Please review extracted data for accuracy"
    ]
  }
  ```
- **Security**:
  - File must be encrypted before upload or use secure upload mechanism
  - Virus and malware scanning performed immediately
  - Document stored in quarantine until processed
  - No extraction or data access until user initiates processing

#### start_document_extraction(document_id, encryption_key_reference)
- **Purpose**: Initiate secure extraction of data from uploaded document
- **Input**:
  - document_id: UUID
  - encryption_key_reference: reference to decryption key (if end-to-end encrypted)
- **Output**:
  ```json
  {
    "extraction_job_id": "uuid",
    "document_id": "uuid",
    "status": "processing",
    "estimated_completion": "ISO timestamp",
    "extraction_method": "string", // e.g., "hybrid_ocr_template"
    "notification_method": "in_app_and_email"
  }
  ```
- **Security**:
  - Extraction runs in isolated sandbox
  - No network access from extraction environment
  - Memory and time limits enforced
  - Output validated against document type schemas

#### get_extracted_document_data(document_id)
- **Purpose**: Retrieve extracted data from a processed document
- **Input**: document_id
- **Output**:
  ```json
  {
    "document_id": "uuid",
    "extraction_status": "completed|failed|needs_review",
    "extraction_confidence": number, // 0-1
    "verification_status": "unverified|partially_verified|verified|disputed",
    "extracted_fields": [
      {
        "field_id": "uuid",
        "field_name": "monthly_gross_salary",
        "field_category": "income",
        "extracted_value": "string",
        "parsed_value": number,
        "data_type": "currency",
        "confidence_score": number,
        "source_location": "string", // e.g., "Page 1, Table 2, Row 3"
        "extraction_method": "string",
        "verified_by_user": boolean,
        "user_corrected_value": number,
        "verification_timestamp": "ISO timestamp"
      }
    ],
    "document_info": {
      "original_filename": "string",
      "document_type": "string",
      "upload_timestamp": "ISO timestamp",
      "page_count": integer
    },
    "extraction_metadata": {
      "method_used": "string",
      "processing_time_ms": integer,
      "quality_metrics": {
        "text_clarity": number,
        "table_detection_accuracy": number
      }
    }
  }
  ```
- **Security**:
  - Only returns data that was successfully extracted and validated
  - Field names are standardized (not raw OCR text)
  - Confidence scores indicate reliability
  - No access to original document content through this tool

#### verify_extracted_field(document_id, field_id, verification_action, corrected_value=null)
- **Purpose**: Allow user to verify or correct extracted field data
- **Input**:
  - document_id: UUID
  - field_id: UUID
  - verification_action: "accept" | "reject" | "correct"
  - corrected_value: optional (required if action is "correct")
- **Output**:
  ```json
  {
    "document_id": "uuid",
    "field_id": "uuid",
    "field_name": "string",
    "previous_status": "unverified",
    "new_status": "verified|needs_correction",
    "verification_action": "string",
    "corrected_value": {
      "value": number,
      "data_type": "string",
      "provided_by_user": boolean
    },
    "verification_timestamp": "ISO timestamp",
    "impact_on_related_fields": [
      {
        "field_id": "uuid",
        "field_name": "string",
        "suggested_review": boolean
      }
    ],
    "extraction_confidence_updated": number
  }
  ```
- **Security**:
  - Validates field belongs to document and document belongs to user
  - Prevents incorrect data types
  - Logs all verification actions for audit trail
  - May suggest reviewing related fields if correction affects consistency

#### get_document_metadata(user_id, filters=null)
- **Purpose**: Get metadata about user's uploaded documents
- **Input**:
  - user_id
  - filters: optional object
    ```json
    {
      "document_type": "salary_slip|etc",
      "upload_date_after": "YYYY-MM-DD",
      "extraction_status": "pending|completed|etc",
      "verification_status": "unverified|verified|etc",
      "limit": integer,
      "offset": integer
    }
    ```
- **Output**:
  ```json
  {
    "documents": [
      {
        "document_id": "uuid",
        "original_filename": "string",
        "document_type": "string",
        "upload_timestamp": "ISO timestamp",
        "file_size": integer,
        "extraction_status": "string",
        "extraction_confidence": number,
        "verification_status": "string",
        "page_count": integer
      }
    ],
    "pagination": {
      "total_count": integer,
      "limit": integer,
      "offset": integer,
      "has_more": boolean
    },
    "summary": {
      "total_documents": integer,
      "by_type": {
        "salary_slip": integer,
        "form_16": integer,
        "bank_statement": integer
      },
      "by_extraction_status": {
        "pending": integer,
        "completed": integer,
        "failed": integer
      },
      "by_verification_status": {
        "unverified": integer,
        "verified": integer,
        "needs_review": integer
      }
    }
  }
  ```

### 6. Public Research Tools

These tools allow the agent to search for and retrieve public financial information while maintaining strict separation from private data.

#### search_public_financial_information(query, source_type=None, limit=10)
- **Purpose**: Search for publicly available financial information
- **Input**:
  - query: string (search query)
  - source_type: optional ("rbi" | "sebi" | "income_tax" | "bank" | "government_scheme" | "financial_news" | "educational")
  - limit: integer (default 10, max 50)
- **Output**:
  ```json
  {
    "query": "string",
    "source_type": "string|null",
    "results": [
      {
        "result_id": "uuid",
        "title": "string",
        "content_snippet": "string",
        "source": {
          "type": "rbi|sebi|income_tax|etc",
          "name": "string",
          "url": "string",
          "credibility_score": number // 0-1 based on source authority
        },
        "published_date": "ISO timestamp|null",
        "relevance_score": number, // 0-1
        "content_type": "regulation|notification|news|educational|etc"
      }
    ],
    "search_metadata": {
      "total_results_found": integer,
      "search_time_ms": integer,
      "sources_consulted": ["string"]
    },
    "disclaimer": "Information is for educational purposes only. Verify with official sources before making financial decisions."
  }
  ```
- **Security**:
  - Strictly prohibits accessing any private user data
  - Only connects to approved public information sources
  - Results are sanitized to prevent data leakage
  - Rate limited to prevent abuse
  - All sources are vetted for credibility

#### get_specific_public_information(information_type, identifiers=None)
- **Purpose**: Retrieve specific pieces of public financial information
- **Input**:
  - information_type: enum ["current_repo_rate", "current_reverse_repo_rate", "current_crr", "current_slr", "pf_interest_rate", "ppf_interest_rate", "nps_returns", "epf_interest_rate", "sukanya_samriddhi_rate", "income_tax_slabs", "section_80c_limit", "etc"]
  - identifiers: optional object for specific queries
    ```json
    {
      "bank_name": "string",
      "scheme_name": "string",
      "assessment_year": "YYYY-YY"
    }
    ```
- **Output**:
  ```json
  {
    "information_type": "string",
    "value": {
      // varies by type - could be number, string, object, array
      "example_for_rate": {
        "rate": number,
        "unit": "percentage",
        "as_of_date": "ISO timestamp",
        "effective_date": "ISO timestamp"
      },
      "example_for_slab": {
        "slabs": [
          {
            "min_income": number,
            "max_income": number,
            "rate": number
          }
        ],
        "currency": "INR",
        "assessment_year": "YYYY-YY"
      }
    },
    "source": {
      "type": "rbi|sebi|income_tax|etc",
      "name": "string",
      "url": "string",
      "retrieved_at": "ISO timestamp",
      "credibility_score": number
    },
    "disclaimer": "Rates and regulations are subject to change. Please verify with official sources."
  }
  ```
- **Security**:
  - Only returns pre-defined, vetted information types
  - No arbitrary data access or queries
  - Information is cached appropriately with freshness indicators
  - Source attribution and credibility scoring included

### 7. Financial Action and Guidance Tools

#### generate_action_plan(user_id, focus_areas=null)
- **Purpose**: Generate personalized financial action plan based on user's data
- **Input**:
  - user_id
  - focus_areas: optional array of strings
    ["emergency_fund", "debt_management", "insurance", "investment", "tax_planning", "goal_management"]
- **Output**:
  ```json
  {
    "user_id": "uuid",
    "generated_at": "ISO timestamp",
    "financial_health_snapshot": {
      "net_worth": {...},
      "savings_rate": number,
      "debt_to_income_ratio": number,
      "emergency_fund_months": number,
      "insurance adequacy": number // percentage
    },
    "priority_actions": [
      {
        "action_id": "uuid",
        "title": "string",
        "description": "string",
        "priority": "high|medium|low",
        "category": "emergency_fund|debt_management|etc",
        "reason": "string",
        "impact": "string", // description of expected impact
        "effort_level": "low|medium|high",
        "estimated_completion": "string", // e.g., "2-4 weeks"
        "source_metrics": {
          // which calculations/data points triggered this action
          "net_worth": number,
          "debt_to_income_ratio": number
        },
        "steps": [
          "Step 1: Description",
          "Step 2: Description"
        ],
        "resources": [
          {
            "type": "article|video|tool",
            "title": "string",
            "url": "string|null"
          }
        ],
        "prerequisites": ["string"] // e.g., ["Upload Form 16 for accurate tax planning"]
      }
    ],
    "long_term_recommendations": [
      {
        "area": "string",
        "recommendation": "string",
        "rationale": "string",
        "review_frequency": "string" // e.g., "quarterly", "annually"
      }
    ],
    "follow_up_suggested": "ISO timestamp" // when to revisit action plan
  }
  ```
- **Security**:
  - Only uses data accessible through authorized tools
  - Actions are based on calculations and summaries, not raw data
  - No action requires accessing sensitive data directly
  - Recommendations are general financial guidance, not specific product advice

#### get_financial_health_score(user_id)
- **Purpose**: Calculate and return a comprehensive financial health score
- **Input**: user_id
- **Output**:
  ```json
  {
    "user_id": "uuid",
    "calculated_at": "ISO timestamp",
    "overall_score": number, // 0-100
    "score_breakdown": [
      {
        "area": "emergency_fund",
        "score": number, // 0-100
        "weight": number, // percentage contribution to overall
        "metric": {
          "name": "emergency_fund_months",
          "value": number,
          "target": number,
          "unit": "months"
        },
        "interpretation": "string" // e.g., "Good - covers 4 months of expenses"
      },
      {
        "area": "savings_rate",
        "score": number,
        "weight": number,
        "metric": {
          "name": "monthly_savings_rate",
          "value": number,
          "target": number,
          "unit": "percentage"
        }
      }
      // ... other areas: debt_burden, insurance_readiness, investment_diversification, freedom_progress, goal_readiness
    ],
    "score_interpretation": {
      "range": "85-100",
      "label": "Excellent",
      "description": "Strong financial health across all areas"
    },
    "improvement_suggestions": [
      {
        "area": "string",
        "suggestion": "string",
        "impact_on_score": number // estimated points increase
      }
    ],
    "historical_trend": [
      {
        "date": "ISO timestamp",
        "score": number
      }
    ],
    "calculation_methodology": {
      "formula_version": "string",
      "last_updated": "ISO timestamp",
      "components": [
        {
          "area": "string",
          "data_sources": ["tool1", "tool2"],
          "calculation_tool": "specific_calculation_tool_name"
        }
      ]
    }
  }
  ```
- **Security**:
  - Score is derived from authorized tool outputs only
  - No raw data exposed in score calculation
  - Methodology is transparent and auditable
  - Historical tracking uses only score values, not underlying data

### 8. Authentication and Session Tools

These tools handle user authentication and session management (typically called by the frontend rather than the agent directly, but available for agent use in certain contexts).

#### verify_user_session(session_token)
- **Purpose**: Verify user session and return user context
- **Input**: session_token (string)
- **Output**:
  ```json
  {
    "valid": boolean,
    "user_id": "uuid|null",
    "expires_at": "ISO timestamp|null",
    "permissions": ["string"], // list of permission scopes
    "authentication_method": "password|mfa|sso|etc"
  }
  ```
- **Security**: Standard session validation

#### refresh_user_token(refresh_token)
- **Purpose**: Refresh expired access token
- **Input**: refresh_token
- **Output**: New access token pair or error
- **Security**: Standard token refresh with replay protection

## Tool Security and Validation Framework

### Input Validation
All tools implement strict input validation:
1. **Type Checking**: Ensures inputs are correct data types
2. **Range Validation**: Numerical values within reasonable bounds
3. **Format Validation**: Strings match expected patterns (email, dates, UUIDs)
4. **Length Limits**: Prevent excessive input sizes
5. **Whitelist Validation**: Enums restricted to allowed values
6. **SQL Injection Prevention**: Parameterized queries or ORM usage
7. **No Trust in Client Data**: All inputs treated as untrusted

### Output Sanitization
Tools ensure outputs don't leak sensitive information:
1. **Data Minimization**: Return only what's needed for the request
2. **Masking**: Sensitive identifiers masked in outputs
3. **Aggregation**: Financial data returned in aggregated form when appropriate
4. **Context Removal**: Strip metadata that could reveal sensitive patterns
5. **Size Limits**: Limit output sizes to prevent data exfiltration
6. **Structured Responses**: Well-defined schemas prevent unexpected data leakage

### Authorization Checks
Every tool verifies authorization:
1. **Authentication Validation**: Confirm user is authenticated
2. **Resource Ownership**: Verify user owns the resource being accessed
3. **Permission Scoping**: Check user has permission for specific operation
4. **Role-Based Access**: Enforce role restrictions where applicable
5. **Contextual Authorization**: Consider request context in authorization decisions
6. **Audit Logging**: Log all authorization decisions (success and failure)

### Rate Limiting and Abuse Prevention
Tools implement protection against abuse:
1. **Per-User Limits**: Restrict number of calls per time period
2. **Per-IP Limits**: Prevent IP-based abuse
3. **Expensive Operation Limits**: Restrict computationally intensive operations
4. **Concurrent Request Limits**: Limit simultaneous requests per user
5. **Circuit Breakers**: Temporarily block abusive patterns
6. **Challenge Responses**: CAPTCHA or similar for suspected abuse

### Audit and Logging
All tool interactions are logged for security and debugging:
1. **Access Logging**: Who accessed what tool when
2. **Input Logging**: Sanitized inputs (excluding sensitive data)
3. **Output Logging**: Whether tool returned success/failure (not output content)
4. **Performance Logging**: Execution time and resource usage
5. **Error Logging**: Detailed errors for debugging (secured logs)
6. **Security Event Logging**: Suspicious patterns or potential attacks

## Agent-Tool Interaction Patterns

### Sequential Processing
Most common pattern: gather data → calculate → explain
```javascript
// Example: Answering "What's my net worth and how can I improve it?"
const profile = await get_user_profile();
const income = await get_income_summary(user_id, startDate, endDate);
const expenses = await get_expense_summary(user_id, startDate, endDate);
const assets = await get_asset_summary(user_id);
const liabilities = await get_liability_summary(user_id);
const netWorth = await calculate_net_worth(user_id);
const actionPlan = await generate_action_plan(user_id, ["net_worth_improvement"]);
```

### Parallel Processing
When data is independent, fetch in parallel for efficiency:
```javascript
// Example: Getting comprehensive financial snapshot
const [profile, income, expenses, assets, liabilities, insurance] = await Promise.all([
  get_user_profile(),
  get_income_summary(user_id, monthStart, monthEnd),
  get_expense_summary(user_id, monthStart, monthEnd),
  get_asset_summary(user_id),
  get_liability_summary(user_id),
  get_insurance_summary(user_id)
]);
```

### Conditional Tool Use
Only call tools when needed based on previous results:
```javascript
// Example: Only check tax documents if user wants tax planning
const profile = await get_user_profile();
const wantsTaxPlanning = userQuery.includes("tax") || userQuery.includes("section 80c");
let taxInfo = null;
if (wantsTaxPlanning) {
  const documents = await get_document_metadata(user_id, { 
    document_type: "form_16", 
    verification_status: "verified" 
  });
  if (documents.total_count > 0) {
    taxInfo = await get_specific_public_information("income_tax_slabs");
  }
}
```

### Error Handling and Fallbacks
Graceful degradation when tools fail or return limited data:
```javascript
try {
  const netWorth = await calculate_net_worth(user_id);
  // Use net worth in response
} catch (error) {
  // Fallback to approximate calculation from summaries
  const assets = await get_asset_summary(user_id);
  const liabilities = await get_liability_summary(user_id);
  const approximateNetWorth = {
    amount: assets.total_asset_value.amount - liabilities.total_liability_outstanding.amount,
    currency: "INR"
  };
  // Indicate this is approximate in response
  // Suggest uploading documents for more accurate calculation
}
```

## Data Flow and Privacy Boundaries

### Private Data Flow
```
User Request → Agent → 
  [Authorized Tools (get_*_summary, calculate_*)] → 
  [Database/Calculation Engine (private data)] → 
  [Authorized Tools return aggregated/minimal data] → 
  Agent → 
  Response to User
```

Key points:
- Agent never sees raw private data
- Tools act as privacy filters
- Only aggregated or necessary data returns to agent
- Calculation engine isolated from direct agent access

### Public Data Flow
```
User Request → Agent → 
  [Public Research Tools (search_public_*, get_specific_*)] → 
  [Public Information Sources (RBI, SEBI, etc.)] → 
  [Tools return sanitized public information] → 
  Agent → 
  Response to User
```

Key points:
- Public research tools have NO access to private data stores
- Network isolation prevents data leakage
- Tools implement strict allowlists for sources and data types
- Agent combines public and private information only in final response

### Document Processing Flow
```
Upload → 
  [Quarantine Storage (encrypted)] → 
  [User Initiates Processing] → 
  [Sandboxed Extraction (no network, limited resources)] → 
  [Extraction Validation and Standardization] → 
  [Secure Storage of Extracted Data] → 
  [User Verification/Correction] → 
  [Authorized Tools access verified extracted data] → 
  Agent → 
  Response to User
```

Key points:
- Original documents never processed in environments with access to other system components
- Extraction happens in isolated sandbox
- Only standardized, validated extracted data enters main system
- User verification required before data used in financial model
- Original documents securely stored but not searchable/content accessible through main tools

## Implementation Considerations

### Tool Granularity
Tools should be:
- **Specific enough** to prevent over-fetching or unnecessary data access
- **General enough** to avoid proliferation of hyper-specific tools
- **Composable** to allow building complex responses from simple tools
- **Stable** in interface to prevent breaking agent logic

### Error Handling Design
Tools should return:
- **Consistent error format** that agent can parse
- **Actionable error messages** for users when appropriate
- **Distinction between** user errors (fixable) and system errors (try later)
- **Suggestions for resolution** when possible (e.g., "Please upload your Form 16 for accurate tax calculation")

### Performance Optimization
Consider:
- **Result caching** for expensive but infrequently changing data (profiles, preferences)
- **Prefetching** of commonly needed data based on conversation context
- **Batching** of related tool calls where beneficial
- **Async processing** for long-running operations (scenario analysis, document processing)

### Versioning and Evolution
Plan for:
- **Backward compatible** tool additions
- **Deprecation policies** for outdated tools
- **Versioning** of tool interfaces when breaking changes needed
- **Feature flags** for gradual rollout of new tool capabilities
- **Documentation** of tool behavior changes

## Testing Strategy for Tools

### Unit Testing
- Test each tool in isolation with mock dependencies
- Validate input validation rejects invalid inputs
- Verify outputs match expected schemas
- Test error conditions and edge cases
- Security testing for authorization bypass attempts

### Integration Testing
- Test tool chains that work together (e.g., get data → calculate → generate actions)
- Verify data flows correctly between tools
- Test authorization boundaries
- Performance testing for expected loads
- Security testing for cross-tool data leakage

### End-to-End Testing
- Simulate complete user conversations
- Verify agent correctly uses tools to fulfill requests
- Test privacy boundaries are maintained
- Verify security controls work as expected
- Test error handling and graceful degradation

### Security Testing
- Penetration testing focused on tool interfaces
- Authorization testing (attempting to access other users' data)
- Input validation testing (SQL injection, XSS attempts in tool inputs)
- Rate limiting and abuse prevention testing
- Audit logging verification

## Example Conversation Flows

### Flow 1: Basic Financial Overview
**User**: "Tell me about my current financial situation."

**Agent Process**:
1. Call `get_user_profile()` for basic info
2. Call `get_income_summary()` and `get_expense_summary()` for cash flow
3. Call `get_asset_summary()` and `get_liability_summary()` for net worth components
4. Call `calculate_net_worth()` for precise net worth
5. Synthesize response: "Based on your data as of [date], your net worth is ₹X. Your monthly income is ₹Y and expenses are ₹Z, giving you a savings rate of A%."
6. Offer to show more details or generate action plan

### Flow 2: Financial Freedom Planning
**User**: "I want to be financially free by age 45. How am I doing?"

**Agent Process**:
1. Get user profile to calculate current age
2. Get user's financial freedom target (if set) or use default assumptions
3. Call `calculate_freedom_number()` to get target corpus
4. Call `calculate_freedom_projection()` to get projected corpus at target age
5. Call `calculate_freedom_gap()` to get shortfall
6. If significant gap, call `generate_action_plan()` focused on wealth building
7. Explain: "To be financially free by 45, you need ₹X corpus. Based on your current trajectory, you're projected to have ₹Y, leaving a gap of ₹Z. Here are some steps to close this gap..."

### Flow 3: Document-Based Planning
**User**: "I uploaded my salary slip and Form 16. Can you help me plan my taxes?"

**Agent Process**:
1. Check document metadata for uploaded salary slip and Form 16
2. If not extracted, suggest initiating extraction and verification
3. If extracted and verified, use `get_extracted_document_data()` to get salary and tax deduction info
4. Call `get_specific_public_information()` for current tax slabs and Section 80c limits
5. Calculate current tax liability and potential savings
6. Generate tax-focused action plan using `generate_action_plan()` with tax planning focus
7. Explain findings and provide actionable tax planning suggestions

### Flow 4: What-If Scenario Analysis
**User**: "What if I increase my monthly SIP by ₹5,000? When could I retire then?"

**Agent Process**:
1. Get current financial state (income, expenses, assets, liabilities)
2. Get current freedom number and projection
3. Call `run_financial_scenario()` with additional monthly investment of ₹5,000
4. Compare base case vs. scenario case
5. Explain: "Increasing your SIP by ₹5,000/month would increase your projected corpus at age 60 from ₹X to ₹Y, potentially allowing you to reach financial freedom Z years earlier."
6. Provide caveats about assumptions and market risks

## Conclusion

The AI and tool architecture for Financial Freedom Copilot creates a secure, principled boundary between the conversational AI agent and the system's data and computational capabilities. By mediating all access through well-defined, secure tools that enforce least privilege, data minimization, and authorization checks, the architecture ensures that:

1. **The LLM never serves as a source of truth** for financial calculations or data
2. **Private user financial data remains protected** from unauthorized access or leakage
3. **Public information sourcing is isolated** from private data stores
4. **All actions are auditable and traceable** through tool invocation logs
5. **The system provides explainable, evidence-based guidance** rather than opaque AI-generated advice
6. **Users retain control** over their data through verification and consent mechanisms

This architecture supports the core product principles of privacy-first design, deterministic financial calculations, evidence-based guidance, and least privilege access while enabling a rich, helpful conversational experience for users seeking financial freedom.
