import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Database } from 'lucide-react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders title and description', () => {
    const html = renderToStaticMarkup(
      <EmptyState icon={Database} title="No data" description="Import a dataset to begin." />,
    )
    expect(html).toContain('No data')
    expect(html).toContain('Import a dataset to begin.')
  })
})
