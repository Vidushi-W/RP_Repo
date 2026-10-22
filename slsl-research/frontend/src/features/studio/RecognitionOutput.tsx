import { AudioLines, Check, Loader2, Sparkles } from 'lucide-react'
import { SinhalaSpeech, type SpeechTarget } from './SinhalaSpeech'
import { Button } from '@/components/ui/button'

export interface ExpressionAnnotation {
  label: 'angry' | null
  matched_words: string[]
  status: string
  source: string
  message: string
}

export interface SpokenSentence {
  display_text?: string
  expression?: ExpressionAnnotation
  text: string
  status: string
  message: string
  model_name: string
  generation_ms: number
}

interface Props {
  speechTarget?: SpeechTarget | null
  predicting: { filename: string } | null
  words: string[] | null
  expression?: ExpressionAnnotation | null
  analyzing: boolean
  suggestion: SpokenSentence | null
  liveText: string
  playing: boolean
  elapsed: number
  onRetry: () => void
  disabled: boolean
}

export function RecognitionOutput({ speechTarget, predicting, words, expression, analyzing, suggestion, liveText, playing, elapsed, onRetry, disabled }: Props) {
  const hasWords = words !== null
  const annotation = suggestion?.expression ?? expression
  const matched = new Set(annotation?.matched_words ?? [])
  const canRetry = hasWords && !!words.length && !!suggestion && ['unavailable', 'timeout', 'busy', 'error', 'fallback'].includes(suggestion.status)
  return <section className="studio-panel test-output">
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs font-semibold uppercase tracking-wider text-accent">Recognition output</p><ol aria-label="Recognition stages" className="flex items-center gap-3 text-[10px] text-muted">{['Motion', 'Words', 'Sentence'].map((label, i) => {
      const complete = i === 0 ? hasWords : i === 1 ? hasWords : !!suggestion?.text
      const active = i === 0 ? !!predicting : i === 2 && analyzing
      return <li key={label} className={`flex items-center gap-1.5 ${active || complete ? 'text-accent' : ''}`}><span className={`flex h-4 w-4 items-center justify-center rounded-full border ${complete ? 'border-accent/30 bg-accent/10' : 'border-current/25'}`}>{complete ? <Check size={9} aria-hidden="true" /> : i + 1}</span>{label}</li>
    })}</ol></div>
    <div className="mt-5" aria-live="polite" aria-atomic="false">
      {predicting ? <div role="status" className="flex min-h-20 items-center gap-4"><span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-accent/15 bg-surface/70"><Loader2 aria-hidden="true" className="h-6 w-6 animate-spin text-accent motion-reduce:animate-none" /></span><div className="min-w-0"><p className="text-xl font-medium">Predicting motion…</p><p className="mt-1 break-all text-xs text-muted">Analyzing {predicting.filename}. The recognized words will appear first.</p></div></div> : hasWords ? <>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Recognized words · motion model</p>
        {words.length ? <div className="mt-3 flex flex-wrap gap-2">{words.map((word, index) => <span key={`${index}-${word}`} className={`rounded-lg border px-3 py-2 text-sm font-semibold ${matched.has(word.trim().toUpperCase().replace(/\s+/g, ' ')) ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-accent/15 bg-surface/80'}`}>{word}</span>)}</div> : <p className="mt-3 text-sm">No signs recognized. Try another recording.</p>}
        {annotation?.label === 'angry' && <p className="mt-3 text-xs text-rose-800">Configured expression: <strong>angry</strong> · matched {annotation.matched_words.join(', ')}</p>}
        {annotation?.status === 'unavailable' && <p role="status" className="mt-3 text-xs text-warning">{annotation.message}</p>}
        <div className="mt-5 border-t border-accent/15 pt-5" aria-busy={analyzing}>
          {analyzing ? <div role="status" className="flex items-center gap-3"><Loader2 aria-hidden="true" className="h-5 w-5 shrink-0 animate-spin text-accent motion-reduce:animate-none" /><div><p className="text-sm font-semibold">Forming sentence…</p><p className="mt-1 text-xs text-muted">The local AI is analyzing the recognized words and adding English grammar.</p></div></div> : suggestion?.text ? <><p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-accent"><Sparkles size={13} aria-hidden="true" />{suggestion.status === 'fallback' ? 'Word-based sentence fallback' : 'Suggested spoken sentence · local AI'}</p><p className="mt-3 text-2xl font-medium leading-relaxed">{suggestion.display_text ?? suggestion.text}</p><p className="mt-3 text-[11px] leading-5 text-muted">{suggestion.message}</p></> : suggestion ? <><p className="text-sm font-medium">Sentence suggestion unavailable</p><p className="mt-2 text-xs leading-5 text-muted">{suggestion.message}</p></> : <p className="text-xs text-muted">Your sentence suggestion will appear here.</p>}
          {suggestion?.text && speechTarget && !analyzing && <SinhalaSpeech key={`${speechTarget.recognitionId}:${suggestion.text}`} target={speechTarget} disabled={disabled} />}
          {canRetry && !analyzing && <Button className="mt-3" size="sm" variant="secondary" disabled={disabled} onClick={onRetry}><Sparkles size={13} />Try sentence again</Button>}
        </div>
      </> : <><AudioLines className="mb-3 h-6 w-6 text-accent/60" aria-hidden="true" /><p className="min-h-12 text-2xl font-medium">{liveText || 'Choose a recording below to see its output.'}</p><p className="mt-3 text-xs text-muted">{liveText ? 'CSV playback output. Use Recognize to generate a local AI sentence.' : 'Recognized words appear first, followed by a local AI sentence suggestion.'}</p></>}
    </div>
    {playing && <p className="mt-3 text-xs text-muted">Playing · {(elapsed / 1000).toFixed(1)} seconds · provisional text may change</p>}
  </section>
}
