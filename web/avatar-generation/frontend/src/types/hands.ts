export interface Landmark { x: number; y: number }
export type Hand = Landmark[] | null;
export interface HandFrame { timestampMs: number; leftHand: Hand; rightHand: Hand; pose?: (Landmark|null)[]|null; face?: (Landmark|null)[]|null }
export interface HandAnimation {
  schemaVersion: 1;
  signId: string;
  durationMs: number;
  frames: HandFrame[];
  metadata: {
    sourceWidth: number;
    sourceHeight: number;
    extractionVersion: string;
    sampleIntervalMs?: number;
    fixture?: boolean;
    [key: string]: unknown;
  };
}
export interface SignEntry {
  signId: string;
  label: string;
  aliases: string[];
  animationUrl: string;
  datasetReference: string;
  reviewed: boolean;
  sha256?: string;
}
export interface AnimationManifest { schemaVersion: 1; fixture: boolean; signs: SignEntry[] }
export interface SignSegment { startMs: number; endMs: number; signs: string[] }
export interface AgentResult { englishText: string; sinhalaText?: string; signs: string[]; segments?: SignSegment[] }
export interface VideoClock { currentTimeMs: number; playing: boolean }
