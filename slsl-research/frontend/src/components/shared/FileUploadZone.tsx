import { Upload } from 'lucide-react'
import { useRef } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface FileUploadZoneProps {
  files: File[]
  onChange: (files: File[]) => void
  accept?: string
  multiple?: boolean
  label?: string
  hint?: string
  className?: string
}

export function FileUploadZone({ files, onChange, accept = '.csv,.zip', multiple = true, label = 'Choose files', hint, className }: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = (incoming: FileList | null) => {
    if (!incoming?.length) return
    const next = multiple ? [...files, ...Array.from(incoming)] : [incoming[0]]
    const seen = new Set<string>()
    onChange(next.filter((f) => {
      const key = `${f.name}:${f.size}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }))
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div
        className="rounded-xl border-2 border-dashed border-border bg-surface-muted/50 p-6 text-center transition hover:border-accent/30 hover:bg-accent-soft/30"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          addFiles(e.dataTransfer.files)
        }}
      >
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-accent-soft text-accent">
          <Upload className="h-4 w-4" />
        </div>
        <p className="text-sm font-medium text-foreground">Drop files here or browse</p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple={multiple}
          accept={accept}
          onChange={(e) => {
            addFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <Button type="button" variant="secondary" size="sm" className="mt-4" onClick={() => inputRef.current?.click()}>
          {label}
        </Button>
      </div>
      {files.length > 0 && (
        <ul className="space-y-1.5 text-sm">
          {files.map((f) => (
            <li key={`${f.name}-${f.size}`} className="flex items-center justify-between rounded-lg border border-border bg-surface px-3 py-2 shadow-sm">
              <span className="truncate">{f.name} <span className="text-xs text-muted">({(f.size / 1024).toFixed(1)} KB)</span></span>
              <button type="button" className="text-xs font-medium text-danger hover:underline" onClick={() => onChange(files.filter((x) => x !== f))}>Remove</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
