import { create } from "zustand";
import type { ExportSettings, ScenePlan, SceneStatus, TimelineScene } from "@/lib/types";

interface ProjectState {
  /* Auth */
  token: string;
  setToken: (t: string) => void;

  /* Current project */
  projectId: string;
  projectTitle: string;
  setProject: (id: string, title: string) => void;

  /* Scene plan */
  scenePlans: ScenePlan[];
  setScenePlans: (plans: ScenePlan[]) => void;

  /* Timeline scenes */
  scenes: TimelineScene[];
  setScenes: (s: TimelineScene[]) => void;
  updateScene: (id: string, patch: Partial<TimelineScene>) => void;
  removeScene: (id: string) => void;
  duplicateScene: (id: string) => void;
  reorderScenes: (from: number, to: number) => void;

  /* Selection */
  selectedSceneId: string | null;
  setSelectedSceneId: (id: string | null) => void;

  /* Preview */
  previewUrl: string | null;
  setPreviewUrl: (url: string | null) => void;

  /* Voiceover */
  voiceoverScript: string;
  setVoiceoverScript: (s: string) => void;
  voiceoverVoice: string;
  setVoiceoverVoice: (v: string) => void;
  voiceoverUrl: string | null;
  setVoiceoverUrl: (url: string | null) => void;

  /* Export */
  exportSettings: ExportSettings;
  setExportSettings: (s: Partial<ExportSettings>) => void;
  exportProgress: number;
  setExportProgress: (p: number) => void;

  /* Jobs */
  activeJobs: Record<string, { status: string; progress: number }>;
  setJobStatus: (jobId: string, status: string, progress: number) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  token: "",
  setToken: (t) => set({ token: t }),

  projectId: "",
  projectTitle: "",
  setProject: (id, title) => set({ projectId: id, projectTitle: title }),

  scenePlans: [],
  setScenePlans: (plans) => set({ scenePlans: plans }),

  scenes: [],
  setScenes: (s) => set({ scenes: s }),
  updateScene: (id, patch) =>
    set({ scenes: get().scenes.map((s) => (s.id === id ? { ...s, ...patch } : s)) }),
  removeScene: (id) =>
    set({ scenes: get().scenes.filter((s) => s.id !== id) }),
  duplicateScene: (id) => {
    const scene = get().scenes.find((s) => s.id === id);
    if (!scene) return;
    const dup = { ...scene, id: `${id}-dup-${Date.now()}` };
    const idx = get().scenes.findIndex((s) => s.id === id);
    const next = [...get().scenes];
    next.splice(idx + 1, 0, dup);
    set({ scenes: next });
  },
  reorderScenes: (from, to) => {
    const next = [...get().scenes];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    set({ scenes: next });
  },

  selectedSceneId: null,
  setSelectedSceneId: (id) => set({ selectedSceneId: id }),

  previewUrl: null,
  setPreviewUrl: (url) => set({ previewUrl: url }),

  voiceoverScript: "",
  setVoiceoverScript: (s) => set({ voiceoverScript: s }),
  voiceoverVoice: "Adam",
  setVoiceoverVoice: (v) => set({ voiceoverVoice: v }),
  voiceoverUrl: null,
  setVoiceoverUrl: (url) => set({ voiceoverUrl: url }),

  exportSettings: { resolution: "1080p", fps: 30, format: "mp4" },
  setExportSettings: (s) => set({ exportSettings: { ...get().exportSettings, ...s } }),
  exportProgress: 0,
  setExportProgress: (p) => set({ exportProgress: p }),

  activeJobs: {},
  setJobStatus: (jobId, status, progress) =>
    set({ activeJobs: { ...get().activeJobs, [jobId]: { status, progress } } }),
}));
