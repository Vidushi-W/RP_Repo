import { useId, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownToLine, ChevronLeft, ChevronRight, FileSpreadsheet, FolderOpen, HardDrive, History, Loader2, Search, Settings2, Trash2, UploadCloud, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { maintenanceApi } from '@/services/maintenanceApi'
import { settingsApi } from '@/services/settingsApi'
import { readApiError } from '@/lib/apiError'
import type { TrainingJob } from '@/types/training'

export function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill status-${status}`}><span aria-hidden="true" />{status.replaceAll('_', ' ')}</span>
}

export function ConfirmAction({ title, description, label, run, phrase, disabled, compact = false }: { title: string; description: string; label: string; run: () => Promise<unknown>; phrase?: string; disabled?: boolean; compact?: boolean }) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState('')
  const qc = useQueryClient()
  const mutation = useMutation({ mutationFn: run, onSettled: () => { void qc.invalidateQueries() }, onSuccess: () => { setOpen(false); setValue('') } })
  return <Dialog open={open} onOpenChange={next => { if (!mutation.isPending) { setOpen(next); setValue(''); mutation.reset() } }}>
    <DialogTrigger asChild><Button variant="ghost" size="sm" className="text-danger" disabled={disabled} aria-label={label}><Trash2 className="h-4 w-4" />{!compact && label}</Button></DialogTrigger>
    <DialogContent className="max-w-md" onInteractOutside={e => { if (mutation.isPending) e.preventDefault() }} onEscapeKeyDown={e => { if (mutation.isPending) e.preventDefault() }}>
      <DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription></DialogHeader>
      <DialogBody>{phrase && <label className="block text-sm">Type <strong>{phrase}</strong> to confirm<input className="studio-input mt-2" value={value} onChange={e => setValue(e.target.value)} autoComplete="off" /></label>}
        {mutation.error && <p role="alert" className="mt-3 text-sm text-danger">{(mutation.error as Error).message}</p>}
        <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" disabled={mutation.isPending} onClick={() => setOpen(false)}>Cancel</Button><Button variant="destructive" disabled={mutation.isPending || (!!phrase && value !== phrase)} onClick={() => mutation.mutate()}>{mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}{mutation.isPending ? 'Deleting…' : label}</Button></div>
      </DialogBody>
    </DialogContent>
  </Dialog>
}

export function UploadField({ label, files, onChange, multiple = false, optional = false }: { label: string; files: File[]; onChange: (files: File[]) => void; multiple?: boolean; optional?: boolean }) {
  const id = useId()
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  function select(incoming: File[]) {
    const csv = incoming.filter(file => file.name.toLowerCase().endsWith('.csv'))
    setError(csv.length !== incoming.length ? 'Choose CSV files. Extract ZIP archives before uploading.' : '')
    if (csv.length) onChange(multiple ? csv : csv.slice(0, 1))
  }
  return <div className="mt-5"><label htmlFor={id} className="mb-2 block text-sm font-medium">{label}{optional && <span className="ml-2 text-xs font-normal text-muted">Optional</span>}</label>
    <div className={`upload-zone ${dragging ? 'is-dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); select(Array.from(e.dataTransfer.files)) }}>
      <UploadCloud className="mx-auto h-6 w-6 text-accent" /><p className="mt-2 text-sm font-medium">Drop your CSV {multiple ? 'files' : 'file'} here</p><p className="mt-1 text-xs text-muted">or <label htmlFor={id} className="cursor-pointer font-semibold text-accent underline underline-offset-4">browse files</label> · CSV only</p>
      <input id={id} className="sr-only" type="file" multiple={multiple} accept=".csv" onChange={e => { select(Array.from(e.target.files || [])); e.target.value = '' }} />
    </div>
    {error && <p role="alert" className="mt-2 text-xs text-danger">{error}</p>}
    {!!files.length && <div className="mt-2 rounded-xl border border-border bg-surface-muted p-3"><div className="flex items-center gap-2 text-xs"><FileSpreadsheet className="h-4 w-4 text-accent" /><span className="min-w-0 flex-1 truncate">{files.length === 1 ? files[0].name : `${files.length} CSV files selected`}</span><span className="text-muted">{maintenanceApi.formatBytes(files.reduce((sum, file) => sum + file.size, 0))}</span><button type="button" className="icon-button" aria-label={`Clear ${label}`} onClick={() => onChange([])}><X className="h-3.5 w-3.5" /></button></div></div>}
  </div>
}

export function SearchField({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="search-field"><Search className="h-4 w-4 text-muted" /><input aria-label={placeholder} placeholder={placeholder} value={value} onChange={e => onChange(e.target.value)} />{value && <button type="button" aria-label="Clear search" onClick={() => onChange('')}><X className="h-3.5 w-3.5" /></button>}</label>
}

export function Pagination({ page, total, size, onChange }: { page: number; total: number; size: number; onChange: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size))
  return <div className="pagination"><p>{total ? `${(page - 1) * size + 1}–${Math.min(page * size, total)} of ${total}` : 'No results'}</p><div className="flex items-center gap-2"><Button size="sm" variant="secondary" aria-label="Previous page" disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft className="h-4 w-4" /></Button><span>Page {page} of {pages}</span><Button size="sm" variant="secondary" aria-label="Next page" disabled={page >= pages} onClick={() => onChange(page + 1)}><ChevronRight className="h-4 w-4" /></Button></div></div>
}

export function TrainingHistory() {
  const { data: jobs = [], error, isPending } = useQuery({ queryKey: ['studio-training-history'], queryFn: async () => { const response = await fetch('/api/training/jobs'); if (!response.ok) throw new Error(await readApiError(response)); return response.json() as Promise<TrainingJob[]> }, refetchInterval: 5000 })
  const [filter, setFilter] = useState('all')
  const [page, setPage] = useState(1)
  const completed = jobs.filter(job => !['running', 'queued'].includes(job.status))
  const filtered = jobs.filter(job => filter === 'all' || job.status === filter)
  const currentPage = Math.min(page, Math.max(1, Math.ceil(filtered.length / 8)))
  async function clear() { for (const job of completed) await maintenanceApi.deleteJob(job.id) }
  return <section className="studio-panel overflow-hidden !p-0"><div className="section-heading"><div><p className="eyebrow">YOUR WORKSPACE</p><h2 className="mt-1 text-lg font-semibold">Training history <span className="count-badge">{jobs.length}</span></h2></div><ConfirmAction title="Clear finished training history?" description={`Delete ${completed.length} finished session records. Model files, learned weights, and recordings are kept. Active sessions are skipped.`} label="Clear history" run={clear} disabled={!completed.length} phrase="CLEAR" /></div>
    <div className="flex flex-wrap items-center justify-between gap-3 px-6 pb-4"><p className="text-xs text-muted">Your model continues learning across sessions.</p><label className="text-xs text-muted">Status <select className="ml-2 rounded-lg border border-border bg-surface px-3 py-2 text-foreground" value={filter} onChange={e => { setFilter(e.target.value); setPage(1) }}><option value="all">All sessions</option>{Array.from(new Set(jobs.map(job => job.status))).map(status => <option key={status} value={status}>{status}</option>)}</select></label></div>
    {error && <p role="alert" className="px-6 pb-4 text-sm text-danger">{(error as Error).message}</p>}
    {!filtered.length ? <div className="empty-state"><History className="h-8 w-8 text-muted" /><h3>{isPending ? 'Loading sessions…' : 'A fresh start'}</h3><p>{isPending ? 'Fetching your training history.' : 'Your training sessions will appear here.'}</p></div> : <div className="overflow-x-auto"><table className="data-table w-full"><thead><tr><th>Session</th><th>Status</th><th>Progress</th><th>Training loss</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{filtered.slice((currentPage - 1) * 8, currentPage * 8).map(job => <tr key={job.id}><td className="min-w-52"><p className="font-medium">Session #{job.id}</p><p className="mt-1 text-xs text-muted">{new Date(job.created_at).toLocaleString()}</p><p className="mt-1 max-w-sm text-xs text-muted">{job.message}</p></td><td><StatusPill status={job.status} /></td><td className="min-w-32"><span className="text-xs">{job.current_epoch} / {job.total_epochs} rounds</span><progress className="mt-2 block h-1.5 w-24" max={job.total_epochs || 1} value={job.current_epoch} aria-label={`Session ${job.id} progress`} /></td><td className="font-mono text-xs">{job.train_loss?.toFixed(4) ?? '—'}</td><td><ConfirmAction title={`Delete session #${job.id}?`} description="Remove this training history record. Model files and training recordings are kept." label="Delete session" compact run={() => maintenanceApi.deleteJob(job.id)} disabled={['running', 'queued'].includes(job.status)} /></td></tr>)}</tbody></table></div>}
    <div className="px-6"><Pagination page={currentPage} total={filtered.length} size={8} onChange={setPage} /></div>
  </section>
}

export function WorkspaceDialog() {
  const [open, setOpen] = useState(false)
  const { data: storage, error } = useQuery({ queryKey: ['workspace-storage'], queryFn: maintenanceApi.storage, enabled: open })
  const backup = useMutation({ mutationFn: async () => { const data = await settingsApi.exportMetadata(); const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = `slsl-workspace-${new Date().toISOString().slice(0, 10)}.json`; link.click(); URL.revokeObjectURL(url) } })
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button variant="ghost" size="sm"><Settings2 className="h-4 w-4" /><span className="hidden sm:inline">Workspace</span></Button></DialogTrigger><DialogContent className="max-w-lg"><DialogHeader><DialogTitle>Workspace management</DialogTitle><DialogDescription>A little housekeeping for your local studio.</DialogDescription></DialogHeader><DialogBody>
    <div className="rounded-xl border border-border bg-surface-muted p-4"><div className="flex items-center gap-2 font-medium"><HardDrive className="h-4 w-4 text-accent" />Local storage</div>{storage ? <div className="mt-4 grid grid-cols-3 gap-3">{[['Database', storage.database_size_bytes], ['Recordings', storage.data_dir_size_bytes], ['Models', storage.artifacts_dir_size_bytes]].map(([label, bytes]) => <div key={String(label)}><p className="text-xs text-muted">{label}</p><p className="mt-1 text-sm font-semibold">{maintenanceApi.formatBytes(Number(bytes))}</p></div>)}</div> : <p className="mt-3 text-sm text-muted">{error ? 'Storage summary unavailable.' : 'Checking storage…'}</p>}</div>
    <div className="mt-5 flex items-start gap-3"><FolderOpen className="mt-1 h-5 w-5 shrink-0 text-accent" /><div><h3 className="text-sm font-semibold">Export workspace metadata</h3><p className="mt-1 text-xs leading-5 text-muted">Download dataset, model, and configuration metadata. Recording CSVs and trained model weights are not included.</p><Button className="mt-3" variant="secondary" size="sm" disabled={backup.isPending} onClick={() => backup.mutate()}><ArrowDownToLine className="h-4 w-4" />{backup.isPending ? 'Exporting…' : 'Export metadata'}</Button>{backup.isSuccess && <p role="status" className="mt-2 text-xs text-success">Metadata export downloaded.</p>}{backup.error && <p role="alert" className="mt-2 text-xs text-danger">{(backup.error as Error).message}</p>}</div></div>
    <div className="mt-6 rounded-xl bg-accent-soft p-4 text-xs leading-5 text-muted">Manage collections on the Data page. Delete completed sessions or clear training history on Train. Model reset is available under Train → Start over.</div>
  </DialogBody></DialogContent></Dialog>
}
