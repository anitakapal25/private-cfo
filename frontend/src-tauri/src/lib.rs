use regex::Regex;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Read;
use std::os::unix::fs::OpenOptionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::State;
use uuid::Uuid;

const MAX_DOCUMENT_BYTES: u64 = 10 * 1024 * 1024;
const MAX_TEXT_BYTES: u64 = 2 * 1024 * 1024;
const TOKEN_TTL: Duration = Duration::from_secs(10 * 60);

struct SelectedDocument {
    path: PathBuf,
    selected_at: Instant,
}

#[derive(Default)]
struct SelectionState(Mutex<HashMap<Uuid, SelectedDocument>>);

#[derive(Serialize)]
struct SelectedDocumentMetadata {
    selection_token: String,
    display_name: String,
    file_size_bytes: u64,
}

#[derive(Serialize, Debug, PartialEq)]
struct LocalCandidate {
    evidence_id: String,
    fact_type: String,
    value: String,
    unit: String,
    confidence: String,
    source_location: String,
    source_type: String,
}

#[derive(Serialize)]
struct LocalProcessingResult {
    scan_status: String,
    extractor_version: String,
    candidates: Vec<LocalCandidate>,
}

#[derive(Serialize)]
struct LocalDocumentCapabilities {
    available: bool,
    platform: String,
    scanner_available: bool,
    sandbox_available: bool,
    pdf_text_available: bool,
    limitations: Vec<String>,
}

struct TemporaryOutput(PathBuf);

