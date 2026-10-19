import { MessageSquare, Upload } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

export function PlaygroundPage() {
  return (
    <div>
      <PageHeader
        title="Playground"
        description="A chat-like view of recognized English sign-language messages — not an LLM chatbot."
        action={<Button disabled><Upload className="h-4 w-4" /> Upload Recording</Button>}
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <Card className="min-h-[420px]">
          <CardContent className="flex h-full flex-col py-6">
            <EmptyState
              icon={MessageSquare}
              title="No recognized messages yet"
              description="When recognition is implemented, confirmed English sentences, gloss sequences, emotion labels, and confidence feedback will appear here in chronological order."
            />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardContent className="space-y-3 py-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-muted)]">Input source</span>
                <Badge variant="secondary">CSV (planned)</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-muted)]">Physical gloves</span>
                <Badge variant="warning">Not connected</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--color-muted)]">Recognition</span>
                <Badge variant="secondary">Step 2</Badge>
              </div>
            </CardContent>
          </Card>
          <p className="text-xs leading-5 text-[var(--color-muted)]">
            Provisional predictions will be visually distinct from confirmed messages. Low-confidence results will request repetition instead of presenting uncertain text as final.
          </p>
        </div>
      </div>
    </div>
  )
}
