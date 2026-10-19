import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ChartSeries } from '@/types/dataset'

interface SensorChartProps {
  title: string
  series: ChartSeries
  color: string
}

export function SensorChart({ title, series, color }: SensorChartProps) {
  const data = series.timestamps_ms.map((t, i) => ({ t: (t / 1000).toFixed(2), v: series.values[i] }))
  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-white p-4">
      <p className="mb-2 text-xs font-medium text-[var(--color-muted)]">{title}</p>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="t" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={36} />
            <Tooltip />
            <Line type="monotone" dataKey="v" stroke={color} dot={false} strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
