# Technology Stack: Current, Approved and Future

**Status:** Decision guide; only items marked current are implemented  
**Last reviewed:** 2026-08-30

## Current repository stack

- Python 3.14 development environment; FastAPI and SQLAlchemy backend
- PostgreSQL schema managed through Alembic
- React 18, TypeScript and Vite frontend
- Pydantic settings, JWT bearer authentication and Passlib password hashing
- Local encrypted document storage for development only
- Pytest security-boundary tests plus frontend TypeScript, ESLint and Vite checks

Redis, Elasticsearch, cloud object storage, managed identity, KMS, an external LLM,
containers and Kubernetes are **not current dependencies**. They remain options that
require an Architecture Decision Record before adoption. The UI uses the repository's
shared components; MUI and Ant Design are not approved defaults.

## Overview
This document outlines the recommended technology stack for building Financial Freedom Copilot (ArthaOS), focusing on security, scalability, maintainability, and suitability for financial applications.

## Backend Technologies

### Primary Language: Python 3.11+
**Rationale:**
- Excellent ecosystem for financial calculations (NumPy, Pandas, SciPy)
- Strong security libraries and frameworks
- Mature AI/ML integration capabilities (for document processing and NLP)
- Good performance for computational workloads
- Extensive testing frameworks
- Strong typing support with MyPy

### Web Framework: FastAPI
**Rationale:**
- High performance (async/await support)
- Automatic OpenAPI/Swagger documentation
- Built-in data validation with Pydantic
- Dependency injection system
- Excellent for microservices architecture
- Strong security features
- Easy testing capabilities

### Alternative: Django REST Framework
**Consider if:** More batteries-included approach preferred, excellent admin interface, but heavier than FastAPI.

## Frontend Technologies

### Framework: React 18+ with TypeScript
**Rationale:**
- Component-based architecture for maintainable UI
- Strong ecosystem for financial visualization libraries
- TypeScript ensures type safety throughout the stack
- Good performance and developer experience
- Extensive community support
- Easy integration with state management libraries

### State Management: React local state currently; Redux Toolkit or Zustand only if justified by an ADR
**Rationale:**
- Predictable state transitions
- Excellent debugging capabilities
- Middleware support for logging and persistence
- Scalable for complex financial applications

### UI Component Library: Existing ArthaOS shared components
**Rationale:**
- Professional, accessible components
- Theming capabilities for brand consistency
- Comprehensive documentation
- Good performance
- Internationalization support

### Data Visualization: Recharts or Victory (React-based) or D3.js (for custom visualizations)
**Rationale:**
- Declarative API that integrates well with React
- Good performance for financial charts
- Accessibility built-in
- Extensive chart types suitable for financial data
- Alternative: Chart.js with react-wrapper for simpler needs

## Database Technologies

### Primary Database: PostgreSQL 15+
**Rationale:**
- ACID compliance essential for financial data
- Strong security features (row-level security, encryption)
- Excellent performance and reliability
- JSONB support for flexible document storage
- Extensive extension ecosystem (PostGIS for geographic data if needed)
- Point-in-time recovery and logical replication
- Strong community and enterprise support

### Alternative: MySQL 8.0+
**Consider if:** Team has stronger MySQL expertise, but PostgreSQL generally preferred for financial applications due to advanced features and stronger adherence to SQL standards.

### Cache Layer: Redis 7+
**Rationale:**
- Fast in-memory caching for frequently accessed data
- Session storage
- Pub/sub capabilities for real-time updates
- Support for various data structures
- Persistence options available
- Excellent for reducing database load

### Search Engine: Elasticsearch or PostgreSQL Full-Text Search
**Rationale:**
- Full-text search capabilities for document content
- Financial document search and retrieval
- Analytics capabilities
- Alternative: Start with PostgreSQL FTS for simplicity, migrate to Elasticsearch if search becomes bottleneck

## Document Processing

### Storage: Amazon S3 (or compatible MinIO for self-hosted)
**Rationale:**
- Secure object storage with encryption at rest
- Fine-grained access control
- Versioning capabilities
- Lifecycle policies for cost optimization
- Integration with processing workflows
- Alternative: Azure Blob Storage or Google Cloud Storage based on cloud provider preference

### Processing Libraries:
- **PDF Processing:** PyPDF2/PyMuPDF or pdfplumber for text extraction, tabula-py for tables
- **Image Processing:** PIL/Pillow or OpenCV for image preprocessing
- **OCR:** Tesseract OCR or cloud-based solutions (AWS Textract, Google Vision) for scanned documents
- **Format Specific:** openpyxl for Excel, python-docx for Word documents

### Validation: Pydantic models for data validation post-extraction

