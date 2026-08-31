# Local Document Review Workflow

**Status:** Linux MVP implemented and tested; production distribution remains gated

**Last reviewed:** 2026-08-30

**Owner:** Security and document-platform leads

Private CFO does not upload or retain a user's original financial document. Document
review is a desktop-only capability:

```text
Native desktop file picker
  → canonical path retained in native memory behind a one-time opaque token
  → PDF size, extension and signature validation
  → local ClamAV scan (fail closed)
  → local bubblewrap sandbox with no network
  → bounded pdftotext extraction into a private temporary file
  → deterministic candidate parsing in native memory
  → temporary plaintext deletion
  → local candidate review
  → explicit user confirmation
  → confirmed structured fact plus opaque evidence UUID sent to backend
```

The React webview receives the display filename and size, not the filesystem path. It
never receives raw extracted text. The native selection token expires after ten minutes
and is consumed once. The original document remains unchanged on the user's system.
Temporary extraction output is created with owner-only permissions and removed on both
success and failure.

Version 1 accepts PDF files up to 10 MB. It recognizes only an unambiguous net-pay label
on a salary slip or sum-assured label on an insurance policy. Money remains a decimal
string. Bank statements, Form 16, EPF statements, ambiguous labels and image-only PDFs
produce no inferred financial fact. OCR is not enabled.

ClamAV, bubblewrap and pdftotext run from fixed system paths. Scanning or extraction
failure stops processing. The extraction process has isolated namespaces, no network,
a read-only tool filesystem, CPU/address-space/output/file-descriptor limits and a wall
timeout. Native unit tests and an opt-in installed-tool integration test exercise this
boundary.

Confirmation is still a user assertion: the backend cannot independently re-check a
document it never receives. It stores only the structured value, type, confidence,
`local_document_confirmation` source type and a UUID evidence reference. Rejection
sends nothing. Contradictory verified facts remain unresolved until the normal explicit
financial-memory decision completes.

The previous server upload, encrypted storage and extraction implementation remains
legacy internal code for migration history and isolated tests. Its API routes and the
mocked legacy agent router are not mounted, and upload settings are absent from the
runtime configuration. The browser contract test also fails if any document request is
attempted.

The Debian package declares bubblewrap, ClamAV and Poppler as required dependencies.
CI builds the package, and the desktop reports missing prerequisites before permitting
selection. ClamAV signature updates remain the host package manager's responsibility.

The Linux MVP acceptance criteria are implemented in code. Production distribution is
still prohibited until the generated package is signed with an organization-controlled
key and an independent desktop security/incident-response review is approved. Those are
external release decisions and cannot be represented by source code or self-attestation.

On Linux, `npm run tauri dev` clears inherited Snap GTK/GIO loader variables before
starting the native process. This prevents a Snap-hosted IDE from mixing its bundled
`core20` libraries with the host glibc. It does not alter the application environment,
document permissions or extraction sandbox.
