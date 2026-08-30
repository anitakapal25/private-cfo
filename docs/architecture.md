# Financial Freedom Copilot - Architecture

**Status:** Agent-first target architecture with partial implementation  
**Last reviewed:** 2026-08-30  
**Implementation status:** See [documentation index](README.md). Migrations and code are authoritative when this document differs from the repository.

## Overview
Financial Freedom Copilot (ArthaOS) is a private financial-freedom operating system designed for Indian salaried employees. The system helps users understand their current financial position, set goals, simulate scenarios, and track progress toward financial freedom.

## Core Architectural Principles

### 1. Privacy-First Architecture
- Strict separation between private user financial data and public financial information
- No unrestricted access for web search agents to private data
- Data minimization - only expose necessary data to AI agent
- Encryption at rest and in transit for all sensitive data

### 2. Deterministic Financial Engine
- All financial calculations performed by validated deterministic code
- LLM never serves as source of truth for calculations
- Clear exposure of assumptions in all calculations
- Modular calculation engine with comprehensive test coverage

### 3. Evidence-Based Information
- Claims about financial policies, regulations, and market data must be traceable to authoritative sources
- Preference for primary sources (RBI, SEBI, Income Tax Department, etc.)
- Source metadata retained wherever practical
- Clear separation between user-specific advice and general financial education

### 4. Least Privilege Access
- AI agent interacts with system through explicit, limited tools
- No direct database access from LLM
- Tool-based interface for all operations
- Fine-grained permissions for different data types

### 5. Modular Monolith
- Single deployable unit for MVP to reduce complexity
- Clear module boundaries with well-defined interfaces
- Easy to decompose into microservices later if needed
- Shared kernel for cross-cutting concerns (auth, logging, etc.)

## System Components

### 1. User Interface Layer
- Web application (React/Vue) or mobile app
- Conversational interface as primary interaction method
- Dashboard for visualizing financial health and progress
- Document upload and management interface

### 2. API Gateway
- RESTful API for client-server communication
- Authentication and authorization middleware
- Rate limiting and input validation
- Request/response logging and monitoring

### 3. Core Services
- **Financial Agent Service**: Main AI agent orchestrating user interactions
- **Calculation Engine**: Deterministic financial calculations
- **Data Service**: Secure access to user financial data
- **Document Processing Service**: Secure handling of uploaded financial documents
- **Research Service**: Evidence-grounded public information retrieval
- **Goal & Action Service**: Financial goal tracking and action item generation

### 4. Data Layer
- Encrypted database for user financial data
- Secure document storage (encrypted at rest)
- Cache layer for frequently accessed non-sensitive data
- Audit log storage

### 5. Infrastructure
- Containerized deployment (Docker/Kubernetes)
- CI/CD pipeline for automated testing and deployment
- Monitoring and alerting system
- Backup and disaster recovery procedures

## Data Flow

### User Interaction Flow
1. User interacts through conversational interface
2. Financial Agent interprets intent and determines required actions
3. Agent uses appropriate tools to:
   - Retrieve user financial data (through Data Service)
   - Perform calculations (through Calculation Engine)
   - Research public information (through Research Service)
   - Process documents (through Document Processing Service)
4. Agent formulates response with explanations, visualizations, and action items
5. Response delivered to user through interface

### Document Processing Flow
1. User uploads financial document
2. Document stored in encrypted quarantine area
3. Document Processing Service extracts data in sandboxed environment
4. Extracted data validated and verified
5. Validated data merged into user financial model (with user confirmation)
6. Original document securely stored, extractable data indexed

## Security Boundaries

### Trust Boundary 1: User Interface ↔ API Gateway
- TLS encryption
- Authentication tokens
- Input validation and sanitization

### Trust Boundary 2: API Gateway ↔ Core Services
- Service-to-service authentication
- API authorization based on user permissions
- Request logging and monitoring

### Trust Boundary 3: Core Services ↔ Data Layer
- Database connection pooling with encrypted credentials
- Query parameterization to prevent SQL injection
- Column-level encryption for sensitive fields
- Read replicas for non-sensitive analytics

### Trust Boundary 4: Core Services ↔ External Systems
- Public research service isolated from private data
- API keys stored in secure secrets manager
- Outbound traffic restricted and monitored
- No inbound connections from external systems to private data stores

## Technology Stack Rationale

See [technology-stack.md](./technology-stack.md) for detailed recommendations.

## Deployment Architecture

### Development Environment
- Local development with Docker Compose
- Feature flags for gradual rollout
- Automated testing in CI pipeline
- Code quality gates

### Staging Environment
- Production-like infrastructure
- Performance and security testing
- User acceptance testing
- Blue-green deployment capability

### Production Environment
- High availability setup
- Auto-scaling based on load
- Geographic distribution for disaster recovery
- Comprehensive monitoring and logging
- Regular security assessments

## Scalability Considerations

### Horizontal Scaling
- Stateless services behind load balancers
- Database read replicas for scaling reads
- Sharding strategy for user data (tenant-based)
- Caching layer for expensive computations

### Vertical Scaling
- Resource optimization for calculation-intensive operations
- Database connection pooling
- Efficient document processing pipelines
- Memory management for AI model inference

## Extensibility Points

### Plugin Architecture
- Well-defined interfaces for adding new calculation modules
- Extension points for new document types
- Customizable action templates
- Configurable financial rules engine

### Integration Points
- API endpoints for third-party financial aggregators
- Webhook support for external triggers
- Export interfaces for data portability
- Import capabilities for legacy financial data

## Monitoring and Observability

### Metrics Collection
- Business metrics (user engagement, goal completion rates)
- Performance metrics (response times, throughput)
- Infrastructure metrics (CPU, memory, disk, network)
- Financial accuracy metrics (calculation validation results)

