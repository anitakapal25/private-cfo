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

### Phase 1: Agent MVP (Partial — not production-ready)
- Authenticated v1 conversations persist messages, agent runs, deterministic calculation records, tool-call evidence, short-lived payload-bound confirmations and sanitized audit events.
- The React entry point is a chat-first host that renders missing-data, refusal and calculation-evidence states; production sign-in and browser validation remain planned.
- Net-worth and recurring cash-flow intents use Decimal-based deterministic orchestration. A full financial-freedom projection still requires verified target and approved assumption inputs.
- Document upload is encrypted locally; extraction is simulated and malware scanning is not implemented.
- Intent routing is deterministic and tools are restricted by an explicit intent-scoped allow-list. A provider-neutral model boundary exists but remains disabled until privacy review and the model-release evaluation gate pass.
- Goal setting and tracking (financial freedom targets)
- Privacy-first design with deterministic calculation engine
- Audit coverage outside the v1 agent flow remains planned.
- Backend and frontend prototypes build locally; production deployment and operational controls are planned.

### Phase 2: Enhanced Features (Current Focus)
- **Advanced Scenario Simulation**: Monte Carlo simulations for market volatility, income variability, and expense fluctuations
- **Insurance Planning Module**: Life, health, and property insurance needs analysis with coverage gap detection
- **Tax Optimization Strategies**: Indian tax regime comparison (old vs new), deduction maximization, and tax-loss harvesting suggestions
- **Investment Portfolio Analysis**: Asset allocation optimization, risk profiling, rebalancing recommendations, and goal-based investing
- **Enhanced Document Processing**: Expanded support for Form 16, investment statements, loan agreements, and property documents
- **Goal-Based Planning**: Multiple financial goal tracking (emergency fund, home purchase, education, retirement) with priority-based funding
- **Cash Flow Forecasting**: 12-month forward-looking cash flow projections with scenario planning
- **Debt Management Tools**: Loan amortization schedules, prepayment impact analysis, and debt snowball/avalanche strategies

### Phase 3: Ecosystem Integration
- API for financial advisors to securely access client portfolios (with consent)
- Direct integration with banking platforms via Account Aggregator framework (RBI-regulated)
- Integration with investment platforms (mutual funds, stocks) for portfolio import
- Community features (anonymized benchmarks against similar demographic profiles)
- Employer-sponsored financial wellness programs with custom branding
- API webhooks for triggering actions based on life events or market conditions
- Export capabilities for tax filing and loan application documents

### Phase 4: Intelligence Enhancement
- Predictive financial modeling using machine learning for income/expense forecasting
- Anomaly detection in spending patterns to identify unusual transactions or subscription creep
- Personalized financial education content based on user knowledge gaps and behavior
- Behavioral nudges and habit formation tools for improved financial discipline
- Natural language improvements for complex multi-step financial planning conversations
- Integration with external economic indicators for context-aware advice
