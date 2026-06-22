export interface Asset {
  type: string;
  name: string;
  description: string;
  animation?: string;
}

export interface Scene {
  id: string;
  type: string;
  duration: number; // in seconds
  headline?: string;
  subheadline?: string;
  animation?: string;
  assets?: Asset[];
  voiceover_segment?: string;
}

export interface Blueprint {
  version: string;
  title: string;
  duration: number; // in seconds
  aspect_ratio: string;
  voiceover?: string;
  scenes: Scene[];
}
