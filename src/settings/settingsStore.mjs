export const SETTINGS_KEY = 'signlanka.preferences.v1';
export const DEFAULT_PREFERENCES = Object.freeze({
  hapticIntensity: 'normal',
  notificationsEnabled: true,
  phoneVibrationEnabled: false,
  retainAudioSamples: false,
});
export const DEFAULT_CATEGORIES = Object.freeze([
  'Fire alarm', 'Emergency vehicle siren', 'Vehicle horn', 'Doorbell', 'Human calling or shouting', 'Unknown sound',
]);
const intensities = new Set(['low', 'normal', 'high', 'critical']);

export function normalizePreferences(value = {}) {
  return {
    hapticIntensity: intensities.has(value.hapticIntensity) ? value.hapticIntensity : DEFAULT_PREFERENCES.hapticIntensity,
    notificationsEnabled: typeof value.notificationsEnabled === 'boolean' ? value.notificationsEnabled : DEFAULT_PREFERENCES.notificationsEnabled,
    phoneVibrationEnabled: typeof value.phoneVibrationEnabled === 'boolean' ? value.phoneVibrationEnabled : DEFAULT_PREFERENCES.phoneVibrationEnabled,
    retainAudioSamples: value.retainAudioSamples === true,
  };
}

export function validateCategory(input, existing = []) {
  const value = typeof input === 'string' ? input.trim().replace(/\s+/g, ' ') : '';
  if (value.length < 2 || value.length > 40) throw new Error('Category names must be 2 to 40 characters long.');
  if (!/^[\p{L}\p{N}][\p{L}\p{N} &'()-]*$/u.test(value)) throw new Error('Use letters, numbers, spaces, apostrophes, parentheses, ampersands, or hyphens only.');
  if (existing.some(item => item.toLowerCase() === value.toLowerCase())) throw new Error('That category already exists.');
  return value;
}

export function validateSample({ filename, category, uri } = {}) {
  const safeName = typeof filename === 'string' ? filename.trim().slice(0, 120) : '';
  if (!safeName || !/\.(wav|mp3|m4a|aac|flac|ogg|opus)$/i.test(safeName)) throw new Error('Choose a labelled audio clip in WAV, MP3, M4A, AAC, FLAC, OGG, or OPUS format.');
  if (typeof category !== 'string' || !category.trim()) throw new Error('Select a category for this sample.');
  if (typeof uri !== 'string' || !uri.startsWith('file://')) throw new Error('The selected audio file is not available in local storage.');
  return { id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, filename: safeName, category: category.trim(), uri, createdAt: new Date().toISOString(), status: 'stored_locally_not_used_for_training' };
}

export function createSettingsStore(storage, key = SETTINGS_KEY) {
  async function load() {
    const raw = await storage.getItem(key);
    if (!raw) return { preferences: { ...DEFAULT_PREFERENCES }, categories: [...DEFAULT_CATEGORIES], samples: [] };
    try {
      const parsed = JSON.parse(raw);
      return {
        preferences: normalizePreferences(parsed.preferences),
        categories: Array.isArray(parsed.categories) ? [...new Set([...DEFAULT_CATEGORIES, ...parsed.categories.filter(value => typeof value === 'string')])] : [...DEFAULT_CATEGORIES],
        samples: Array.isArray(parsed.samples) ? parsed.samples.filter(sample => sample && typeof sample.uri === 'string' && typeof sample.filename === 'string' && typeof sample.category === 'string') : [],
      };
    } catch {
      return { preferences: { ...DEFAULT_PREFERENCES }, categories: [...DEFAULT_CATEGORIES], samples: [] };
    }
  }
  async function save(next) { await storage.setItem(key, JSON.stringify(next)); return next; }
  return {
    load,
    async updatePreferences(changes) {
      const current = await load();
      return save({ ...current, preferences: normalizePreferences({ ...current.preferences, ...changes }) });
    },
    async addCategory(input) {
      const current = await load();
      const category = validateCategory(input, current.categories);
      return save({ ...current, categories: [...current.categories, category] });
    },
    async addSample(input) {
      const current = await load();
      if (!current.preferences.retainAudioSamples) throw new Error('Enable audio retention and confirm the local storage notice before importing clips.');
      const sample = validateSample(input);
      if (!current.categories.includes(sample.category)) throw new Error('Choose one of the available categories.');
      return save({ ...current, samples: [sample, ...current.samples] });
    },
    async removeSample(id) {
      const current = await load();
      return save({ ...current, samples: current.samples.filter(sample => sample.id !== id) });
    },
    async resetPreferences() {
      const current = await load();
      return save({ ...current, preferences: { ...DEFAULT_PREFERENCES }, categories: [...DEFAULT_CATEGORIES], samples: [] });
    },
    async clearSamples() {
      const current = await load();
      return save({ ...current, samples: [] });
    },
    async clearAll() { return save({ preferences: { ...DEFAULT_PREFERENCES }, categories: [...DEFAULT_CATEGORIES], samples: [] }); },
  };
}
