import { useEffect, useMemo, useState } from 'react'
import {
  CheckCircle2,
  Clock3,
  Download,
  Edit3,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  ShieldCheck,
  Wand2,
  XCircle,
} from 'lucide-react'
import './App.css'
import {
  createProject,
  editSegment,
  getProject,
  listProjects,
  markdownExportUrl,
  regenerateSegment,
  signOffProject,
} from './api'
import type { InstructorBrief, ScriptProject, SegmentDraft, SegmentOutline } from './types'

const initialBrief: InstructorBrief = {
  topic: '',
  agenda: [],
  beginner_percentage: 70,
  advanced_percentage: 30,
  duration_minutes: 90,
  content_percentage: 60,
  code_percentage: 40,
  topics_already_covered: [],
}

const exampleTopic = 'Indexing in PostgreSQL'
const exampleAgenda = [
  'Why indexes exist',
  'B-tree index mechanics',
  'Reading EXPLAIN plans',
  'Choosing indexes for common queries',
].join('\n')
const exampleCoveredTopics = ['basic SQL', 'primary keys'].join('\n')

function App() {
  const [brief, setBrief] = useState<InstructorBrief>(initialBrief)
  const [agendaText, setAgendaText] = useState(initialBrief.agenda.join('\n'))
  const [coveredTopicsText, setCoveredTopicsText] = useState(initialBrief.topics_already_covered.join('\n'))
  const [project, setProject] = useState<ScriptProject | null>(null)
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [projects, setProjects] = useState<ScriptProject[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void refreshProjects()
  }, [])

  useEffect(() => {
    if (!project || selectedSegmentId || project.segments.length === 0) return
    setSelectedSegmentId(project.segments[0].id)
  }, [project, selectedSegmentId])

  const selectedSegment = project?.segments.find((segment) => segment.id === selectedSegmentId) ?? null
  const selectedOutline = project?.outline?.segments.find(
    (outline) => outline.id === selectedSegment?.outline_id,
  ) ?? null

  async function submitBrief() {
    setSubmitting(true)
    setError(null)
    try {
      const created = await createProject(brief)
      setProject(created)
      setSelectedSegmentId(null)
      await refreshProjects()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  async function refreshProjects() {
    setLoadingProjects(true)
    try {
      setProjects(await listProjects())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoadingProjects(false)
    }
  }

  async function openProject(projectId: string) {
    setError(null)
    const loaded = await getProject(projectId)
    setProject(loaded)
    setSelectedSegmentId(loaded.segments[0]?.id ?? null)
  }

  function startNewProject() {
    setProject(null)
    setSelectedSegmentId(null)
  }

  async function refreshProject() {
    if (!project) return
    const refreshed = await getProject(project.id)
    setProject(refreshed)
    await refreshProjects()
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Scaler assignment</p>
          <h1>Class Script Authoring Pipeline</h1>
        </div>
        {project && (
          <div className="topbar-actions">
            <StatusBadge status={project.generation_status} />
            <a className="button secondary" href={markdownExportUrl(project.id)}>
              <Download size={16} /> Export
            </a>
          </div>
        )}
      </header>

      {error && <div className="error-banner">{error}</div>}

      {!project ? (
        <BriefForm
          brief={brief}
          setBrief={setBrief}
          agendaText={agendaText}
          setAgendaText={setAgendaText}
          coveredTopicsText={coveredTopicsText}
          setCoveredTopicsText={setCoveredTopicsText}
          submitting={submitting}
          projects={projects}
          loadingProjects={loadingProjects}
          onRefreshProjects={refreshProjects}
          onOpenProject={openProject}
          onSubmit={submitBrief}
        />
      ) : (
        <div className="workspace">
          <aside className="left-rail">
            <ProjectBrowser
              projects={projects}
              activeProjectId={project.id}
              loading={loadingProjects}
              onRefresh={refreshProjects}
              onOpen={openProject}
              onNew={startNewProject}
            />
            <ProjectProgress project={project} onRefresh={refreshProject} />
            <SegmentList
              project={project}
              selectedSegmentId={selectedSegmentId}
              onSelect={setSelectedSegmentId}
            />
          </aside>
          <section className="main-panel">
            {selectedSegment && selectedOutline ? (
              <SegmentPanel
                project={project}
                segment={selectedSegment}
                outline={selectedOutline}
                onProjectChange={setProject}
                onSelectSegment={setSelectedSegmentId}
              />
            ) : (
              <OutlineWaiting project={project} />
            )}
          </section>
          <aside className="right-rail">
            <EvaluationPanel project={project} />
            <SignOffPanel
              project={project}
              onProjectChange={(updatedProject) => {
                setProject(updatedProject)
                void refreshProjects()
              }}
            />
            <ReviewHistory project={project} />
          </aside>
        </div>
      )}
    </main>
  )
}

function ProjectBrowser({
  projects,
  activeProjectId,
  loading,
  onRefresh,
  onOpen,
  onNew,
}: {
  projects: ScriptProject[]
  activeProjectId: string | null
  loading: boolean
  onRefresh: () => void
  onOpen: (id: string) => void
  onNew?: () => void
}) {
  const signedOffProjects = projects.filter((candidate) => candidate.sign_off)
  const unsignedProjects = projects.filter((candidate) => !candidate.sign_off)
  const orderedProjects = [...signedOffProjects, ...unsignedProjects]

  return (
    <div className="panel project-browser">
      <div className="panel-title-row">
        <h2>Projects</h2>
        <div className="toolbar-actions">
          <button className="icon-button" type="button" onClick={onRefresh} title="Refresh projects">
            {loading ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}
          </button>
          {onNew && (
            <button className="icon-button" type="button" onClick={onNew} title="New project">
              <FileText size={15} />
            </button>
          )}
        </div>
      </div>
      {orderedProjects.length === 0 ? (
        <p className="muted">Saved projects will appear here.</p>
      ) : (
        <div className="project-list">
          {orderedProjects.map((candidate) => (
            <button
              className={`project-row ${candidate.id === activeProjectId ? 'active' : ''}`}
              type="button"
              key={candidate.id}
              onClick={() => onOpen(candidate.id)}
            >
              <span>
                <strong>{candidate.brief.topic}</strong>
                <small>{candidate.id}</small>
              </span>
              {candidate.sign_off ? (
                <span className="project-pill approved">Signed off</span>
              ) : (
                <span className="project-pill">{candidate.review_status.replaceAll('_', ' ')}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function BriefForm({
  brief,
  setBrief,
  agendaText,
  setAgendaText,
  coveredTopicsText,
  setCoveredTopicsText,
  submitting,
  projects,
  loadingProjects,
  onRefreshProjects,
  onOpenProject,
  onSubmit,
}: {
  brief: InstructorBrief
  setBrief: (brief: InstructorBrief) => void
  agendaText: string
  setAgendaText: (text: string) => void
  coveredTopicsText: string
  setCoveredTopicsText: (text: string) => void
  submitting: boolean
  projects: ScriptProject[]
  loadingProjects: boolean
  onRefreshProjects: () => void
  onOpenProject: (id: string) => void
  onSubmit: () => void
}) {
  return (
    <section className="brief-grid">
      <div className="form-panel">
        <div className="section-heading">
          <FileText size={18} />
          <h2>Instructor brief</h2>
        </div>
        <label>
          Topic
          <input
            value={brief.topic}
            placeholder={exampleTopic}
            onChange={(event) => setBrief({ ...brief, topic: event.target.value })}
          />
        </label>
        <label>
          Agenda
          <textarea
            rows={6}
            value={agendaText}
            placeholder={exampleAgenda}
            onChange={(event) => {
              setAgendaText(event.target.value)
              setBrief({ ...brief, agenda: parseMultilineList(event.target.value) })
            }}
          />
        </label>
        <label>
          Topics already covered
          <textarea
            rows={3}
            value={coveredTopicsText}
            placeholder={exampleCoveredTopics}
            onChange={(event) => {
              setCoveredTopicsText(event.target.value)
              setBrief({
                ...brief,
                topics_already_covered: parseMultilineList(event.target.value),
              })
            }}
          />
        </label>
      </div>
      <div className="form-panel">
        <div className="section-heading">
          <Clock3 size={18} />
          <h2>Constraints</h2>
        </div>
        <div className="two-col">
          <NumberInput label="Beginner %" value={brief.beginner_percentage} onChange={(value) => setBrief({ ...brief, beginner_percentage: value })} />
          <NumberInput label="Advanced %" value={brief.advanced_percentage} onChange={(value) => setBrief({ ...brief, advanced_percentage: value })} />
          <NumberInput label="Duration" value={brief.duration_minutes} min={5} max={240} onChange={(value) => setBrief({ ...brief, duration_minutes: value })} />
          <NumberInput label="Content %" value={brief.content_percentage} onChange={(value) => setBrief({ ...brief, content_percentage: value })} />
          <NumberInput label="Code %" value={brief.code_percentage} onChange={(value) => setBrief({ ...brief, code_percentage: value })} />
        </div>
        <button
          className="button primary wide"
          type="button"
          onClick={onSubmit}
          disabled={submitting || brief.topic.trim().length < 3 || brief.agenda.length === 0}
        >
          {submitting ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
          {submitting ? 'Generating and evaluating...' : 'Generate script'}
        </button>
        <ProjectBrowser
          projects={projects}
          activeProjectId={null}
          loading={loadingProjects}
          onRefresh={onRefreshProjects}
          onOpen={onOpenProject}
        />
      </div>
    </section>
  )
}

function parseMultilineList(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function NumberInput({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min?: number
  max?: number
  onChange: (value: number) => void
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function ProjectProgress({ project, onRefresh }: { project: ScriptProject; onRefresh: () => void }) {
  return (
    <div className="panel compact">
      <div className="panel-title-row">
        <h2>Generation</h2>
        <button className="icon-button" type="button" onClick={onRefresh} title="Refresh project">
          <RefreshCw size={15} />
        </button>
      </div>
      <div className="progress-bar">
        <span style={{ width: `${project.generation_progress}%` }} />
      </div>
      <p className="muted">{project.generation_message}</p>
      {project.generation_error && <p className="danger">{project.generation_error}</p>}
    </div>
  )
}

function SegmentList({
  project,
  selectedSegmentId,
  onSelect,
}: {
  project: ScriptProject
  selectedSegmentId: string | null
  onSelect: (id: string) => void
}) {
  const rows = project.outline?.segments ?? []
  return (
    <div className="panel segments-panel">
      <h2>Segments</h2>
      {rows.length === 0 && <p className="muted">Outline segments will appear here.</p>}
      {rows.map((outline) => {
        const draft = project.segments.find((segment) => segment.outline_id === outline.id)
        const isSelected = draft?.id === selectedSegmentId
        return (
          <button
            key={outline.id}
            className={`segment-row ${isSelected ? 'active' : ''}`}
            type="button"
            disabled={!draft}
            onClick={() => draft && onSelect(draft.id)}
          >
            <span className="segment-index">{outline.order}</span>
            <span>
              <strong>{outline.title}</strong>
              <small>{outline.duration_minutes} min</small>
            </span>
            {draft ? <CheckCircle2 size={15} /> : <Loader2 className="spin" size={15} />}
          </button>
        )
      })}
    </div>
  )
}

function SegmentPanel({
  project,
  segment,
  outline,
  onProjectChange,
  onSelectSegment,
}: {
  project: ScriptProject
  segment: SegmentDraft
  outline: SegmentOutline
  onProjectChange: (project: ScriptProject) => void
  onSelectSegment: (segmentId: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draftText, setDraftText] = useState(segment.instructor_narration)
  const [feedback, setFeedback] = useState('')
  const [regenInstruction, setRegenInstruction] = useState('')
  const [busy, setBusy] = useState(false)
  const isSignedOff = Boolean(project.sign_off)
  const currentSegmentIndex = project.segments.findIndex((candidate) => candidate.id === segment.id)
  const previousSegment = currentSegmentIndex > 0 ? project.segments[currentSegmentIndex - 1] : null
  const nextSegment =
    currentSegmentIndex >= 0 && currentSegmentIndex < project.segments.length - 1
      ? project.segments[currentSegmentIndex + 1]
      : null

  useEffect(() => setDraftText(segment.instructor_narration), [segment.id, segment.version])
  useEffect(() => {
    if (isSignedOff) setEditing(false)
  }, [isSignedOff])

  async function saveEdit() {
    setBusy(true)
    try {
      onProjectChange(await editSegment(project.id, segment.id, draftText, feedback))
      setEditing(false)
      setFeedback('')
    } finally {
      setBusy(false)
    }
  }

  async function runRegeneration() {
    setBusy(true)
    try {
      onProjectChange(await regenerateSegment(project.id, segment.id, regenInstruction, feedback))
      setRegenInstruction('')
      setFeedback('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="segment-detail">
      <div className="segment-header">
        <div>
          <p className="eyebrow">Segment {outline.order}</p>
          <h2>{outline.title}</h2>
          <p className="muted">{outline.learning_objective}</p>
        </div>
        <div className="metric-row">
          <Metric label="Total" value={`${segment.duration_minutes}m`} />
          <Metric label="Content" value={`${segment.content_minutes}m`} />
          <Metric label="Code" value={`${segment.code_minutes}m`} />
          <Metric label="Version" value={`v${segment.version}`} />
        </div>
      </div>

      <div className="outline-strip">
        <p><strong>Strategy:</strong> {outline.teaching_strategy}</p>
        <p><strong>Rationale:</strong> {outline.rationale}</p>
      </div>

      <section className="script-block">
        <div className="panel-title-row">
          <h3>Instructor narration</h3>
          <button
            className="button secondary"
            type="button"
            onClick={() => setEditing(!editing)}
            disabled={isSignedOff}
            title={isSignedOff ? 'Signed-off scripts are locked' : 'Edit narration'}
          >
            <Edit3 size={15} /> {editing ? 'Cancel' : 'Edit'}
          </button>
        </div>
        {editing ? (
          <>
            <textarea rows={14} value={draftText} onChange={(event) => setDraftText(event.target.value)} />
            <input
              placeholder="Optional edit note"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
            />
            <button className="button primary" type="button" onClick={saveEdit} disabled={busy}>
              Save edit
            </button>
          </>
        ) : (
          <InlineScript segment={segment} />
        )}
      </section>

      <div className="segment-navigation">
        <button
          className="button secondary"
          type="button"
          disabled={!previousSegment}
          onClick={() => previousSegment && onSelectSegment(previousSegment.id)}
        >
          Previous segment
        </button>
        <button
          className="button secondary"
          type="button"
          disabled={!nextSegment}
          onClick={() => nextSegment && onSelectSegment(nextSegment.id)}
        >
          Next segment
        </button>
      </div>

      <section className="script-block">
        <h3>Regenerate this segment</h3>
        {isSignedOff && <p className="muted">This script is signed off, so segment regeneration is locked.</p>}
        <textarea
          rows={3}
          placeholder="Example: make this more beginner-friendly and add a concrete analogy."
          value={regenInstruction}
          onChange={(event) => setRegenInstruction(event.target.value)}
          disabled={isSignedOff}
        />
        <button
          className="button primary"
          type="button"
          onClick={runRegeneration}
          disabled={isSignedOff || busy || regenInstruction.length < 3}
          title={isSignedOff ? 'Signed-off scripts are locked' : 'Regenerate this segment'}
        >
          {busy ? <Loader2 className="spin" size={16} /> : <Wand2 size={16} />} Regenerate
        </button>
      </section>
    </article>
  )
}

function InlineScript({ segment }: { segment: SegmentDraft }) {
  const codeSteps = [...segment.live_code_steps]
  const checks = [...segment.checks]
  const activities = [...segment.activities]
  const markerPattern = /(\[(?:CODE_STEP|CODE SNIPPET|CHECKPOINT|ACTIVITY)\])/gi
  const parts = segment.instructor_narration.split(markerPattern)
  const renderedMarkers = {
    code: 0,
    checks: 0,
    activities: 0,
  }

  const blocks = parts.flatMap((part, index) => {
    const marker = part.toUpperCase()
    if (marker === '[CODE_STEP]' || marker === '[CODE SNIPPET]') {
      const step = codeSteps.shift()
      if (!step) return []
      renderedMarkers.code += 1
      return [<LiveCodeBlock step={step} key={`code-${index}`} />]
    }
    if (marker === '[CHECKPOINT]') {
      const check = checks.shift()
      if (!check) return []
      renderedMarkers.checks += 1
      return [<CheckpointBlock check={check} key={`check-${index}`} />]
    }
    if (marker === '[ACTIVITY]') {
      const activity = activities.shift()
      if (!activity) return []
      renderedMarkers.activities += 1
      return [<ActivityBlock activity={activity} key={`activity-${index}`} />]
    }
    if (!part.trim()) return []
    return [
      <p className="narration" key={`text-${index}`}>
        {part.trim()}
      </p>,
    ]
  })

  return (
    <div className="inline-script">
      {blocks}
      {codeSteps.map((step) => <LiveCodeBlock step={step} key={`remaining-code-${step.order}`} />)}
      {checks.map((check) => <CheckpointBlock check={check} key={`remaining-check-${check.question}`} />)}
      {activities.map((activity) => <ActivityBlock activity={activity} key={`remaining-activity-${activity.prompt}`} />)}
      {renderedMarkers.code + renderedMarkers.checks + renderedMarkers.activities === 0 &&
        segment.live_code_steps.length + segment.checks.length + segment.activities.length > 0 && (
          <p className="muted">Structured items are shown after the narration because this segment has no inline markers yet.</p>
        )}
    </div>
  )
}

function LiveCodeBlock({ step }: { step: SegmentDraft['live_code_steps'][number] }) {
  return (
    <div className="subcard inline-block">
      <span className="block-label">Live code</span>
      <strong>{step.order}. {step.instruction}</strong>
      {step.code && <pre>{step.code}</pre>}
      <p>{step.explanation}</p>
      {step.expected_output && <p className="muted">Expected output: {step.expected_output}</p>}
    </div>
  )
}

function CheckpointBlock({ check }: { check: SegmentDraft['checks'][number] }) {
  return (
    <div className="subcard inline-block checkpoint-block">
      <span className="block-label">Checkpoint</span>
      <strong>{check.question}</strong>
      <p>{check.instructor_guidance}</p>
      <p className="muted">Expected: {check.expected_answer}</p>
    </div>
  )
}

function ActivityBlock({ activity }: { activity: SegmentDraft['activities'][number] }) {
  return (
    <div className="subcard inline-block checkpoint-block">
      <span className="block-label">{activity.type.replaceAll('_', ' ')}</span>
      <strong>{activity.prompt}</strong>
      <p>{activity.facilitation_notes}</p>
      <p className="muted">Expected: {activity.expected_response}</p>
    </div>
  )
}

function EvaluationPanel({ project }: { project: ScriptProject }) {
  const evaluation = project.latest_evaluation
  const score = useMemo(() => {
    if (!evaluation?.model_judge) return null
    const judge = evaluation.model_judge
    return (
      (judge.coverage_score +
        judge.level_fit_score +
        judge.pedagogy_score +
        judge.tone_score +
        judge.factuality_score +
        judge.pacing_score) /
      6
    ).toFixed(1)
  }, [evaluation])

  return (
    <div className="panel">
      <div className="section-heading">
        {evaluation?.passed_gate ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
        <h2>Evaluation</h2>
      </div>
      {!evaluation ? (
        <p className="muted">Evaluation appears after generation completes.</p>
      ) : (
        <>
          <p className={evaluation.passed_gate ? 'success' : 'danger'}>
            {evaluation.passed_gate ? 'Passed gate' : 'Needs review'}
          </p>
          {score && <Metric label="Judge avg" value={score} />}
          {evaluation.structural.failures.length > 0 && (
            <ul className="compact-list">
              {evaluation.structural.failures.map((failure) => <li key={failure}>{failure}</li>)}
            </ul>
          )}
          {evaluation.model_judge && <p className="muted">{evaluation.model_judge.judge_rationale}</p>}
        </>
      )}
    </div>
  )
}

function SignOffPanel({
  project,
  onProjectChange,
}: {
  project: ScriptProject
  onProjectChange: (project: ScriptProject) => void
}) {
  const [name, setName] = useState('')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)

  async function approve() {
    setBusy(true)
    try {
      onProjectChange(await signOffProject(project.id, name, notes))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel">
      <div className="section-heading">
        <ShieldCheck size={18} />
        <h2>Sign-off</h2>
      </div>
      {project.sign_off ? (
        <p className="success">Approved by {project.sign_off.instructor_name}</p>
      ) : (
        <>
          <input placeholder="Instructor name" value={name} onChange={(event) => setName(event.target.value)} />
          <textarea rows={3} placeholder="Final notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <button className="button primary wide" type="button" disabled={!name || busy} onClick={approve}>
            Approve final script
          </button>
        </>
      )}
    </div>
  )
}

function ReviewHistory({ project }: { project: ScriptProject }) {
  return (
    <div className="panel">
      <h2>Review history</h2>
      {project.review_events.length === 0 ? (
        <p className="muted">Edits and approvals will appear here.</p>
      ) : (
        <ul className="event-list">
          {project.review_events.slice(-6).map((event) => (
            <li key={event.id}>
              <strong>{event.type}</strong>
              <span>{event.instructor_feedback || 'No note'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function OutlineWaiting({ project }: { project: ScriptProject }) {
  return (
    <div className="empty-state">
      <Loader2 className="spin" size={24} />
      <h2>{project.generation_message}</h2>
      <p>Generated artifacts will appear progressively as the backend completes each stage.</p>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const ready = status === 'READY_FOR_REVIEW'
  const failed = status === 'FAILED'
  return (
    <span className={`status-badge ${ready ? 'ready' : failed ? 'failed' : ''}`}>
      {ready ? <CheckCircle2 size={15} /> : failed ? <XCircle size={15} /> : <Loader2 className="spin" size={15} />}
      {status.replaceAll('_', ' ')}
    </span>
  )
}

export default App
