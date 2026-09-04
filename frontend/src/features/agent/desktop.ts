import { invoke } from '@tauri-apps/api/core';

export interface LocalDocumentSelection {
  selection_token: string;
  display_name: string;
  file_size_bytes: number;
}

export interface LocalDocumentCandidate {
  evidence_id: string;
  fact_type: string;
  value: string;
  unit: string;
  confidence: string;
  source_location: string;
  source_type: 'local_document_confirmation';
  period_start?: string;
  status?: 'candidate' | 'confirmed' | 'rejected';
}

export interface LocalProcessingResult {
  scan_status: 'clean';
  extractor_version: string;
  candidates: LocalDocumentCandidate[];
}

export interface SessionDocument {
  document_id: string;
  display_name: string;
  file_size_bytes: number;
  document_type: string;
  processed_at: string;
  candidates: LocalDocumentCandidate[];
}

export interface LocalDocumentCapabilities {
  available: boolean;
  platform: string;
  scanner_available: boolean;
  sandbox_available: boolean;
  pdf_text_available: boolean;
  limitations: string[];
}

export function isDesktopHost(): boolean {
  return '__TAURI_INTERNALS__' in window;
}

export function selectLocalDocument(): Promise<LocalDocumentSelection | null> {
  return invoke<LocalDocumentSelection | null>('select_local_document');
}

export function getLocalDocumentCapabilities(): Promise<LocalDocumentCapabilities> {
  return invoke<LocalDocumentCapabilities>('get_local_document_capabilities');
}

export function discardLocalDocumentSelection(selectionToken: string): Promise<void> {
  return invoke<void>('discard_local_document_selection', { selectionToken });
}

export function processLocalDocument(selectionToken: string, documentType: string): Promise<LocalProcessingResult> {
  return invoke<LocalProcessingResult>('process_local_document', {
    selectionToken,
    documentType,
  });
}
