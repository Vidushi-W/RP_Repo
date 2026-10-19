import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertCircle, BookOpen, Hand, MessageSquare, Mic, Pause, Play, Radio, RotateCcw,
  Square, Upload, Vibrate, Zap,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { SensorChart } from '@/components/shared/SensorChart'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { playgroundApi } from '@/services/playgroundApi'
import { trainingApi } from '@/services/trainingApi'
import type { ChatMessage, DictionaryEntry, LiveTickResponse, RecognitionMessage } from '@/types/playground'

function MessageBlock({ msg }: { msg: ChatMessage | RecognitionMessage }) {
  const uncertain = msg.uncertain
  return (
    <div className={`max-w-xl rounded-2xl border px-5 py-4 shadow-sm ${uncertain ? 'border-amber-200 bg-amber-50/60' : 'border-slate-200 bg-white'}`}>
      {uncertain && msg.feedback && (
        <p className="mb-2 flex items-center gap-1.5 text-xs text-amber-800">
          <Vibrate className="h-3.5 w-3.5" /> {msg.feedback.message}
          {msg.feedback.simulated && <span className="text-amber-600">(simulated — no glove motor)</span>}
        </p>
      )}
      <p className="text-lg font-medium text-slate-900 leading-snug">
        {msg.english || <span className="text-slate-500 font-mono text-sm">{msg.gloss_sequence.join(' | ') || 'No signs detected'}</span>}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {msg.gloss_sequence.map((g, i) => (
          <span key={`${g}-${i}`} className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">{g}</span>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {msg.emotion ? (
          <Badge variant={msg.emotion === 'angry' ? 'warning' : 'secondary'}>{msg.emotion}</Badge>
        ) : (
          <span>Emotion unavailable</span>
        )}
        <span>·</span>
        <span>Score {msg.decoder_score.toFixed(2)} (uncalibrated)</span>
        <span>·</span>
        <span>{msg.inference_ms.toFixed(0)} ms</span>
        <span>·</span>
        <span>{msg.model_name} v{msg.model_version}</span>
      </div>
      <p className="mt-1 text-[10px] text-slate-400">{new Date(msg.timestamp * 1000).toLocaleString()} · {msg.filename}</p>
    </div>
  )
}

function RecognitionTab() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [modelId, setModelId] = useState<number | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [fileMeta, setFileMeta] = useState<{ name: string; size: number } | null>(null)

  const { data: status } = useQuery({ queryKey: ['playground-status'], queryFn: playgroundApi.status })
  const { data: models = [] } = useQuery({ queryKey: ['models'], queryFn: () => trainingApi.listModels(false) })

  const recognizeMutation = useMutation({
    mutationFn: () => playgroundApi.recognize(pendingFile!, modelId ?? undefined),
    onSuccess: (msg) => {
      setMessages((prev) => [...prev, { ...msg, id: `${msg.timestamp}-${prev.length}` }])
      setPendingFile(null)
      setFileMeta(null)
    },
  })

  const onFile = (f: File | null) => {
    setPendingFile(f)
    setFileMeta(f ? { name: f.name, size: f.size } : null)
  }

  if (!status?.active_model && models.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-12 text-center">
          <MessageSquare className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-4 font-medium">No trained model available</p>
          <p className="mt-1 text-sm text-[var(--color-muted)]">Train and activate a model before using recognition.</p>
          <Button asChild className="mt-4"><Link to="/training">Go to Training</Link></Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
      <div className="flex min-h-[480px] flex-col rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50/80 to-white">
        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-[300px] flex-col items-center justify-center text-center">
              <div className="rounded-full bg-indigo-100 p-4"><Mic className="h-6 w-6 text-indigo-600" /></div>
              <p className="mt-4 text-sm font-medium text-slate-700">Upload a sensor recording to recognize signs</p>
              <p className="mt-1 max-w-sm text-xs text-slate-500">This is sign-language recognition, not a chatbot. Results come from your trained CNN–BiLSTM–CTC model.</p>
            </div>
          ) : (
            messages.map((m) => <MessageBlock key={m.id} msg={m} />)
          )}
        </div>
        <div className="border-t border-slate-100 bg-white/90 p-4 rounded-b-2xl">
          {fileMeta && <p className="mb-2 text-xs text-slate-500">Ready: {fileMeta.name} ({(fileMeta.size / 1024).toFixed(1)} KB)</p>}
          <div className="flex flex-wrap gap-2">
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm hover:bg-slate-50">
              <Upload className="h-4 w-4" /> Upload Sensor CSV
              <input type="file" accept=".csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0] ?? null)} />
            </label>
            <select className="rounded-lg border px-3 py-2 text-sm" value={modelId ?? ''} onChange={(e) => setModelId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Active model</option>
              {models.filter((m) => !m.is_archived).map((m) => (
                <option key={m.id} value={m.id}>{m.name} {m.status === 'active' ? '★' : ''}</option>
              ))}
            </select>
            <Button disabled={!pendingFile || recognizeMutation.isPending} onClick={() => recognizeMutation.mutate()}>
              <Zap className="h-4 w-4" /> Recognize
            </Button>
            <Button variant="secondary" onClick={() => setMessages([])}>Clear Conversation</Button>
          </div>
          {recognizeMutation.error && <p className="mt-2 text-xs text-rose-600">{(recognizeMutation.error as Error).message}</p>}
        </div>
      </div>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Session</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-xs text-[var(--color-muted)]">
          <p>Model: {status?.active_model?.name ?? 'Select above'} v{status?.active_model?.version ?? '—'}</p>
          <p>Messages: {messages.length}</p>
          <p className="leading-relaxed">Ground-truth labels are never accessed during recognition.</p>
        </CardContent>
      </Card>
    </div>
  )
}

