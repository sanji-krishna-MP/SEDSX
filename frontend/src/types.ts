export interface MetricDetail {
  id?: number;
  metric_code: string; // P1..P9, C1..C11
  name: string;
  stage: 'preprocessing' | 'comparison';
  image_role: 'source' | 'reference' | 'pair';
  raw_value: number | null;
  raw_unit: string;
  display_index: number | null;
  index_label: string;
  formula_id: string;
  formula_text: string;
  substituted_inputs: Record<string, any>;
  numerator?: number | null;
  denominator?: number | null;
  availability: boolean;
  unavailable_reason?: string | null;
  provenance: string;
  extra_data?: Record<string, any> | null;
}

export interface MatchPoint {
  id?: number;
  match_index: number;
  source_x: number;
  source_y: number;
  ref_x: number;
  ref_y: number;
  pred_ref_x?: number | null;
  pred_ref_y?: number | null;
  distance: number;
  ambiguity_ratio: number;
  is_inlier: boolean;
  residual?: number | null;
  rejection_reason?: string | null;
}

export interface CheckpointRecord {
  id?: number;
  checkpoint_id?: string;
  source_x: number;
  source_y: number;
  ref_x: number;
  ref_y: number;
  pred_ref_x?: number | null;
  pred_ref_y?: number | null;
  residual?: number | null;
}

export interface RunSummary {
  id: string;
  created_at: string;
  status: 'queued' | 'validating' | 'preprocessing' | 'matching' | 'fitting' | 'registering' | 'evaluating' | 'saving' | 'completed' | 'inconclusive' | 'failed' | 'cancelled';
  stage_message: string;
  timing_ms: Record<string, number>;
  source_filename: string;
  reference_filename: string;
  source_dims?: [number, number] | null;
  ref_dims?: [number, number] | null;
  modes: string[];
  warnings: string[];
  inlier_count?: number | null;
  candidate_count?: number | null;
  median_residual?: number | null;
  overlap_bbox?: [number, number, number, number] | null;
  affine_params?: Record<string, any> | null;
  failure_reason?: string | null;
  config: Record<string, any>;
}

export interface RunFullData {
  run: RunSummary;
  assets: Record<string, string>;
  metrics: MetricDetail[];
  matches?: MatchPoint[];
  checkpoints?: CheckpointRecord[];
}

export interface ExtractedMetadata {
  product_id?: string | null;
  instrument_id?: string | null;
  acquisition_time?: string | null;
  image_filename?: string | null;
  width?: number | null;
  height?: number | null;
  pixel_data_type?: string | null;
  resolution?: string | null;
}

export type MetadataStatus =
  | 'idle'
  | 'Processing Metadata'
  | 'Upload Successful'
  | 'Metadata Matched'
  | 'Metadata Mismatch'
  | 'Invalid Metadata';

export interface MetadataParseResult {
  status: MetadataStatus;
  status_label: string;
  checks?: {
    matches?: string[];
    mismatches?: string[];
    has_image?: boolean;
  };
  metadata: ExtractedMetadata;
  format?: string;
  filename: string;
  size_bytes: number;
  raw_fields?: Record<string, any>;
  normalized_metadata?: Record<string, any>;
}

