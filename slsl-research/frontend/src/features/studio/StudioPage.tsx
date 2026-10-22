import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, AudioLines, BookOpen, CheckCircle2, Database, FlaskConical, Loader2, Play, RotateCcw, Upload, X } from 'lucide-react'
import type { SinhalaResult } from './SinhalaSpeech'
import { ExpressionRuleSettings } from './ExpressionRuleSettings'
import { RecognitionOutput, type SpokenSentence, type ExpressionAnnotation } from './RecognitionOutput'
import { ConfirmAction, Pagination, SearchField, StatusPill, TrainingHistory, UploadField } from './StudioWidgets'
import { maintenanceApi } from '@/services/maintenanceApi'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button } from '@/components/ui/button'
import { playgroundApi } from '@/services/playgroundApi'
import { datasetApi } from '@/services/datasetApi'
import { readApiError } from '@/lib/apiError'

type Page = 'overview' | 'data' | 'train' | 'test' | 'dictionary'
interface Job { id: number; status: string; epoch: number; epochs: number; message: string; loss: number | null }
interface Overview { exact_matches: number; labelled_test_recordings: number; pending_evaluations: number; excluded_evaluations: number; unlabelled_test_recordings: number; sign_error_rate: number | null; accuracy_interval: number[] | null; included_dataset_ids: number[] | null; model: { id: number; name: string; version: string } | null; vocabulary: string[]; training_recordings: number; test_recordings: number; accuracy: number | null; evaluated_recordings: number; jobs: Job[] }
interface TestRecording { id: string; filename: string; frames: number; duration_ms: number; expected_signs: string[]; result: { sinhala?: SinhalaResult; expression?: ExpressionAnnotation; english_display?: string; recognition_id?: string; spoken_sentence?: SpokenSentence; model_id: number; accuracy_excluded_reason?: string | null; predicted_signs: string[]; english: string; text_status: string; uncertain: boolean; inference_ms: number; metrics: { exact_match: boolean; word_error_rate: number } | null } | null }
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/studio${path}`, init)
  if (!response.ok) throw new Error(await readApiError(response))
  return response.json() as Promise<T>
}
const json = (body: unknown) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
const field = 'studio-input mt-2'
const panel = 'studio-panel'
const titles: Record<Page, [string, string]> = {
  overview: ['Overview', 'Add recordings, train your model, and see how it performs on new motion.'],
  data: ['Dataset library', 'Keep labelled training recordings and unseen test recordings in separate collections.'],
  train: ['Training workspace', 'Continue learning using only the collections selected on the Data page.'],
  test: ['Test & recognize', 'Read a motion sequence, see its text output, and check it against an optional answer key.'],
  dictionary: ['Model dictionary', 'Explore the signs currently included in your model’s vocabulary.'],
}

export function StudioPage({ page }: { page: Page }) {
  const qc = useQueryClient()
  const { data: overview, error: overviewError } = useQuery({ queryKey: ['studio-overview'], queryFn: () => api<Overview>('/overview'), refetchInterval: 3000 })
  const { data: datasets = [], error: datasetError } = useQuery({ queryKey: ['datasets'], queryFn: datasetApi.list, enabled: page === 'data' })
  const { data: tests = [], error: testError } = useQuery({ queryKey: ['studio-tests'], queryFn: () => api<TestRecording[]>('/tests'), enabled: page === 'data' || page === 'test' })
  const { data: dictionary, error: dictionaryError } = useQuery({ queryKey: ['studio-dictionary', overview?.model?.id], queryFn: () => playgroundApi.dictionary(overview?.model?.id), enabled: page === 'dictionary' && !!overview?.model })
  const [trainingFiles, setTrainingFiles] = useState<File[]>([])
  const [testFiles, setTestFiles] = useState<File[]>([])
  const [manifest, setManifest] = useState<File | null>(null)
  const [answerKey, setAnswerKey] = useState<File | null>(null)
  const [name, setName] = useState('My training recordings')
  const [epochs, setEpochs] = useState(20)
  const [learningRate, setLearningRate] = useState(.001)
  const [search, setSearch] = useState('')
  const [testSearch, setTestSearch] = useState('')
  const [collectionSearch, setCollectionSearch] = useState('')
  const [listPage, setListPage] = useState(1)
  const [testFilter, setTestFilter] = useState('all')
  const [notice, setNotice] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [session, setSession] = useState<string | null>(null)
  const [liveText, setLiveText] = useState('')
  const [liveElapsed, setLiveElapsed] = useState(0)
  const [predicting, setPredicting] = useState<{ id: string; filename: string } | null>(null)
  const [recognized, setRecognized] = useState<TestRecording | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [spoken, setSpoken] = useState<SpokenSentence | null>(null)
  const [deletingTest, setDeletingTest] = useState(false)
  const liveBusy = useRef(false)
  const action = useMutation({ mutationFn: (run: () => Promise<unknown>) => run(), onSuccess: async () => {
    await qc.invalidateQueries()
  } })
  const busy = action.isPending || deletingTest
  const running = overview?.jobs.find(j => j.status === 'running' || j.status === 'queued')
  const latest = overview?.jobs[0]
  const filteredTests = tests.filter(test => test.filename.toLowerCase().includes(testSearch.toLowerCase()) && (testFilter === 'all' || (testFilter === 'unrun' ? !test.result : !!test.result)))
  const filteredSigns = (overview?.vocabulary || []).filter(sign => sign.toLowerCase().includes(search.toLowerCase()))
  const pageSize = page === 'dictionary' ? 24 : 12
  const totalItems = page === 'dictionary' ? filteredSigns.length : filteredTests.length
  const currentPage = Math.min(listPage, Math.max(1, Math.ceil(totalItems / pageSize)))
  useEffect(() => { setListPage(1); setSearch(''); setTestSearch('') }, [page])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    const timer = window.setInterval(async () => {
      if (liveBusy.current) return
      liveBusy.current = true
      try {
        const tick = await playgroundApi.liveTick(session)
        if (cancelled) return
        setLiveElapsed(tick.elapsed_ms)
        if (tick.provisional) setLiveText(tick.provisional.english || tick.provisional.gloss_sequence.join(' '))
        if (typeof tick.auto_finalized?.english === 'string') setLiveText(tick.auto_finalized.english)
        if (tick.status === 'stopped') { setSession(null); setNotice('Playback complete. The final text is shown below.') }
      } catch (error) { if (!cancelled) { setNotice((error as Error).message); setSession(null) } }
      finally { liveBusy.current = false }
    }, 150)
    return () => { cancelled = true; window.clearInterval(timer); void playgroundApi.liveStop(session).catch(() => {}) }
  }, [session])

  async function upload(kind: 'training' | 'tests') {
    const form = new FormData()
    const files = kind === 'training' ? trainingFiles : testFiles
    files.forEach(file => form.append('files', file))
    if (kind === 'training') { form.append('name', name); if (manifest) form.append('manifest', manifest) }
    else if (answerKey) form.append('answer_key', answerKey)
    const result = await api<{ imported: number; errors?: string[] }>(`/data/${kind}`, { method: 'POST', body: form })
    if (!result.imported) throw new Error(result.errors?.join(' ') || 'No recordings imported. Check the CSV format.')
    if (kind === 'training') { setTrainingFiles([]); setManifest(null) } else { setTestFiles([]); setAnswerKey(null) }
    setNotice(`${result.imported} ${kind === 'training' ? 'training' : 'test'} recordings added.${result.errors?.length ? ' Some files were skipped: ' + result.errors.join(' ') : ''}`)
  }
  async function formSentence(row: TestRecording) {
    if (!row.result?.recognition_id) return
    setAnalyzing(true)
    setSpoken(null)
    try {
      const suggestion = await api<SpokenSentence>(`/tests/${row.id}/sentence`, json({ recognition_id: row.result.recognition_id }))
      setSpoken(suggestion)
      setNotice(suggestion.text ? 'Motion recognized. Your spoken sentence suggestion is ready.' : 'Motion recognized. Check the sentence status above.')
    } catch (error) {
      setSpoken({ text: '', status: 'error', message: (error as Error).message, model_name: 'Local AI', generation_ms: 0 })
    } finally {
      setAnalyzing(false)
    }
  }
  async function recognize(test: TestRecording) {
    setPredicting({ id: test.id, filename: test.filename })
    setRecognized(null)
    setSpoken(null)
    setLiveText('')
    setNotice('')
    try {
      const row = await api<TestRecording>(`/tests/${test.id}/run`, json({}))
      setRecognized(row)
      setPredicting(null)
      // The second request starts only after the motion words are available.
      await formSentence(row)
    } finally {
      setPredicting(null)
    }
  }
  async function deleteTest(test: TestRecording) {
    setDeletingTest(true)
    try {
      await api(`/tests/${test.id}`, { method: 'DELETE' })
      if (recognized?.id === test.id) { setRecognized(null); setSpoken(null); setLiveText('') }
      setNotice(`${test.filename} deleted.`)
      await Promise.all([qc.invalidateQueries({ queryKey: ['studio-tests'] }), qc.invalidateQueries({ queryKey: ['studio-overview'] })])
    } finally { setDeletingTest(false) }
  }
  async function play(test: TestRecording) {
    setRecognized(null); setSpoken(null)
    const response = await fetch(`/api/studio/tests/${test.id}/file`)
    if (!response.ok) throw new Error(await readApiError(response))
    const created = await playgroundApi.createLiveSession('csv_playback')
    await playgroundApi.liveUpload(created.session_id, new File([await response.blob()], test.filename))
    await playgroundApi.liveStart(created.session_id)
    setLiveText('Waiting for enough motion…'); setLiveElapsed(0); setSession(created.session_id)
    setNotice('Playback is running. Text is provisional until the recording ends.')
  }
  function jobs() {
    return <div className="space-y-3">{overview?.jobs.filter(job => job.status === 'running' || job.status === 'queued').map(job => <div key={job.id} className="rounded-xl border border-border p-4">
      <div className="flex items-center justify-between gap-3"><strong className="text-sm">Training session {job.id}</strong><span className="rounded-full bg-surface-muted px-3 py-1 text-xs capitalize">{job.status}</span></div>
      <p className="mt-2 text-sm text-muted">{job.message}</p>
      {(job.status === 'running' || job.status === 'queued') && <progress className="mt-3 w-full" aria-label="Training progress" value={job.epoch} max={job.epochs || 1} />}
      <p className="mt-2 text-xs text-muted">{job.epoch} / {job.epochs} rounds{job.loss != null ? ` · Learning loss ${job.loss.toFixed(3)}` : ''}</p>
    </div>)}</div>
  }

  return <div className="studio-page space-y-6">
    <PageHeader title={titles[page][0]} description={titles[page][1]} />
    {(overviewError || action.error || datasetError || testError || dictionaryError) && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{((action.error || overviewError || datasetError || testError || dictionaryError) as Error).message}</div>}
    {notice && <div role="status" aria-live="polite" className="notice-banner"><CheckCircle2 className="h-4 w-4 shrink-0 text-accent" /><span className="flex-1">{notice}</span><button aria-label="Dismiss notification" onClick={() => setNotice('')}><X className="h-4 w-4" /></button></div>}

    {page === 'overview' && <>
      <div className="studio-hero"><section className="welcome-card"><div className="welcome-orbit" aria-hidden="true" /><span className="eyebrow">YOUR SLSL WORKSPACE</span><h2>A little more learning.<br />A lot more meaning.</h2><p>Turn motion recordings into a growing vocabulary. Your next training session starts here.</p><Button asChild className="mt-6 relative"><Link to={overview?.training_recordings ? '/training' : '/datasets'}>{overview?.training_recordings ? (overview.model ? 'Continue training' : 'Start training') : 'Add your first dataset'}<ArrowRight size={14} /></Link></Button></section><section className="model-card"><div className="flex items-center justify-between"><span className="eyebrow">CURRENT MODEL</span><AudioLines size={22} className="text-[#bdd8a4]" /></div><h2>{overview?.model ? 'SLSL recognition model' : 'Your model starts here'}</h2><p className="mt-2 text-xs text-white/50">{overview?.model ? `Version ${overview.model.version} · Continuous learning` : 'Upload a dataset to begin learning'}</p><div className="mt-6 flex items-center justify-between gap-3 border-t border-white/15 pt-4"><span className="inline-flex items-center gap-2 text-xs text-[#d5edbd]"><span className="h-1.5 w-1.5 rounded-full bg-current" />{running ? 'Training in progress' : overview?.model ? 'Ready for recognition' : 'Waiting for first training'}</span><Link to="/dictionary" aria-label="Open model dictionary"><ArrowRight size={16} /></Link></div></section></div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">{[
        ['Test sequence accuracy', overview?.accuracy == null ? '—' : `${(overview.accuracy * 100).toFixed(1)}%`, `${overview?.exact_matches ?? 0} correct / ${overview?.evaluated_recordings ?? 0} scored · ${overview?.labelled_test_recordings ?? 0} labelled tests`, FlaskConical],
        ['Model vocabulary', String(overview?.vocabulary.length ?? 0), 'signs learned so far', BookOpen],
        ['Training recordings', (overview?.training_recordings ?? 0).toLocaleString(), 'in selected collections', Database],
        ['Test recordings', (overview?.test_recordings ?? 0).toLocaleString(), 'ready to check recognition', CheckCircle2],
      ].map(([label,value,detail,Icon]) => { const Symbol = Icon as typeof Database; return <section key={String(label)} className={`${panel} metric-card`}><div className="flex items-center justify-between gap-2"><p className="metric-label">{String(label)}</p><span className="metric-icon"><Symbol size={15} /></span></div><p className="metric-value">{String(value)}</p><p className="mt-2 text-[10px] text-muted">{String(detail)}</p></section> })}</div>
      <section className={panel}><h2 className="font-semibold">Test coverage · current model</h2><p className="mt-2 text-sm text-muted">{overview?.evaluated_recordings ?? 0} scored of {overview?.labelled_test_recordings ?? 0} labelled recordings · {overview?.pending_evaluations ?? 0} need testing · {overview?.excluded_evaluations ?? 0} excluded · {overview?.unlabelled_test_recordings ?? 0} without answers.</p>{overview?.accuracy_interval && <p className="mt-2 text-xs text-muted">Approximate 95% interval (assuming independent tests): {(overview.accuracy_interval[0]*100).toFixed(1)}–{(overview.accuracy_interval[1]*100).toFixed(1)}%. Sign error rate: {((overview.sign_error_rate ?? 0)*100).toFixed(1)}%.</p>}<p className="mt-2 text-xs text-muted">This score describes the evaluated CSVs, not overall SLSL or real-glove accuracy. A small or easy synthetic test set can score 100%. Run all labelled tests for broader coverage; test new timing and motion variations separately.</p><Link to="/test" className="mt-3 inline-block text-xs font-medium text-accent">Open tests →</Link></section>
      <section className={panel}><div className="mb-5 flex items-center justify-between"><div><p className="eyebrow">A SIMPLE WORKFLOW</p><h2 className="mt-1 text-lg font-semibold">From recordings to recognition</h2></div><span className="hidden text-xs text-muted sm:block">Three steps. One growing model.</span></div><div className="grid gap-3 lg:grid-cols-3">{[
        ['/datasets','Add recordings','Organize your training and test CSVs.'],
        ['/training','Train the model','Build on what it already knows.'],
        ['/test','Test recognition','See predictions and measure results.'],
      ].map(([to,title,description], index) => <Link key={to} to={to} className="workflow-step"><span className="step-number">0{index+1}</span><div className="flex-1"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1.5 text-[11px] leading-5 text-muted">{description}</p></div><ArrowRight size={14} className="mt-2 text-muted" /></Link>)}</div></section>
      {latest && <section className={panel}><div className="flex items-center justify-between"><div><p className="eyebrow">LATEST ACTIVITY</p><h2 className="mt-2 font-semibold">Training session #{latest.id}</h2></div><StatusPill status={latest.status} /></div><p className="mt-3 text-sm text-muted">{latest.message}</p><Link to="/training" className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-accent">View training history <ArrowRight size={13} /></Link></section>}
    </>}

    {page === 'data' && <>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className={panel}><Upload className="h-5 w-5 text-accent" /><h2 className="mt-3 text-lg font-semibold">Training recordings</h2><p className="mt-2 text-sm text-muted">CSV motion frames with an ordered meaning, such as I|NEED|WATER. Each recording is kept together.</p>
          <label className="mt-5 block text-sm" htmlFor="dataset-name">Collection name</label><input id="dataset-name" className={field} value={name} onChange={e => setName(e.target.value)} />
          <UploadField label="Labelled motion CSVs" files={trainingFiles} onChange={setTrainingFiles} multiple />
          <details className="mt-4 text-sm"><summary className="cursor-pointer text-muted">Use a separate label manifest instead</summary><UploadField label="Label manifest" optional files={manifest ? [manifest] : []} onChange={files => setManifest(files[0] || null)} /></details>
          <Button className="mt-5" disabled={busy || !trainingFiles.length} onClick={() => action.mutate(() => upload('training'))}>Add training recordings</Button>
        </section>
        <section className={panel}><CheckCircle2 className="h-5 w-5 text-accent" /><h2 className="mt-3 text-lg font-semibold">Test recordings</h2><p className="mt-2 text-sm text-muted">Upload unseen motion-only CSVs. These files are never used to train the model.</p>
          <UploadField label="Motion-only CSVs" files={testFiles} onChange={setTestFiles} multiple />
          <UploadField label="Answer key CSV" optional files={answerKey ? [answerKey] : []} onChange={files => setAnswerKey(files[0] || null)} /><p className="mt-2 text-xs text-muted">Columns: recording_id, ordered_sign_labels. Match recording_id to the test filename without .csv. Answers are used only to score predictions.</p>
          <Button className="mt-5" disabled={busy || !testFiles.length} onClick={() => action.mutate(() => upload('tests'))}>Add test recordings</Button>
        </section>
      </div>
      <details className={panel}><summary className="cursor-pointer font-medium">CSV format & examples</summary><p className="mt-3 text-sm text-muted">Use timestamp_ms, five normalized flex values, acceleration XYZ in g, and gyroscope XYZ in degrees/second for each hand: 23 motion columns in total. Training files also include ordered_sign_labels; use | between signs. A recording_id column lets one training CSV contain multiple recordings. Meanings are removed before model input.</p><p className="mt-3 text-sm text-muted">Use the same sensor units for generated and glove recordings. Labelled tests are optional; without answers, the app shows predictions rather than an accuracy score.</p></details>
      <section className={panel}><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">Training collections <span className="count-badge">{datasets.length}</span></h2><SearchField value={collectionSearch} onChange={setCollectionSearch} placeholder="Find a collection…" /></div><p className="mt-2 text-xs text-muted">Checked collections are included in training. After resetting, uncheck earlier practice collections before training on glove recordings.</p>{!datasets.length ? <p className="mt-4 text-sm text-muted">Your first collection will appear here.</p> : <div className="mt-4 divide-y divide-border">{datasets.filter(d => d.name.toLowerCase().includes(collectionSearch.toLowerCase())).map(d => <div key={d.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><label className="flex items-center gap-3"><input type="checkbox" disabled={busy || !!running} checked={overview?.included_dataset_ids == null || overview.included_dataset_ids.includes(d.id)} onChange={e => {
        // Capture the choice before React restores this controlled input.
        const checked = e.currentTarget.checked
        const availableIds = new Set(datasets.map(item => item.id))
        const included = (overview?.included_dataset_ids ?? [...availableIds]).filter(id => availableIds.has(id))
        const datasetIds = checked ? [...new Set([...included, d.id])] : included.filter(id => id !== d.id)
        action.mutate(async () => {
          const saved = await api<{ dataset_ids: number[] }>('/collections', json({ dataset_ids: datasetIds }))
          qc.setQueryData<Overview>(['studio-overview'], previous => previous ? { ...previous, included_dataset_ids: saved.dataset_ids } : previous)
          setNotice('Training selection saved. Only checked collections will be used.')
        })
      }} />{d.name}</label><div className="flex items-center gap-3"><span className="text-xs text-muted">{d.recording_count} recordings</span><ConfirmAction compact title={`Delete ${d.name}?`} description="Permanently delete this collection and its recording files. Collections linked to a model cannot be removed here until those models are archived." label="Delete collection" phrase={d.provenance === 'real' ? `DELETE ${d.name}` : `DELETE ${d.id}`} disabled={busy || !!running} run={() => maintenanceApi.deleteDataset(d.id, d.provenance === 'real' ? `DELETE ${d.name}` : `DELETE ${d.id}`)} /></div></div>)}</div>}<p className="mt-4 text-sm text-muted">{tests.length} test recordings stored separately.</p></section>
    </>}

    {page === 'train' && <>
      <section className={panel}><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-wider text-accent">One model · continuous learning</p><h2 className="mt-2 text-xl font-semibold">{overview?.model ? 'Keep your model learning' : 'Train your first model'}</h2><p className="mt-3 max-w-2xl text-sm text-muted">All selected training collections are included. The app preserves learned weights and vocabulary, adds new signs, and keeps validation and test recordings out of training.</p></div><BookOpen className="h-6 w-6 shrink-0 text-accent" /></div>
        <details className="mt-5 rounded-xl bg-surface-muted p-4"><summary className="cursor-pointer text-sm font-medium">Training settings</summary><div className="mt-4 grid max-w-lg gap-4 sm:grid-cols-2"><label className="text-sm" htmlFor="epochs">Training rounds<input id="epochs" type="number" min="1" max="100" value={epochs} className={field} onChange={e => setEpochs(Number(e.target.value))} /></label><label className="text-sm" htmlFor="learning-rate">Learning rate<input id="learning-rate" type="number" min="0.000001" max="0.1" step="0.0001" value={learningRate} className={field} onChange={e => setLearningRate(Number(e.target.value))} /></label></div></details>
        <div className="mt-6 flex flex-wrap items-center gap-3"><Button disabled={busy || !!running || !overview?.training_recordings} onClick={() => action.mutate(async () => { await api('/train', json({ epochs, learning_rate: learningRate })); setNotice('Training started. You can follow its progress below.') })}><Play className="h-4 w-4" />{running ? 'Training in progress' : 'Train Model'}</Button>{running && <Button variant="secondary" disabled={busy} onClick={() => action.mutate(async () => { const response = await fetch(`/api/training/jobs/${running.id}/cancel`,{method:'POST'}); if(!response.ok) throw new Error(await readApiError(response)); setNotice('Training stopped. Your previous model is preserved.') })}>Stop training</Button>}</div>
        <p className="mt-3 text-xs text-muted">More training does not guarantee better accuracy. Check new recordings after each session.</p>
      </section>
      {running && <section className={panel}><h2 className="mb-4 font-semibold">Live training progress</h2>{jobs()}</section>}<TrainingHistory />
      <details className={panel}><summary className="cursor-pointer text-sm font-medium">Start over</summary><p className="mt-3 text-sm text-muted">Reset learned weights and vocabulary. Recordings are kept, and previous checkpoints are archived. Type RESET to confirm.</p><label htmlFor="reset-model" className="sr-only">Reset confirmation</label><input id="reset-model" className={`${field} max-w-xs`} value={confirmation} onChange={e => setConfirmation(e.target.value)} /><Button className="ml-3 mt-3" variant="secondary" disabled={busy || !!running || confirmation !== 'RESET'} onClick={() => action.mutate(async () => { await api('/reset',json({confirmation})); setConfirmation(''); setNotice('Model reset. Choose the training collections for your next experiment before training again.') })}><RotateCcw className="h-4 w-4" />Reset model</Button></details>
    </>}

    {page === 'test' && <>
      <RecognitionOutput speechTarget={recognized?.result?.recognition_id ? { testId: recognized.id, recognitionId: recognized.result.recognition_id } : null} predicting={predicting} words={recognized?.result?.predicted_signs ?? null} expression={recognized?.result?.expression} analyzing={analyzing} suggestion={spoken} liveText={liveText} playing={!!session} elapsed={liveElapsed} disabled={busy || !!session} onRetry={() => { if (recognized) action.mutate(() => formSentence(recognized)) }} />
      <ExpressionRuleSettings disabled={busy || !!session} />
      <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-sm text-muted">{tests.length} test recordings · {overview?.evaluated_recordings ?? 0}/{overview?.labelled_test_recordings ?? 0} labelled tests scored · {overview?.pending_evaluations ?? 0} pending for this model</p><Button variant="secondary" disabled={busy || !!session || !overview?.model || !tests.length} onClick={() => action.mutate(async () => { for (const test of tests) await api(`/tests/${test.id}/run`,json({})); setNotice('All test recordings checked.') })} title="Scores motion recognition only. Use Recognize on a recording for a sentence suggestion.">Run all tests</Button></div>
      {!!tests.length && <div className="flex flex-wrap items-center gap-3"><SearchField value={testSearch} onChange={value => { setTestSearch(value); setListPage(1) }} placeholder="Search test recordings…" /><label className="text-xs text-muted">Show <select className="ml-2 rounded-lg border border-border bg-surface px-3 py-2" value={testFilter} onChange={e => { setTestFilter(e.target.value); setListPage(1) }}><option value="all">All recordings</option><option value="unrun">Not tested yet</option><option value="run">With results</option></select></label><span className="ml-auto text-xs text-muted">{filteredTests.length} recordings</span></div>}
      {!tests.length && <section className={panel}><p className="text-sm text-muted">Add test recordings on the Data page to get started.</p><Link className="mt-3 inline-block text-sm text-accent" to="/datasets">Add test recordings →</Link></section>}
      {!!tests.length && !filteredTests.length && <section className={`${panel} empty-state`}><FlaskConical className="h-8 w-8 text-muted" /><h3>No matching recordings</h3><p>Try another search or change the results filter.</p></section>}
      {filteredTests.slice((currentPage - 1) * pageSize, currentPage * pageSize).map(test => <section key={test.id} className={panel}><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="font-semibold">{test.filename}</h2><p className="mt-1 text-xs text-muted">{test.frames} frames · {(test.duration_ms/1000).toFixed(1)} seconds · {test.expected_signs.length ? 'Answer key available' : 'Prediction only'}</p></div><div className="flex gap-2"><Button size="sm" variant="secondary" disabled={busy || !!session || !overview?.model} onClick={() => action.mutate(() => play(test))}>Play motion</Button><Button size="sm" disabled={busy || !!session || !overview?.model} onClick={() => action.mutate(() => recognize(test))} aria-busy={predicting?.id === test.id || (analyzing && recognized?.id === test.id)}>{predicting?.id === test.id || (analyzing && recognized?.id === test.id) ? <><Loader2 aria-hidden="true" className="h-3.5 w-3.5 animate-spin motion-reduce:animate-none" />{analyzing ? 'Forming sentence…' : 'Predicting…'}</> : 'Recognize'}</Button><ConfirmAction compact title={`Delete ${test.filename}?`} description="Delete this test motion file, its answer key and prediction results. This also removes its contribution to test accuracy. Your trained model is kept." label="Delete test recording" disabled={busy || !!session} run={() => deleteTest(test)} /></div></div>
        {test.result && predicting?.id !== test.id && <div className="mt-4 rounded-xl bg-surface-muted p-4 text-sm"><p className="font-medium">{test.result.spoken_sentence?.display_text || test.result.spoken_sentence?.text || test.result.english_display || test.result.english || 'No signs recognized'}</p>{test.result.sinhala?.text && <p lang="si" className="mt-2 text-base">{test.result.sinhala.text}</p>}{test.result.sinhala?.speech && test.result.model_id === overview?.model?.id && <audio aria-label={`Sinhala audio for ${test.filename}`} controls preload="none" className="mt-3 w-full max-w-md" src={test.result.sinhala.speech.audio_url} />}{test.result.spoken_sentence?.text && <p className="mt-1 text-[10px] text-muted">{test.result.spoken_sentence.status === 'fallback' ? 'Word-based fallback' : 'Local AI sentence suggestion'}</p>}<p className="mt-2 text-xs text-muted">Signs: {test.result.predicted_signs.join(' → ') || 'None'} · {test.result.inference_ms.toFixed(0)} ms</p>{test.result.model_id !== overview?.model?.id && <p className="mt-2 text-xs text-amber-800">From an earlier model version. Run again to check the current model.</p>}{test.result.accuracy_excluded_reason && <p className="mt-2 text-xs text-amber-800">{test.result.accuracy_excluded_reason}</p>}{test.result.expression?.label === 'angry' && <p className="mt-2 text-xs text-rose-800">Angry word rule · {test.result.expression.matched_words.join(', ')}</p>}{test.result.uncertain && <p className="mt-2 text-xs text-amber-800">Uncertain recognition—try another recording.</p>}{test.result.metrics && <p className="mt-2 text-xs">{test.result.metrics.exact_match ? 'Sequence matched' : 'Sequence differs'} · Sign error rate {(test.result.metrics.word_error_rate*100).toFixed(1)}% · Expected: {test.expected_signs.join(' → ')}</p>}</div>}
      </section>)}
      {!!tests.length && <Pagination page={currentPage} total={filteredTests.length} size={pageSize} onChange={setListPage} />}
    </>}

    {page === 'dictionary' && <><div className="flex flex-wrap items-center justify-between gap-4"><SearchField value={search} onChange={value => { setSearch(value); setListPage(1) }} placeholder="Search the model dictionary…" /><p className="text-xs text-muted">{overview?.vocabulary.length ?? 0} signs in your model</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{filteredSigns.slice((currentPage - 1) * pageSize, currentPage * pageSize).map(sign => { const entry = dictionary?.entries.find(e => e.gloss === sign); return <section key={sign} className={`${panel} dictionary-card`}><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft"><BookOpen className="h-4 w-4 text-accent" /></span><div><h2 className="font-semibold">{sign}</h2><p className="text-[10px] text-muted">{entry?.support_count ?? '—'} recording examples</p></div></section> })}</div>{!filteredSigns.length && <section className={`${panel} empty-state`}><BookOpen className="h-8 w-8 text-muted" /><h3>{search ? 'No matching signs' : 'Your vocabulary starts here'}</h3><p>{search ? 'Try another word or clear your search.' : 'Train your model to add its first signs.'}</p></section>}<Pagination page={currentPage} total={filteredSigns.length} size={pageSize} onChange={setListPage} /><p className="text-[11px] text-muted">Vocabulary inclusion does not establish recognition accuracy.</p></>}
  </div>
}