function LiveInputTab() {
  const [source, setSource] = useState<'csv_playback' | 'hardware_gloves'>('csv_playback')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [tick, setTick] = useState<LiveTickResponse | null>(null)
  const [speed, setSpeed] = useState(1)
  const pollRef = useRef<number | null>(null)

  const { data: status } = useQuery({ queryKey: ['playground-status'], queryFn: playgroundApi.status })

  const initSession = useMutation({
    mutationFn: () => playgroundApi.createLiveSession(source),
    onSuccess: (s) => setSessionId(s.session_id),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => playgroundApi.liveUpload(sessionId!, file),
  })

  const poll = useCallback(async () => {
    if (!sessionId) return
    const data = await playgroundApi.liveTick(sessionId)
    setTick(data)
  }, [sessionId])

  useEffect(() => {
    if (tick?.status === 'playing' && sessionId) {
      pollRef.current = window.setInterval(() => { poll().catch(() => undefined) }, 200)
      return () => { if (pollRef.current) clearInterval(pollRef.current) }
    }
    if (pollRef.current) clearInterval(pollRef.current)
  }, [tick?.status, sessionId, poll])

  const motionLeft = tick?.motion ? { timestamps_ms: tick.motion.timestamps_ms, values: tick.motion.left } : { timestamps_ms: [], values: [] }
  const motionRight = tick?.motion ? { timestamps_ms: tick.motion.timestamps_ms, values: tick.motion.right } : { timestamps_ms: [], values: [] }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <div className="space-y-4">
        <Card>
          <CardHeader><CardTitle className="text-sm">Source</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button size="sm" variant={source === 'csv_playback' ? 'default' : 'secondary'} onClick={() => setSource('csv_playback')}>
              <Radio className="h-3 w-3" /> CSV Playback
            </Button>
            <Button size="sm" variant={source === 'hardware_gloves' ? 'default' : 'secondary'} onClick={() => setSource('hardware_gloves')}>
              <Hand className="h-3 w-3" /> Physical Gloves
            </Button>
          </CardContent>
        </Card>

        {source === 'hardware_gloves' ? (
          <Card className="border-dashed">
            <CardContent className="py-10 text-center text-sm">
              <AlertCircle className="mx-auto h-8 w-8 text-amber-500" />
              <p className="mt-3 font-medium">No device connected</p>
              <p className="mt-2 text-xs text-[var(--color-muted)] max-w-md mx-auto">{status?.hardware_message}</p>
              <p className="mt-2 text-xs text-[var(--color-muted)]">See docs/HARDWARE_CONTRACT.md for the future adapter specification.</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {!sessionId && <Button onClick={() => initSession.mutate()}>Initialize Playback Session</Button>}
            {sessionId && (
              <Card>
                <CardContent className="space-y-3 py-4">
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm">
                    <Upload className="h-4 w-4" /> Upload recording
                    <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && uploadMutation.mutate(e.target.files[0])} />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={() => playgroundApi.liveStart(sessionId).then(poll)}><Play className="h-3 w-3" /> Start</Button>
                    <Button size="sm" variant="secondary" onClick={() => playgroundApi.livePause(sessionId).then(poll)}><Pause className="h-3 w-3" /> Pause</Button>
                    <Button size="sm" variant="secondary" onClick={() => playgroundApi.liveResume(sessionId).then(poll)}>Resume</Button>
                    <Button size="sm" variant="secondary" onClick={() => playgroundApi.liveStop(sessionId).then(poll)}><Square className="h-3 w-3" /> Stop</Button>
                    <Button size="sm" variant="secondary" onClick={() => playgroundApi.liveReset(sessionId).then(poll)}><RotateCcw className="h-3 w-3" /> Reset</Button>
                    <Button size="sm" onClick={() => playgroundApi.liveFinalize(sessionId).then(poll)}>Finalize phrase</Button>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span>Speed</span>
                    <input type="range" min={0.5} max={3} step={0.25} value={speed} onChange={(e) => {
                      const v = Number(e.target.value)
                      setSpeed(v)
                      playgroundApi.liveSpeed(sessionId, v)
                    }} />
                    <span>{speed}×</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {tick && (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <SensorChart title="Left motion" series={motionLeft} color="#4f46e5" />
                  <SensorChart title="Right motion" series={motionRight} color="#0891b2" />
                </div>
                <Card>
                  <CardContent className="py-4 text-sm space-y-2">
                    <div className="flex flex-wrap gap-3 text-xs text-[var(--color-muted)]">
                      <span>Status: <strong>{tick.status}</strong></span>
                      <span>Elapsed: {(tick.elapsed_ms / 1000).toFixed(2)} s</span>
                      <span>Buffer: {tick.buffer_frames} frames</span>
                    </div>
                    {tick.provisional && (
                      <div className="rounded-lg border border-dashed border-indigo-200 bg-indigo-50/50 p-3">
                        <p className="text-xs font-medium text-indigo-800">Provisional prediction</p>
                        <p className="mt-1 font-mono text-sm">{tick.provisional.gloss_sequence.join(' | ')}</p>
                        <p className="mt-1 text-xs text-indigo-600">{tick.provisional.lookahead_note}</p>
                      </div>
                    )}
                    {tick.finalized_messages.map((m, i) => (
                      <div key={i} className="rounded-lg border bg-white p-3">
                        <p className="font-medium">{(m as { english?: string }).english}</p>
                        <p className="text-xs font-mono text-slate-500">{((m as { gloss_sequence?: string[] }).gloss_sequence ?? []).join(' | ')}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </>
            )}
          </>
        )}
      </div>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Live status</CardTitle></CardHeader>
        <CardContent className="text-xs text-[var(--color-muted)] space-y-2">
          <p>Connection: {source === 'csv_playback' ? 'CSV adapter' : status?.hardware_connected ? 'Connected' : 'Not connected'}</p>
          <p>Phrase ending uses sustained rest detection or manual finalize.</p>
        </CardContent>
      </Card>
    </div>
  )
}

function DictionaryTab() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<DictionaryEntry | null>(null)
  const { data: status } = useQuery({ queryKey: ['playground-status'], queryFn: playgroundApi.status })
  const { data: dictionary, error } = useQuery({
    queryKey: ['playground-dictionary'],
    queryFn: () => playgroundApi.dictionary(),
    enabled: !!status?.active_model,
  })

  if (!status?.active_model) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-10 text-center text-sm">
          <BookOpen className="mx-auto h-8 w-8 text-slate-300" />
          <p className="mt-3">Activate a model to explore its vocabulary.</p>
          <Button asChild className="mt-3" variant="secondary"><Link to="/training">Training</Link></Button>
        </CardContent>
      </Card>
    )
  }

  const filtered = dictionary?.entries.filter((e) =>
    e.gloss.toLowerCase().includes(search.toLowerCase()) ||
    e.english_concept.toLowerCase().includes(search.toLowerCase()),
  ) ?? []

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <div>
        <input className="mb-4 w-full rounded-lg border px-3 py-2 text-sm" placeholder="Search gloss vocabulary…" value={search} onChange={(e) => setSearch(e.target.value)} />
        {error && <p className="text-sm text-rose-600">{(error as Error).message}</p>}
        <div className="space-y-2">
          {filtered.map((entry) => (
            <button
              key={entry.gloss}
              type="button"
              className={`w-full rounded-xl border p-4 text-left text-sm transition hover:border-indigo-200 ${selected?.gloss === entry.gloss ? 'border-indigo-400 bg-indigo-50/40' : 'bg-white'}`}
              onClick={() => setSelected(entry)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-indigo-900">{entry.gloss}</span>
                <Badge variant={entry.validation_status === 'prototype_synthetic' ? 'secondary' : 'default'}>
                  {entry.validation_status === 'prototype_synthetic' ? 'Prototype' : 'Real'}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-[var(--color-muted)]">{entry.english_concept} · {entry.support_count} dataset occurrences</p>
            </button>
          ))}
        </div>
        {dictionary && <p className="mt-4 text-xs text-[var(--color-muted)]">{dictionary.disclaimer}</p>}
      </div>
      {selected && (
        <Card>
          <CardHeader><CardTitle>{selected.gloss}</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-3">
            <p className="text-xs text-[var(--color-muted)]">{selected.reliability_note}</p>
            {selected.supported_patterns.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[var(--color-muted)]">Sentence patterns</p>
                <ul className="mt-1 space-y-1 text-xs">
                  {selected.supported_patterns.map((p) => (
                    <li key={p.english}>{p.gloss_sequence.join(' + ')} → {p.english}</li>
                  ))}
                </ul>
              </div>
            )}
            {selected.example_recordings.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[var(--color-muted)]">Example recordings</p>
                <ul className="mt-1 space-y-1">
                  {selected.example_recordings.map((ex) => (
                    <li key={ex.recording_id}>
                      <Link className="text-indigo-700 text-xs hover:underline" to={`/datasets/${ex.dataset_id}/recordings/${ex.recording_id}`}>
                        {ex.recording_id} ({ex.split})
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export function PlaygroundPage() {
  return (
    <div>
      <PageHeader
        title="Playground"
        description="Recognize sign language from sensor recordings — a conversation view of genuine model output, not an LLM chatbot."
      />
      <Tabs defaultValue="recognition">
        <TabsList>
          <TabsTrigger value="recognition">Recognition</TabsTrigger>
          <TabsTrigger value="live">Live Input</TabsTrigger>
          <TabsTrigger value="dictionary">Dictionary</TabsTrigger>
        </TabsList>
        <TabsContent value="recognition"><RecognitionTab /></TabsContent>
        <TabsContent value="live"><LiveInputTab /></TabsContent>
        <TabsContent value="dictionary"><DictionaryTab /></TabsContent>
      </Tabs>
    </div>
  )
}
