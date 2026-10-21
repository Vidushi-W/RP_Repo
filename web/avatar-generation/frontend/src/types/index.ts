export type AnimationStatus = 'available' | 'processing' | 'unavailable';
export interface VocabularyEntry {
  id: string; word: string; datasetReference: string; sourceVideo: string;
  animationStatus: AnimationStatus; animationUrl?: string; clipName?: string; validated: boolean;
}
export interface Cue { id: string; wordId: string; label: string; start: number; end: number }
export interface Manifest { title: string; demonstration: boolean; videoUrl: string | null; avatarUrl: string | null; cues: Cue[] }
export interface Preferences { avatarSize: 'small' | 'medium' | 'large'; avatarVisible: boolean; signingSpeed: number; highContrast: boolean; reducedMotion: boolean }
export interface SyncState { cue: Cue | null; animationTime: number; playing: boolean }
