export type ActiveRegion = {
  rank: number;
  probability: number;
  heatmap_score?: number | null;
  image_path?: string | null;
  bbox_original?: number[] | null;
};

export type Heatmap = {
  method_name: string;
  image_path: string;
};

export type Prediction = {
  prediction_id: string;
  timestamp: string;
  date: string;
  prediction_hour: string;
  global_flare_probability: number;
  localized_probabilities: number[];
  predicted_class: string;
  jp2_image_url?: string | null;
  full_disk_image_url?: string | null;
  active_regions: ActiveRegion[];
  heatmaps: Heatmap[];
  raw_active_regions: Record<string, unknown>[];
};

export type JobResponse = {
  status: "queued" | "job_exists" | "prediction_exists" | string;
  prediction_id?: string | null;
  prediction_hour: string;
  job_id?: string;
  job_status?: string;
  created_at?: string;
  payload?: {
    helioviewer_date?: string;
    [key: string]: unknown;
  };
};

export type QueuedRangeJob = {
  job_id: string;
  prediction_hour: string;
};

export type JobRangeResponse = {
  status: "queued" | "already_covered" | string;
  start_prediction_hour: string;
  end_prediction_hour: string;
  total_hours: number;
  queued_count: number;
  prediction_exists_count: number;
  job_exists_count: number;
  returned_jobs_count: number;
  queued_jobs: QueuedRangeJob[];
};

export type JobStatusResponse = {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  created_at: string;
  prediction_hour?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  prediction_id?: string | null;
  error_message?: string | null;
  payload: {
    helioviewer_date?: string;
    [key: string]: unknown;
  };
};
