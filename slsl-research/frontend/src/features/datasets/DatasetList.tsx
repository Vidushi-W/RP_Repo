import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import type { DatasetSummary } from '@/types/dataset'

export function DatasetList({ datasets }: { datasets: DatasetSummary[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-[var(--color-muted)]">
          <tr>
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Version</th>
            <th className="px-4 py-3 font-medium">Recordings</th>
            <th className="px-4 py-3 font-medium">Provenance</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <tr key={d.id} className="border-t border-[var(--color-border)] hover:bg-slate-50/80">
              <td className="px-4 py-3">
                <Link to={`/datasets/${d.id}`} className="font-medium text-indigo-700 hover:underline">{d.name}</Link>
                {d.description && <p className="mt-0.5 text-xs text-[var(--color-muted)]">{d.description}</p>}
              </td>
              <td className="px-4 py-3">{d.current_version}</td>
              <td className="px-4 py-3">{d.recording_count}</td>
              <td className="px-4 py-3 capitalize">{d.provenance}</td>
              <td className="px-4 py-3"><Badge variant={d.status === 'ready' ? 'success' : 'secondary'}>{d.status}</Badge></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