## AI/ML Components

### Language Model Integration:
- **Primary:** Claude API (Anthropic) for conversational interface
- **Alternative:** Open-source LLMs (Llama 2, Mistral) for self-hosted options if data privacy requirements demand it
- **Rationale for Claude:** Strong reasoning capabilities, safety features, and good performance for financial planning tasks

### Document Intelligence:
- **Layout Analysis:** LayoutLM or Donut for understanding document structure
- **Named Entity Recognition:** spaCy or custom models for extracting financial entities
- **Classification:** Scikit-learn or TensorFlow/PyTorch for document type classification

### Embedding Models:
- Sentence-transformers for semantic search capabilities
- Alternative: OpenAI embeddings or Cohere if using their APIs

## Security Components

### Authentication: Auth0 or AWS Cognito or Custom OIDC
**Rationale:**
- Industry-standard authentication protocols
- Social login options if needed
- Multi-factor authentication support
- User management capabilities
- Alternative: Custom implementation using OAuth2/OIDC libraries (more work but full control)

### Authorization: Role-Based Access Control (RBAC) with Attribute-Based Access Control (ABAC) extensions
**Implementation:** Custom middleware checking permissions based on user roles and resource attributes

### Secrets Management: HashiCorp Vault or AWS Secrets Manager or Azure Key Vault
**Rationale:**
- Secure storage of API keys, database credentials, encryption keys
- Dynamic secret generation where applicable
- Audit logging of secret access
- Rotation capabilities

### Encryption:
- **At Rest:** AES-256 for database fields and file storage
- **In Transit:** TLS 1.3 for all communications
- **Key Management:** Cloud KMS or HashiCorp Vault for key lifecycle management

### Input Validation: Pydantic models combined with custom validation logic
**Rationale:**
- Declarative validation rules
- Automatic serialization/deserialization
- Custom validators for complex business rules
- Integration with FastAPI endpoints

### Rate Limiting: SlowAPI (for FastAPI) or Redis-based rate limiting
**Rationale:**
- Protect against brute force and DoS attacks
- Configurable limits per endpoint/user
- Distributed rate limiting for multi-instance deployments

## Infrastructure & DevOps

### Containerization: Docker
**Rationale:**
- Consistent development, testing, and production environments
- Microservices deployment flexibility
- Easy scaling and orchestration
- Standardized packaging

### Orchestration: Kubernetes (or Docker Compose for simpler deployments)
**Rationale:**
- Auto-scaling based on load
- Self-healing capabilities
- Service discovery and load balancing
- Rolling updates and rollbacks
- Alternative: Docker Swarm for simpler needs, or managed services (EKS, GKE, AKS)

### CI/CD: GitHub Actions or GitLab CI
**Rationale:**
- Automated testing on every commit
- Security scanning in pipeline
- Automated deployments to staging/production
- Environment promotion workflows
- Infrastructure as Code testing

### Infrastructure as Code: Terraform or AWS CDK or Pulumi
**Rationale:**
- Reproducible infrastructure deployments
- Version control for infrastructure
- Cross-cloud capabilities (Terraform)
- Policy as code for compliance monitoring

### Monitoring & Logging:
- **Metrics:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana) or Loki + Grafana
- **Tracing:** Jaeger or Zipkin for distributed tracing
- **Health Checks:** Custom endpoints combined with Kubernetes liveness/readiness probes
- **Error Tracking:** Sentry or similar service
- **Business Intelligence:** Metabase or Superset for internal analytics

## Testing Framework

### Backend Testing:
- **Unit Tests:** Pytest with coverage reporting
- **Integration Tests:** Pytest with test databases and mocks
- **Contract Testing:** Pact or similar for service-to-service contracts
- **Performance Testing:** Locust or k6 for load testing
- **Security Testing:** OWASP ZAP or similar for vulnerability scanning
- **Property-Based Testing:** Hypothesis for mathematical properties of financial calculations

### Frontend Testing:
- **Unit Tests:** Jest + React Testing Library
- **Integration Tests:** Cypress or Playwright
- **Visual Regression:** Storybook with Chromatic or Percy
- **Accessibility Testing:** Axe-core integration

## Financial Calculation Specifics

### Numerical Precision: Decimal type for all monetary calculations
**Implementation:** Python's decimal module with appropriate context settings
**Rationale:** Avoid floating-point precision errors in financial calculations

### Calculation Libraries:
- **Financial Functions:** numpy-financial or custom implementations
- **Statistical Analysis:** SciPy and NumPy
- **Date Handling:** Python's datetime with dateutil for complex calculations
- **Currency Handling:** money-python or similar for multi-currency support (if needed in future)

