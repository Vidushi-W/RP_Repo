import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { Preferences } from '../types';
const defaults: Preferences = { avatarSize: 'medium', avatarVisible: true, signingSpeed: 1, highContrast: false, reducedMotion: false };
const key = 'lankasigns.avatar.preferences.v1';
function load(): Preferences {
  try {
    const data = JSON.parse(localStorage.getItem(key) || '{}');
    return { avatarSize: ['small','medium','large'].includes(data.avatarSize) ? data.avatarSize : defaults.avatarSize, avatarVisible: typeof data.avatarVisible === 'boolean' ? data.avatarVisible : true, signingSpeed: [0.5, 0.75, 1, 1.25, 1.5].includes(data.signingSpeed) ? data.signingSpeed : 1, highContrast: data.highContrast === true, reducedMotion: data.reducedMotion === true };
  } catch { return defaults; }
}
const Context = createContext<{ preferences: Preferences; update: (patch: Partial<Preferences>) => void; reset: () => void } | null>(null);
export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, set] = useState(load);
  useEffect(() => { try { localStorage.setItem(key, JSON.stringify(preferences)); } catch { /* Session preferences still work when storage is blocked. */ } }, [preferences]);
  return <Context.Provider value={{ preferences, update: patch => set(current => ({ ...current, ...patch })), reset: () => set(defaults) }}>{children}</Context.Provider>;
}
export function usePreferences() { const context = useContext(Context); if (!context) throw new Error('PreferencesProvider missing'); return context; }