### Logging Strategy
- Structured logging for easy parsing
- Audit trails for all financial data access
- Error tracking with context preservation
- Performance profiling capabilities

### Health Checks
- Liveness and readiness probes for all services
- Dependency health checks (database, external APIs)
- Business rule validation checks
- Data consistency verification

## Failure Handling and Resilience

### Graceful Degradation
- Non-essential features disabled during high load
- Cached responses for frequently requested calculations
- Manual override for automated processes
- Clear error messaging to users

### Data Protection
- Regular automated backups
- Point-in-time recovery capabilities
- Cross-region replication for critical data
- Immutable audit logs for compliance

### Incident Response
- Automated alerts for anomalous behavior
- Runbooks for common failure scenarios
- Forensic data preservation capabilities
- Regular disaster recovery testing

## Future Evolution Path

### Phase 1: Agent MVP (Implemented — release-gated)
- Authenticated v1 conversations persist messages, agent runs, deterministic calculation records, tool-call evidence, short-lived payload-bound confirmations and sanitized audit events.
- The React entry point is a chat-first host with email/password sign-in, structured scenario confirmation, and missing-data, refusal and calculation-evidence states. Real-browser validation remains pending.
- Net-worth, recurring cash-flow and user-confirmed financial-freedom scenarios use versioned Decimal-based deterministic orchestration. The projection never invents return, inflation or withdrawal assumptions.
- Intent routing is deterministic and tools are restricted by an explicit intent-scoped allow-list. A provider-neutral model boundary exists but remains disabled until privacy review and the model-release evaluation gate pass.
- Existing financial-freedom targets remain available as stored goals; action-plan mutation and proactive review generation belong to later milestones.
- Privacy-first design with deterministic calculation engine
- Audit coverage outside the v1 agent flow remains planned.
- Backend tests and the frontend type-check, lint and production build pass locally. PostgreSQL deployment verification and operational controls remain release gates.

### Phase 2: Enhanced Features (Current Focus)
- **Milestone 2 verified financial memory — Implemented:** Authenticated users create candidate facts with provenance, observation time, confidence and sensitivity classification. Candidates never enter calculation context before explicit confirmation; conflicting confirmed values are superseded only by a separate confirm decision. Purpose-scoped context packets return only required verified fields and missing-field labels.
- **Milestone 3 deterministic financial foundation — Implemented:** Versioned Decimal services cover net worth, monthly surplus and savings rate, emergency-reserve coverage, debt metrics, goal progress/projection and financial-freedom projections. Calculation records persist normalized inputs, fact provenance, assumptions, rule versions, as-of time, results and limitations. Current tax calculations remain fail-closed because their assumption catalogue is expired; this is a safety outcome, not an incomplete arithmetic path.
- **Scenario planning — Partial**: Confirmed financial-freedom scenarios are deterministic and versioned. The legacy Monte Carlo implementation remains outside the v1 agent because it uses floating-point calculations and unreviewed embedded assumptions.
- **Insurance planning — Partial**: The agent compares stored coverage with an explicit user-selected target. It does not select a coverage level or recommend a product.
- **Tax optimization — Blocked**: The reviewed tax catalogue is expired; tax requests fail closed until current authoritative rules complete the calculation-release workflow.
- **Investment analysis — Blocked at advice boundary**: Stored assets contribute to net worth, but personalized allocation, rebalancing and product guidance require separate regulatory review.
- **Document processing — Blocked**: Malware scanning and sandboxed extraction are absent, so the v1 agent does not invoke the simulated document tools.
- **Goal-based planning — Partial**: Active goal progress is calculated deterministically. Priority funding and confirmed action-plan mutation remain pending.
- **Cash-flow forecasting — Implemented**: A versioned 12-month flat recurring scenario exposes the no-growth and one-time-item exclusions.
- **Debt analysis — Partial**: Outstanding debt, monthly EMI and debt-to-income ratio are implemented. Amortization and prepayment comparisons remain pending.

### Phase 3: Ecosystem Integration
- **Release gating — Implemented:** Phase 3 routers are absent by default and an authenticated capability endpoint reports non-sensitive status. Financial integrations require configured provider and approval references before startup.
- **Advisor access — Blocked:** Legacy consent routes require role verification, scoped consent, expiry and complete access auditing before enablement.
- **Account Aggregator — Blocked:** Existing simulated records are not an RBI-regulated integration. An approved provider, real consent protocol and specialist review are required.
- **Investment-platform import — Blocked:** Provider contracts, real read-only APIs, credential lifecycle controls and reconciliation tests are absent.
- **Community benchmarks — Blocked:** Cohort thresholds and re-identification controls are not implemented.
- **Employer wellness — Blocked:** Tenant isolation and employer/employee data-boundary evidence are incomplete.
- **External webhooks — Blocked:** SSRF-safe destinations, signing, replay defense and redacted delivery are incomplete.
- **Tax and loan exports — Blocked:** Confirmation, minimization, encrypted short-lived artifacts and deletion coverage are incomplete.

The release procedure and evidence requirements are defined in [the ecosystem integration workflow](workflows/ecosystem-release.md). No Phase 3 provider integration is represented as complete or production-ready.

### Phase 4: Intelligence Enhancement
- Predictive financial modeling using machine learning for income/expense forecasting
- Anomaly detection in spending patterns to identify unusual transactions or subscription creep
- Personalized financial education content based on user knowledge gaps and behavior
- Behavioral nudges and habit formation tools for improved financial discipline
- Natural language improvements for complex multi-step financial planning conversations
- Integration with external economic indicators for context-aware advice