impl Drop for TemporaryOutput {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn safe_error(message: &str) -> String {
    message.to_string()
}

fn local_document_capabilities() -> LocalDocumentCapabilities {
    let scanner_available = Path::new("/usr/bin/clamscan").is_file();
    let sandbox_available = Path::new("/usr/bin/bwrap").is_file()
        && Path::new("/usr/bin/timeout").is_file()
        && Path::new("/usr/bin/prlimit").is_file();
    let pdf_text_available = Path::new("/usr/bin/pdftotext").is_file();
    let mut limitations = Vec::new();
    if !scanner_available {
        limitations.push("ClamAV is unavailable; local documents cannot be scanned".to_string());
    }
    if !sandbox_available {
        limitations.push("The Linux extraction sandbox is unavailable".to_string());
    }
    if !pdf_text_available {
        limitations.push("PDF text extraction is unavailable".to_string());
    }
    limitations.push("PDF text documents only; OCR is not enabled".to_string());
    LocalDocumentCapabilities {
        available: scanner_available && sandbox_available && pdf_text_available,
        platform: std::env::consts::OS.to_string(),
        scanner_available,
        sandbox_available,
        pdf_text_available,
        limitations,
    }
}

fn validate_pdf(path: &Path) -> Result<u64, String> {
    let metadata =
        fs::metadata(path).map_err(|_| safe_error("Selected document is unavailable"))?;
    if !metadata.is_file() || metadata.len() == 0 || metadata.len() > MAX_DOCUMENT_BYTES {
        return Err(safe_error("Document is empty or exceeds the 10 MB limit"));
    }
    if path
        .extension()
        .and_then(|value| value.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
        != Some("pdf")
    {
        return Err(safe_error(
            "Only PDF documents are supported by the local extractor",
        ));
    }
    let mut signature = [0_u8; 5];
    fs::File::open(path)
        .and_then(|mut file| file.read_exact(&mut signature))
        .map_err(|_| safe_error("Document signature could not be validated"))?;
    if &signature != b"%PDF-" {
        return Err(safe_error("Document extension and signature do not match"));
    }
    Ok(metadata.len())
}

fn scan_document(path: &Path) -> Result<(), String> {
    let status = Command::new("/usr/bin/clamscan")
        .arg("--no-summary")
        .arg(path)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|_| safe_error("Local malware scanner is unavailable"))?;
    match status.code() {
        Some(0) => Ok(()),
        Some(1) => Err(safe_error("Document failed malware scanning")),
        _ => Err(safe_error("Local malware scanner failed closed")),
    }
}

fn extract_text(path: &Path) -> Result<String, String> {
    for required in [
        "/usr/bin/timeout",
        "/usr/bin/bwrap",
        "/usr/bin/prlimit",
        "/usr/bin/pdftotext",
    ] {
        if !Path::new(required).is_file() {
            return Err(safe_error(
                "Local sandboxed extraction tools are unavailable",
            ));
        }
    }
    let output_path = std::env::temp_dir().join(format!("private-cfo-{}.txt", Uuid::new_v4()));
    let output_guard = TemporaryOutput(output_path.clone());
    let output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&output_path)
        .map_err(|_| safe_error("Private extraction output could not be created"))?;
    let status = Command::new("/usr/bin/timeout")
        .args([
            "--signal=KILL",
            "20",
            "/usr/bin/bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
        ])
        .args([
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
        ])
        .args([
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--ro-bind",
        ])
        .arg(path)
        .args([
            "/document.pdf",
            "--setenv",
            "HOME",
            "/tmp",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
            "--",
            "/usr/bin/prlimit",
        ])
        .arg(format!("--as={}", 256 * 1024 * 1024))
        .args(["--cpu=10"])
        .arg(format!("--fsize={MAX_TEXT_BYTES}"))
        .args([
            "--nofile=64",
            "--",
            "/usr/bin/pdftotext",
            "-layout",
            "/document.pdf",
            "-",
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::from(output))
        .stderr(Stdio::null())
        .status()
        .map_err(|_| safe_error("Sandboxed document extraction could not start"))?;
    if !status.success() {
        return Err(safe_error("Sandboxed document extraction failed closed"));
    }
    if fs::metadata(&output_path)
        .map(|item| item.len())
        .unwrap_or(MAX_TEXT_BYTES + 1)
        > MAX_TEXT_BYTES
    {
        return Err(safe_error("Extracted text exceeded the safety limit"));
    }
    let text = fs::read_to_string(&output_path)
        .map_err(|_| safe_error("Extracted document text is not valid UTF-8"))?;
    drop(output_guard);
    Ok(text)
}

fn normalize_money(raw: &str) -> Option<String> {
    let compact = raw.replace(',', "");
    let mut parts = compact.split('.');
    let whole = parts.next()?;
    let fraction = parts.next();
    if parts.next().is_some()
        || whole.is_empty()
        || !whole.chars().all(|value| value.is_ascii_digit())
    {
        return None;
    }
    let fraction = match fraction {
        None => "00".to_string(),
        Some(value) if value.len() == 1 && value.chars().all(|item| item.is_ascii_digit()) => {
            format!("{value}0")
        }
        Some(value) if value.len() == 2 && value.chars().all(|item| item.is_ascii_digit()) => {
            value.to_string()
        }
        _ => return None,
    };
    Some(format!("{whole}.{fraction}"))
}

fn parse_candidates(document_type: &str, text: &str) -> Vec<LocalCandidate> {
    let (fact_type, pattern) = match document_type {
        "salary_slip" => (
            "monthly_income",
            r"(?im)^\s*(?:net\s+pay|net\s+salary|take[ -]?home\s+(?:pay|salary))\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$",
        ),
        "insurance_policy" => (
            "insurance_coverage",
            r"(?im)^\s*(?:sum\s+assured|coverage\s+amount)\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*$",
        ),
        _ => return Vec::new(),
    };
    let regex = match Regex::new(pattern) {
        Ok(value) => value,
        Err(_) => return Vec::new(),
    };
    let matches: Vec<_> = regex.captures_iter(text).collect();
    if matches.len() != 1 {
        return Vec::new();
    }
    let matched = &matches[0];
    let Some(value) = matched
        .get(1)
        .and_then(|item| normalize_money(item.as_str()))
    else {
        return Vec::new();
    };
    let line = text[..matched.get(0).map(|item| item.start()).unwrap_or(0)]
        .bytes()
        .filter(|value| *value == b'\n')
        .count()
        + 1;
    vec![LocalCandidate {
        evidence_id: Uuid::new_v4().to_string(),
        fact_type: fact_type.to_string(),
        value,
        unit: "INR".to_string(),
        confidence: "0.9000".to_string(),
        source_location: format!("local extracted text line {line}"),
        source_type: "local_document_confirmation".to_string(),
    }]
}

#[tauri::command]
fn select_local_document(
    state: State<'_, SelectionState>,
) -> Result<Option<SelectedDocumentMetadata>, String> {
    let Some(selected) = rfd::FileDialog::new()
        .add_filter("PDF document", &["pdf"])
        .pick_file()
    else {
        return Ok(None);
    };
    let canonical = selected
        .canonicalize()
        .map_err(|_| safe_error("Selected document is unavailable"))?;
    let size = validate_pdf(&canonical)?;
    let display_name = canonical
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("document.pdf")
        .to_string();
    let token = Uuid::new_v4();
    let mut selections = state
        .0
        .lock()
        .map_err(|_| safe_error("Local selection state is unavailable"))?;
    selections.retain(|_, item| item.selected_at.elapsed() < TOKEN_TTL);
    selections.insert(
        token,
        SelectedDocument {
            path: canonical,
            selected_at: Instant::now(),
        },
    );
    Ok(Some(SelectedDocumentMetadata {
        selection_token: token.to_string(),
        display_name,
        file_size_bytes: size,
    }))
}

#[tauri::command]
fn get_local_document_capabilities() -> LocalDocumentCapabilities {
    local_document_capabilities()
}

#[tauri::command]
fn discard_local_document_selection(
    selection_token: String,
    state: State<'_, SelectionState>,
) -> Result<(), String> {
    let token = Uuid::parse_str(&selection_token)
        .map_err(|_| safe_error("Local document selection is invalid or expired"))?;
    let mut selections = state
        .0
        .lock()
        .map_err(|_| safe_error("Local selection state is unavailable"))?;
    selections.remove(&token);
    Ok(())
}

#[tauri::command]
fn process_local_document(
    selection_token: String,
    document_type: String,
    state: State<'_, SelectionState>,
) -> Result<LocalProcessingResult, String> {
    let token = Uuid::parse_str(&selection_token)
        .map_err(|_| safe_error("Local document selection is invalid or expired"))?;
    let selected = {
        let mut selections = state
            .0
            .lock()
            .map_err(|_| safe_error("Local selection state is unavailable"))?;
        selections.retain(|_, item| item.selected_at.elapsed() < TOKEN_TTL);
        selections
            .remove(&token)
            .ok_or_else(|| safe_error("Local document selection is invalid or expired"))?
    };
    validate_pdf(&selected.path)?;
    scan_document(&selected.path)?;
    let text = extract_text(&selected.path)?;
    let candidates = parse_candidates(&document_type, &text);
    Ok(LocalProcessingResult {
        scan_status: "clean".to_string(),
        extractor_version: "desktop-local-pdf-v1".to_string(),
        candidates,
    })
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(SelectionState::default())
        .invoke_handler(tauri::generate_handler![
            get_local_document_capabilities,
            select_local_document,
            discard_local_document_selection,
            process_local_document
        ])
        .run(tauri::generate_context!())
        .expect("Private CFO desktop failed to start");
}

#[cfg(test)]
mod tests {
    use super::{
        extract_text, local_document_capabilities, normalize_money, parse_candidates,
        scan_document, validate_pdf,
    };
    use std::path::Path;

