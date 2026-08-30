# Document Ingestion Workflow

**Status:** Partially implemented; malware scanning and sandboxing are release blockers  
**Last reviewed:** 2026-08-30  
**Owner:** Security and document-platform leads

```text
Authenticated upload
  → ownership binding and quota check
  → quarantine
  → size, signature and type validation
  → malware scan
  → encryption with managed key
  → sandboxed extraction
  → confidence and anomaly checks
  → user verification
  → approved financial-data update
  → retention or verified deletion
```

Documents must never be parsed directly in the API process, sent wholesale to an LLM,
served from a public path or marked encrypted unless the stored bytes are encrypted.
Failure after file creation must remove or quarantine the orphan safely.
