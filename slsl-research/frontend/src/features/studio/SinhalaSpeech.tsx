import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Download, Languages, Loader2, RefreshCw, Volume2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { readApiError } from '@/lib/apiError'

export interface SinhalaResult {
  translation_id: string
  text: string
  english: string
  emotion: string | null
  message: string
  speech: { audio_url: string; emotion: string | null; style_method: string } | null
}

export interface SpeechTarget { testId: string; recognitionId: string }

export function SinhalaSpeech({ target, disabled }: { target: SpeechTarget; disabled: boolean }) {
  const qc = useQueryClient()
  const [result, setResult] = useState<SinhalaResult | null>(null)
  const [stage, setStage] = useState<'translating' | 'speaking' | 'ready' | 'error'>('translating')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const { testId, recognitionId } = target
  useEffect(() => {
    const controller = new AbortController()
    async function post(path: string, body: unknown): Promise<SinhalaResult> {
      const response = await fetch(`/api/studio/tests/${testId}/${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body), signal: controller.signal,
      })
      if (!response.ok) throw new Error(await readApiError(response))
      return response.json() as Promise<SinhalaResult>
    }
    async function generate() {
      setEditing(false); setSaving(false); setResult(null); setError(''); setStage('translating')
      try {
        const translation = await post('translate', { recognition_id: recognitionId })
        if (controller.signal.aborted) return
        setResult(translation); setStage('speaking')
        const spoken = await post('speech', { recognition_id: recognitionId, translation_id: translation.translation_id })
        if (controller.signal.aborted) return
        setResult(spoken); setStage('ready')
        void qc.invalidateQueries({ queryKey: ['studio-tests'] })
      } catch (e) {
        if (!controller.signal.aborted) { setError((e as Error).message); setStage('error') }
      }
    }
    // Defer one task so React StrictMode's mount cleanup cancels the first request.
    const timer = window.setTimeout(() => { void generate() }, 0)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [testId, recognitionId, attempt, qc])
  async function regenerateAudio(translation: SinhalaResult) {
    setStage('speaking'); setError('')
    try {
      const response = await fetch(`/api/studio/tests/${testId}/speech`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recognition_id: recognitionId, translation_id: translation.translation_id }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      setResult(await response.json() as SinhalaResult); setStage('ready')
    } catch (e) { setError((e as Error).message); setStage('error') }
    finally { void qc.invalidateQueries({ queryKey: ['studio-tests'] }) }
  }
  async function saveCorrection() {
    if (!result) return
    setSaving(true); setError('')
    try {
      const response = await fetch(`/api/studio/tests/${testId}/translation`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recognition_id: recognitionId, translation_id: result.translation_id, text: draft }),
      })
      if (!response.ok) throw new Error(await readApiError(response))
      const updated = await response.json() as SinhalaResult
      setResult(updated); setEditing(false); setStage('speaking')
      await regenerateAudio(updated)
    } catch (e) { setError((e as Error).message); setStage('error') }
    finally { setSaving(false) }
  }
  return <div className="mt-5 border-t border-accent/15 pt-5">
    <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wider text-accent"><Languages size={13} aria-hidden="true" />Sinhala · text & voice</p>
    {stage === 'translating' && <p role="status" className="mt-3 flex items-center gap-2 text-sm"><Loader2 size={16} className="animate-spin motion-reduce:animate-none" />Translating to Sinhala…</p>}
    {result && <><p lang="si" className="mt-3 text-2xl font-medium leading-relaxed">{result.text}</p><p className="mt-2 text-[11px] text-muted">{result.message}</p></>}
    {result && !editing && stage !== 'speaking' && <Button size="sm" variant="secondary" className="mt-3" disabled={disabled || saving} onClick={() => { setDraft(result.text); setEditing(true) }}>Edit Sinhala</Button>}
    {result && editing && <div className="mt-3"><label className="text-xs font-medium" htmlFor="sinhala-correction">Sinhala wording</label><textarea id="sinhala-correction" lang="si" className="studio-input mt-2 min-h-24" value={draft} maxLength={1500} disabled={saving} onChange={e => setDraft(e.target.value)} /><div className="mt-2 flex gap-2"><Button size="sm" disabled={disabled || saving || !draft.trim()} onClick={() => { void saveCorrection() }}>{saving ? 'Preparing voice…' : 'Save & regenerate voice'}</Button><Button size="sm" variant="secondary" disabled={saving} onClick={() => setEditing(false)}>Cancel</Button></div></div>}
    {stage === 'speaking' && <p role="status" className="mt-3 flex items-center gap-2 text-sm"><Loader2 size={16} className="animate-spin motion-reduce:animate-none" />Preparing Sinhala voice…</p>}
    {result?.speech && <><p className="mt-3 flex items-center gap-2 text-xs text-muted"><Volume2 size={14} />{result.speech.emotion ? `${result.speech.emotion}-style delivery · simulated speaking style` : 'Normal delivery · no emotion applied'}</p><audio key={result.speech.audio_url} aria-label="Sinhala sentence audio" controls preload="none" className="mt-3 w-full" src={result.speech.audio_url} /><a className="mt-2 inline-flex items-center gap-2 text-xs font-medium text-accent" href={result.speech.audio_url} download="sinhala-speech.wav"><Download size={13} />Download audio</a></>}
    {stage === 'error' && <div role="alert" className="mt-3"><p className="text-xs text-danger">{error}</p><Button size="sm" variant="secondary" className="mt-2" disabled={disabled} onClick={() => { if (result) void regenerateAudio(result); else setAttempt(value => value+1) }}><RefreshCw size={13} />{result ? 'Try voice again' : 'Try Sinhala again'}</Button></div>}
  </div>
}
