# Data Rights Workflow

**Status:** Required before production  
**Last reviewed:** 2026-08-30  
**Owner:** Privacy lead

1. Authenticate the requester without collecting unnecessary new identifiers.
2. Record request type: access, correction, update, erasure, consent withdrawal or grievance.
3. Locate primary, derived, processor, queue, cache and backup data using the data inventory.
4. Validate legal exceptions or holds with the privacy owner.
5. Execute the request with least-privilege service credentials.
6. Propagate the action to processors and integrations.
7. Verify completion and record evidence without copying sensitive content into the audit log.
8. Notify the requester in accessible language and provide grievance escalation.

No request is complete merely because the primary database row was removed. Backup
expiry and processor completion must be tracked separately.
