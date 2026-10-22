import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { readApiError } from '@/lib/apiError'

interface Rule { enabled: boolean; words: string[]; emotion: 'angry'; source: string }
async function request(init?: RequestInit): Promise<Rule> {
  const response = await fetch('/api/studio/expression-rules', init)
  if (!response.ok) throw new Error(await readApiError(response))
  return response.json()
}

export function ExpressionRuleSettings({ disabled }: { disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [enabled, setEnabled] = useState(true)
  const [text, setText] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saved, setSaved] = useState(false)
  const qc = useQueryClient()
  const { data, error, isPending } = useQuery({ queryKey: ['expression-rules'], queryFn: () => request(), enabled: open })
  useEffect(() => { if (data && !dirty) { setEnabled(data.enabled); setText(data.words.join(', ')) } }, [data, dirty])
  const words = text.split(/[,\n]+/).map(word => word.trim()).filter(Boolean)
  const save = useMutation({ mutationFn: () => request({ method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled, words }) }), onSuccess: rule => { qc.setQueryData(['expression-rules'], rule); setDirty(false); setSaved(true) } })
  function change() { setDirty(true); setSaved(false); save.reset() }
  return <details className="studio-panel" open={open} onToggle={e => setOpen(e.currentTarget.open)}><summary className="cursor-pointer text-sm font-semibold"><span className="inline-flex items-center gap-2"><SlidersHorizontal size={15} className="text-accent" />Angry expression rule</span></summary>
    <p className="mt-3 text-xs leading-5 text-muted">A matching recognized label adds <strong>[angry]</strong> after the sentence. This is your configured word rule, not emotion measured from the signer.</p>
    {isPending && !error ? <p role="status" className="mt-3 text-xs text-muted">Loading your rule…</p> : <>
      {error && <p role="alert" className="mt-3 text-xs text-danger">{(error as Error).message}</p>}
      <label className="mt-4 flex items-center gap-2 text-sm"><input type="checkbox" checked={enabled} disabled={disabled || save.isPending} onChange={e => { change(); setEnabled(e.target.checked) }} />Enable angry annotation</label>
      <label className="mt-4 block text-xs font-medium" htmlFor="angry-trigger-words">Trigger words <span className="font-normal text-muted">· separate with commas or new lines</span></label><textarea id="angry-trigger-words" className="studio-input mt-2 resize-y" rows={3} value={text} disabled={disabled || save.isPending} onChange={e => { change(); setText(e.target.value) }} />
      <p className="mt-2 text-[11px] text-muted">{words.length} entries · whole labels only · any matching word triggers angry, including in negated phrases. Unmatched phrases receive no emotion label.</p>
      <div className="mt-4 flex flex-wrap items-center gap-3"><Button size="sm" variant="secondary" disabled={disabled || save.isPending || !dirty || words.length > 100} onClick={() => save.mutate()}>{save.isPending && <Loader2 size={13} className="animate-spin" />}{save.isPending ? 'Saving…' : 'Save rule'}</Button>{saved && <p role="status" className="text-xs text-success">Saved. Recognize a recording again to apply the rule.</p>}</div>
      {save.error && <p role="alert" className="mt-3 text-xs text-danger">{(save.error as Error).message}</p>}
    </>}
  </details>
}
