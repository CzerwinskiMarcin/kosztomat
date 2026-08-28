export interface ColumnMapping {
  booking_date: string | number;
  amount?: string | number | null;
  description?: string | number | null;
  amount_debit?: string | number | null;
  amount_credit?: string | number | null;
}

export interface SourceProfile {
  id: number;
  name: string;
  delimiter: string;
  encoding: string;
  has_header: boolean;
  skip_rows: number;
  decimal_separator: string;
  thousand_separator: string;
  date_format: string;
  amount_mode: 'signed' | 'absolute';
  column_mapping: ColumnMapping;
  created_at: string;
  updated_at: string;
}

export interface ProfilePayload {
  name: string;
  delimiter: string;
  encoding: string;
  has_header: boolean;
  skip_rows: number;
  decimal_separator: string;
  thousand_separator: string;
  date_format: string;
  amount_mode: 'signed' | 'absolute';
  column_mapping: ColumnMapping;
}

export interface SourceFile {
  id: number;
  display_name: string;
  original_filename: string;
  byte_size: number;
  checksum_sha256: string;
  profile_id: number | null;
  status: 'uploaded' | 'mapped' | 'imported' | 'failed';
  row_count: number;
  error_message: string | null;
  uploaded_at: string;
  imported_at: string | null;
  profile: SourceProfile | null;
  duplicate_of_file_id: number | null;
}

export interface Preview {
  encoding: string;
  delimiter: string;
  has_header: boolean;
  skip_rows: number;
  headers: string[];
  rows: string[][];
  row_count: number;
  detected_encoding: string;
  detected_delimiter: string;
}

export interface ImportErrorItem {
  row_index: number;
  message: string;
}

export interface ImportResult {
  file: SourceFile;
  errors: ImportErrorItem[];
}

export interface FileImportRequest {
  profile_id?: number | null;
  config?: ProfilePayload;
  save_as_profile?: { name: string } | null;
}

export interface TransactionRow {
  id: number;
  row_index: number;
  booking_date: string;
  amount: string;
  description: string | null;
  raw_payload: Record<string, string>;
}

export interface TransactionPage {
  items: TransactionRow[];
  total: number;
  offset: number;
  limit: number;
}

export interface ComparisonSummary {
  exact: number;
  probable: number;
  unmatched_a: number;
  unmatched_b: number;
  total_a: number;
  total_b: number;
}

export interface FileRef {
  id: number;
  display_name: string;
}

export interface Comparison {
  id: number;
  file_a: FileRef;
  file_b: FileRef;
  date_tolerance_days: number;
  created_at: string;
  summary: ComparisonSummary;
}

export interface MatchSide {
  id: number;
  booking_date: string;
  amount: string;
  description: string | null;
}

export interface MatchRow {
  id: number;
  kind: 'exact' | 'probable' | 'unmatched_a' | 'unmatched_b';
  confidence: number;
  date_delta_days: number | null;
  amount: string;
  a: MatchSide | null;
  b: MatchSide | null;
}

export type MatchKind = MatchRow['kind'];