### Validation Approach:
- Property-based testing for mathematical identities
- Comparison against known-good implementations (Excel, financial calculators)
- Edge case testing (zero values, negative numbers, extreme values)
- Tolerance-based comparison for floating-point results where unavoidable

## Development Tools

### Code Quality:
- **Formatting:** Black (Python) and Prettier (JavaScript/TypeScript)
- **Linting:** Ruff or Flake8 (Python) and ESLint (JavaScript/TypeScript)
- **Type Checking:** MyPy (Python) and TypeScript compiler
- **Security Scanning:** Bandit (Python) and npm audit or similar (JavaScript/TypeScript)

### Dependency Management:
- **Python:** Poetry or Pipenv for dependency locking and virtual environments
- **JavaScript/TypeScript:** npm or Yarn with lockfiles
- **Pre-commit hooks:** For running checks before commits

### Documentation:
- **API Docs:** Automatic generation from FastAPI/OpenAPI
- **Technical Docs:** MkDocs or Sphinx for project documentation
- **Architecture Diagrams:** Mermaid or PlantUML for version-controlled diagrams

## Deployment Considerations

### Environment Strategy:
- **Development:** Local Docker Compose setup
- **Staging:** Production-like environment for testing
- **Production:** High-availability Kubernetes deployment

### Configuration Management:
- **Environment Variables:** For environment-specific configuration
- **Feature Flags:** LaunchDarkly or custom implementation for gradual rollouts
- **Centralized Config:** Consul or etcd for distributed systems (if needed)

### Backup & Disaster Recovery:
- **Database:** Regular logical dumps + point-in-time recovery setup
- **Object Storage:** Versioning and cross-region replication
- **Secrets:** Regular rotation and backup of master keys
- **Disaster Recovery Site:** Active-passive or active-active setup based on RTO/RPO requirements

## Third-Party Service Integrations

### Financial Data Aggregators (Future):
- Account Aggregator framework (India-specific)
- Bank APIs via UAE or similar protocols
- Mutual fund and stock exchange APIs
- Credit bureau APIs (with proper consent mechanisms)

### Communication:
- **Email:** SendGrid or Amazon SES or Mailgun
- **SMS:** Twilio or MSG91 or similar Indian providers
- **Push Notifications:** Firebase Cloud Messaging or Apple Push Notification Service
- **In-App Notifications:** Custom implementation or services like Courier

### Payments (Future, if needed):
- Razorpay or PayU or Stripe India
- UPI payment gateway integration
- NEFT/RTGS/IMPS capabilities

## Compliance and Localization

### Data Localization:
- Consider Indian data localization requirements for financial data
- Potential need for India-based data centers or specific compliance measures

### Regulatory Reporting:
- Architecture should support generation of required reports
- Audit trails compliant with financial regulations

### Language Support:
- UTF-8 throughout the stack
- Internationalization (i18n) framework for frontend
- Consideration for Hindi and other Indian languages in future

## Technology Stack Summary

| Layer | Technology | Choice Rationale |
|-------|------------|------------------|
| **Language** | Python 3.11+ | Financial ecosystem, security, AI integration |
| **Backend Framework** | FastAPI | Performance, async, automatic docs |
| **Frontend Framework** | React 18+ with TypeScript | Component-based, type-safe, ecosystem |
| **State Management** | Redux Toolkit/Zustand | Predictable state, debugging |
| **UI Library** | MUI/Ant Design | Professional components, theming |
| **Data Viz** | Recharts/Victory/D3.js | Financial charts, accessibility |
| **Database** | PostgreSQL 15+ | ACID, security, JSONB, reliability |
| **Cache** | Redis 7+ | Fast caching, sessions, pub/sub |
| **Object Storage** | AWS S3/MinIO | Secure, scalable, versioned |
| **Auth** | Auth0/Cognito/OIDC | Standardized, MFA, user management |
| **Secrets** | Vault/AWS Secrets Manager | Secure storage, rotation, audit |
| **Container** | Docker | Consistency, isolation, portability |
| **Orchestration** | Kubernetes | Scaling, self-healing, deployments |
| **CI/CD** | GitHub Actions | Automation, testing, security scanning |
| **Testing** | Pytest/Jest/Cypress | Comprehensive coverage |
| **Monitoring** | Prometheus/Grafana/ELK | Observability, alerting |
| **Tracing** | Jaeger/Zipkin | Distributed tracing |
| **Math Precision** | Python Decimal | Avoid floating-point errors |

This technology stack provides a solid foundation for building a secure, scalable, and maintainable Financial Freedom Copilot that meets the core principles of privacy, deterministic calculations, and evidence-based guidance.
