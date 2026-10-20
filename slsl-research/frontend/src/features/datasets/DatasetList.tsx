import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import type { DatasetSummary } from '@/types/dataset'

export function DatasetList({ datasets }: { datasets: DatasetSummary[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
      <table className="data-table min-w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Version</th>
            <th>Recordings</th>
            <th>Provenance</th>
            <th>Status</th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <tr key={d.id}>
              <td>
                <Link to={`/datasets/${d.id}`} className="font-medium text-accent hover:underline">{d.name}</Link>
                {d.description && <p className="mt-0.5 max-w-md text-xs text-muted">{d.description}</p>}
              </td>
              <td className="text-muted">v{d.current_version}</td>
              <td>{d.recording_count}</td>
              <td className="capitalize">{d.provenance}</td>
              <td><Badge variant={d.status === 'ready' ? 'success' : 'secondary'}>{d.status}</Badge></td>
              <td>
                <Link to={`/datasets/${d.id}`} className="inline-flex text-muted hover:text-accent" aria-label={`Open ${d.name}`}>
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