    #[test]
    fn money_normalization_uses_strings_not_floating_point() {
        assert_eq!(normalize_money("1,23,456.7").as_deref(), Some("123456.70"));
        assert_eq!(normalize_money("12.345"), None);
    }

    #[test]
    fn candidate_parser_requires_one_unambiguous_direct_label() {
        let values = parse_candidates("salary_slip", "Employee: Test\nNet Pay: INR 85,000.00\n");
        assert_eq!(values.len(), 1);
        assert_eq!(values[0].fact_type, "monthly_income");
        assert_eq!(values[0].value, "85000.00");
        assert!(parse_candidates("salary_slip", "Net Pay: 1\nNet Salary: 2").is_empty());
        assert!(parse_candidates("bank_statement", "Closing balance: 500").is_empty());
    }

    #[test]
    fn capability_report_is_non_sensitive_and_fails_closed() {
        let report = local_document_capabilities();
        assert_eq!(report.platform, std::env::consts::OS);
        assert_eq!(
            report.available,
            report.scanner_available && report.sandbox_available && report.pdf_text_available
        );
        assert!(report.limitations.iter().all(|item| !item.contains('/')));
    }

    #[test]
    #[ignore = "requires ClamAV, bubblewrap, pdftotext and the local public PDF fixture"]
    fn installed_local_pipeline_scans_and_extracts_without_uploading() {
        let fixture = Path::new("/usr/share/doc/printer-driver-foo2zjs/manual.pdf");
        assert!(validate_pdf(fixture).is_ok());
        assert!(scan_document(fixture).is_ok());
        let text = extract_text(fixture).expect("sandboxed text extraction should succeed");
        assert!(!text.is_empty());
    }
}
