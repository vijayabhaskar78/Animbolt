export type StylePreset = { id: string; display_name: string; description: string };

export type TokenResponse = { access_token: string; refresh_token: string; token_type: string };

export type Project = { id: string; title: string; description: string; created_at: string };

export type SceneVersion = {
  id: string;
  scene_id: string;
  version_no: number;
  prompt: string;
  manim_code: string;
  validation_status: string;
  error_log: string;
  style_preset: string;
  max_duration_sec: number;
  aspect_ratio: string;
  created_at: string;
};

export type Scene = {
  id: string;
  title: string;
  order_index: number;
  created_at: string;
  versions: SceneVersion[];
  thumbnail_path: string | null;
  video_preview_path: string | null;
};

export type ProjectDetail = Project & { scenes: Scene[] };

export type QueueJobResponse = { job_id: string; status: string };

export type Asset = {
  id: string;
  asset_type: string;
  mime_type: string;
  storage_path: string;
  duration_ms: number;
  checksum_sha256: string;
};

export type Job = {
  id: string;
  job_type: string;
  status: string;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string;
  metrics: Record<string, unknown>;
  assets: Asset[];
};

export type UsageEntry = { used: number; limit: number };

export type UsageSummary = {
  preview_renders: UsageEntry;
  hd_renders: UsageEntry;
  exports: UsageEntry;
  tts_generations: UsageEntry;
  voiceover_uploads: UsageEntry;
  reset: string;
};

/* AnimBolt-specific types */
export type ScenePlan = { scene: number; description: string };

export type SceneStatus = "idle" | "generating_code" | "rendering_video" | "complete" | "error";

export type TimelineScene = {
  id: string;
  sceneNumber: number;
  description: string;
  duration: number;
  videoUrl: string | null;
  thumbnailUrl: string | null;
  prompt: string;
  manimCode: string;
  status: SceneStatus;
  progress: number;
};

export type VoiceOption = { id: string; name: string };

export type ExportSettings = {
  resolution: "720p" | "1080p" | "4K";
  fps: 30 | 60;
  format: "mp4";
};
