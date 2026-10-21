import type { AgentResult, SignSegment } from '../types/hands';
import { finite, record, validSignId } from './animationSchema';
function signList(value: unknown): string[] {
  if (!Array.isArray(value) || value.length > 200 || !value.every(validSignId)) throw new Error('Agent signs must be up to 200 explicit sign identifiers.');
  return [...value];
}
export function parseSegments(value: unknown): SignSegment[] {
  if (!Array.isArray(value) || value.length > 1000) throw new Error('Invalid timestamped segments.');
  let previousEnd = -1;
  return value.map(segment => {
    if (!record(segment) || !finite(segment.startMs) || !finite(segment.endMs) || segment.startMs < 0 || segment.endMs <= segment.startMs || segment.startMs < previousEnd) throw new Error('Segments must be ordered, non-overlapping millisecond intervals.');
    previousEnd = segment.endMs;
    return { startMs: segment.startMs, endMs: segment.endMs, signs: signList(segment.signs) };
  });
}
export function parseAgentResult(value: unknown): AgentResult {
  if (!record(value) || typeof value.englishText !== 'string' || value.englishText.length > 20000 || (value.sinhalaText !== undefined && (typeof value.sinhalaText !== 'string' || value.sinhalaText.length > 20000))) throw new Error('Invalid agent text fields.');
  const signs = signList(value.signs);
  const segments = value.segments === undefined ? undefined : parseSegments(value.segments);
  if (segments && JSON.stringify(segments.flatMap(segment => segment.signs)) !== JSON.stringify(signs)) throw new Error('Top-level signs must equal the ordered signs in timestamped segments.');
  return {englishText:value.englishText,sinhalaText:value.sinhalaText as string|undefined,signs,segments};
}
export type AgentClient = (englishText: string, signal?: AbortSignal) => Promise<unknown>;
export async function requestAgent(client: AgentClient | null, englishText: string, signal?: AbortSignal) {
  if (!client) throw new Error('Agent integration pending. No translation service is configured.');
  return parseAgentResult(await client(englishText,signal));
}
