import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Settings } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { settingsApi } from '@/services/settingsApi'

export function SettingsDialog() {
  const [open, setOpen] = useState(false)
  const qc = useQueryClient()
  const { data: settings } = useQuery({
    queryKey: ['studio-settings'],
    queryFn: settingsApi.get,
    enabled: open,
  })

  const saveMutation = useMutation({
    mutationFn: (patch: { torch_threads?: number; uncertainty_threshold?: number; theme?: 'light' | 'dark' }) =>
      settingsApi.update(patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['studio-settings'] }),
  })

  const exportMutation = useMutation({
    mutationFn: settingsApi.exportMetadata,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `slsl-studio-export-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  return (
    <>
      <button
        type="button"
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-[var(--color-muted)] hover:bg-slate-50 hover:text-[var(--color-foreground)]"
        onClick={() => setOpen(true)}
      >
        <Settings className="h-4 w-4" /> Settings
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-lg rounded-xl border bg-white p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Studio Settings</h2>
              <button type="button" className="text-sm text-[var(--color-muted)]" onClick={() => setOpen(false)}>Close</button>
            </div>
            <p className="mt-1 text-xs text-[var(--color-muted)]">Local single-administrator configuration. Storage paths are set via environment variables.</p>

            {settings && (
              <div className="mt-4 space-y-4 text-sm">
                <div>
                  <label className="text-xs text-[var(--color-muted)]">Data directory (read-only)</label>
                  <p className="font-mono text-xs break-all">{settings.data_dir}</p>
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted)]">Artifacts directory (read-only)</label>
                  <p className="font-mono text-xs break-all">{settings.artifacts_dir}</p>
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted)]">CPU threads for training</label>
                  <input
                    type="number"
                    min={1}
                    max={8}
                    className="mt-1 w-full rounded-md border px-3 py-2"
                    value={settings.torch_threads}
                    onChange={(e) => saveMutation.mutate({ torch_threads: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted)]">Recognition uncertainty threshold</label>
                  <input
                    type="number"
                    step={0.05}
                    min={0}
                    max={1}
                    className="mt-1 w-full rounded-md border px-3 py-2"
                    value={settings.uncertainty_threshold}
                    onChange={(e) => saveMutation.mutate({ uncertainty_threshold: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--color-muted)]">Max upload (MB, env default)</label>
                  <p>{settings.max_upload_mb} MB</p>
                </div>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                Export metadata
              </Button>
              <Button variant="secondary" onClick={() => setOpen(false)}>Done</Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
