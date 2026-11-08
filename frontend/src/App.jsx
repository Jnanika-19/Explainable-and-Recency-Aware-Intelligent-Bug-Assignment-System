import { useCallback, useEffect, useState } from 'react'

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`)
  return payload
}

const pages = [
  ['dashboard', 'Overview', '▦'],
  ['new-bug', 'New bug report', '＋'],
  ['bugs', 'Bug reports', '▤'],
  ['developers', 'Developers', '♙'],
  ['assignments', 'Assignment history', '◷'],
  ['explainability', 'Explainability', '✧'],
]

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [selectedId, setSelectedId] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('')
  const [sortOrder, setSortOrder] = useState('newest')
  const [refresh, setRefresh] = useState(0)

  const load = useCallback(async () => {
    if (page === 'new-bug') return
    setLoading(true)
    setError('')
    try {
      let path = ''
      if (page === 'dashboard') path = '/dashboard/stats'
      if (page === 'bugs') {
        const params = new URLSearchParams()
        if (search) params.set('search', search)
        if (filter) params.set('status', filter)
        params.set('sort', sortOrder === 'title' ? 'title' : 'created_at')
        params.set('order', sortOrder === 'oldest' || sortOrder === 'title' ? 'asc' : 'desc')
        path = `/bugs?${params}`
      }
      if (page === 'bug-detail') path = `/bugs/${selectedId}`
      if (page === 'developers') path = `/developers?search=${encodeURIComponent(search)}`
      if (page === 'developer-detail') path = `/developers/${encodeURIComponent(selectedId)}`
      if (page === 'assignments') {
        const params = new URLSearchParams()
        if (search) params.set('search', search)
        if (filter) params.set('status', filter)
        params.set('sort', sortOrder === 'developer' ? 'developer_name' : sortOrder === 'title' ? 'bug_title' : 'assignment_date')
        params.set('order', sortOrder === 'oldest' || sortOrder === 'title' || sortOrder === 'developer' ? 'asc' : 'desc')
        path = `/assignments?${params}`
      }
      if (path) setData(await api(path))
    } catch (requestError) {
      setError(requestError.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [page, selectedId, search, filter, sortOrder, refresh])

  useEffect(() => { load() }, [load])

  const navigate = (next, id = null) => {
    setSelectedId(id)
    setSearch('')
    setFilter('')
    setSortOrder('newest')
    setPage(next)
  }

  async function submitBug(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const request = Object.fromEntries(formData.entries())
    setLoading(true)
    setError('')
    try {
      const result = await api('/bugs', { method: 'POST', body: JSON.stringify(request) })
      setSelectedId(result.bug.bug_id)
      setData(result)
      setPage('bug-detail')
      setRefresh((value) => value + 1)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">B</span><span><b>BugWise</b><small>Developer assignment</small></span></div>
        <p className="nav-caption">WORKSPACE</p>
        {pages.map(([id, label, icon]) => (
          <button key={id} className={`nav-item ${page === id ? 'selected' : ''}`} onClick={() => navigate(id)}>
            <span aria-hidden="true">{icon}</span>{label}
          </button>
        ))}
        <div className="side-note"><span className="status-dot" /> Local project workspace</div>
      </aside>
      <main className="main">
        <header className="topbar"><span>BugWise <i>/</i> {page.replace('-', ' ')}</span><span className="avatar">BW</span></header>
        <div className="content">
          {error && <div className="alert" role="alert"><b>Request failed.</b> {error}</div>}
          {loading && <div className="loading" role="status">Loading…</div>}
          {page === 'dashboard' && <Dashboard data={data} navigate={navigate} />}
          {page === 'new-bug' && <BugForm onSubmit={submitBug} loading={loading} />}
          {page === 'bugs' && <BugList data={data} navigate={navigate} search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} sortOrder={sortOrder} setSortOrder={setSortOrder} />}
          {page === 'bug-detail' && <BugDetail data={data} />}
          {page === 'developers' && <DeveloperList data={data} navigate={navigate} search={search} setSearch={setSearch} />}
          {page === 'developer-detail' && <DeveloperDetail data={data} />}
          {page === 'assignments' && <AssignmentList data={data} search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} sortOrder={sortOrder} setSortOrder={setSortOrder} />}
          {page === 'explainability' && <Explainability data={data} />}
        </div>
      </main>
    </div>
  )
}

function Header({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>
}

function Dashboard({ data, navigate }) {
  const stats = data || {}
  return <>
    <Header eyebrow="OVERVIEW" title="Assignment dashboard" description="Bug triage activity, developer coverage, and assignment history."
      action={<button className="button primary" onClick={() => navigate('new-bug')}>＋ New bug report</button>} />
    <div className="stat-grid">
      <Stat label="Total reports" value={stats.total_bugs ?? '—'} icon="▤" />
      <Stat label="Open bugs" value={stats.open_bugs ?? '—'} icon="◷" />
      <Stat label="Resolved bugs" value={stats.resolved_bugs ?? '—'} icon="✓" />
      <Stat label="Assigned bugs" value={stats.assigned_bugs ?? '—'} icon="↗" />
      <Stat label="Developers" value={stats.total_developers ?? '—'} icon="♙" />
    </div>
    <section className="panel">
      <div className="panel-title"><div><h2>Recent assignments</h2><p>Latest recorded developer assignments.</p></div>
        <button className="button secondary" onClick={() => navigate('assignments')}>View history →</button></div>
      {stats.recent_assignments?.length ? <div className="table-scroll"><table><thead><tr><th>Bug</th><th>Developer</th><th>Assigned</th><th>Status</th></tr></thead><tbody>
        {stats.recent_assignments.map((row) => <tr key={row.assignment_id}><td>#{row.bug_id} · {row.bug_title}</td><td>{row.developer_name}</td><td>{date(row.assignment_date)}</td><td><Badge>{row.status}</Badge></td></tr>)}
      </tbody></table></div> : <Empty title="No assignments yet" text="Submitted reports and their assignment history will appear here." />}
    </section>
  </>
}

function Stat({ label, value, icon }) {
  return <article className="stat-card"><div className="stat-label">{label}<span>{icon}</span></div><strong>{value}</strong><small>From saved project records</small></article>
}

function BugForm({ onSubmit, loading }) {
  return <>
    <Header eyebrow="TRIAGE" title="Submit a bug report" description="Capture the issue details and request a developer shortlist." />
    <form className="panel form" onSubmit={onSubmit}>
      <div className="form-grid">
        <Field label="Bug title" name="title" required minLength={3} placeholder="Concise summary of the issue" wide />
        <Field label="Component" name="component" required placeholder="e.g. editor, compiler" />
        <Field label="Programming language" name="programming_language" placeholder="e.g. Java" />
        <Field label="Severity" name="severity" select options={['blocker', 'critical', 'major', 'normal', 'minor']} />
        <Field label="Priority" name="priority" select options={['P1', 'P2', 'P3', 'P4', 'unknown']} />
        <Field label="Submission date" name="submission_date" type="datetime-local" />
        <Field label="Description" name="description" textarea placeholder="Steps to reproduce, expected and actual behavior…" wide />
      </div>
      <div className="form-footer"><span>Recommendations remain marked as demo-only until the ML and scoring modules are integrated.</span>
        <button className="button primary" disabled={loading}>{loading ? 'Submitting…' : 'Submit and recommend →'}</button></div>
    </form>
  </>
}

function Field({ label, name, required, minLength, placeholder, type = 'text', select, options, textarea, wide }) {
  return <label className={`field ${wide ? 'wide' : ''}`}><span>{label}{required && <b> *</b>}</span>
    {select ? <select name={name} defaultValue={options[0]}>{options.map((option) => <option key={option}>{option}</option>)}</select>
      : textarea ? <textarea name={name} rows="6" placeholder={placeholder} />
        : <input name={name} type={type} required={required} minLength={minLength} placeholder={placeholder} />}</label>
}

function SearchControls({ search, setSearch, filter, setFilter, sortOrder, setSortOrder, assignment = false }) {
  return <div className="controls"><input aria-label="Search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search reports…" />
    <select aria-label="Filter by status" value={filter} onChange={(event) => setFilter(event.target.value)}>
      <option value="">All statuses</option><option>OPEN</option><option>ASSIGNED</option><option>IN_PROGRESS</option><option>RESOLVED</option><option>CLOSED</option>
    </select>
    <select aria-label="Sort records" value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}>
      {assignment ? <><option value="newest">Newest assignment</option><option value="oldest">Oldest assignment</option><option value="title">Bug title</option><option value="developer">Developer</option></>
        : <><option value="newest">Newest report</option><option value="oldest">Oldest report</option><option value="title">Title</option></>}
    </select></div>
}

function BugList({ data, navigate, search, setSearch, filter, setFilter, sortOrder, setSortOrder }) {
  return <>
    <Header eyebrow="BUG MANAGEMENT" title="Bug reports" description="Search, filter, and review submitted reports."
      action={<button className="button primary" onClick={() => navigate('new-bug')}>＋ New report</button>} />
    <SearchControls search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} sortOrder={sortOrder} setSortOrder={setSortOrder} />
    <section className="panel table-panel">{data?.items?.length ? <div className="table-scroll"><table><thead><tr><th>ID</th><th>Title</th><th>Component</th><th>Severity</th><th>Submitted</th><th>Status</th></tr></thead><tbody>
      {data.items.map((row) => <tr key={row.bug_id} onClick={() => navigate('bug-detail', row.bug_id)}><td>#{row.bug_id}</td><td>{row.title}</td><td>{row.component}</td><td>{row.severity}</td><td>{date(row.created_at)}</td><td><Badge>{row.status}</Badge></td></tr>)}
    </tbody></table></div> : <Empty title="No matching reports" text="Submit a report or adjust your search filters." />}</section>
  </>
}

function BugDetail({ data }) {
  if (!data?.bug) return <Empty title="Bug report unavailable" text="Return to the report list and choose a report." />
  const bug = data.bug
  const demo = data.recommendations?.some((item) => item.mode === 'demo')
  return <>
    <Header eyebrow={`BUG #${bug.bug_id}`} title={bug.title} description={`${bug.component} · ${bug.severity} · ${bug.priority}`} />
    <section className="panel detail-panel"><h2>Bug description</h2><p>{bug.description || 'No description provided.'}</p>
      <div className="detail-meta"><span>Status <b>{bug.status}</b></span><span>Language <b>{bug.programming_language || 'Not specified'}</b></span><span>Submitted <b>{date(bug.created_at)}</b></span></div></section>
    <section className="recommendations">
      <div className="section-heading"><h2>Top developer recommendations</h2>{demo && <Badge tone="warning">DEMO ONLY</Badge>}</div>
      {demo && <div className="notice" role="note">These placeholders are not ML predictions or assignment advice. Connect Member 2 and Member 3 modules before operational use.</div>}
      <div className="recommendation-grid">{(data.recommendations || []).map((item) => <RecommendationCard key={item.recommendation_id || item.developer_id} item={item} />)}</div>
      {!data.recommendations?.length && <Empty title="No recommendations available" text="The recommendation service has not returned candidates." />}
    </section>
    {data.assignments?.length > 0 && <section className="panel"><h2>Assignment history</h2><AssignmentTable rows={data.assignments} /></section>}
  </>
}

function RecommendationCard({ item }) {
  const demo = item.mode === 'demo'
  return <article className="recommend-card">
    <div className="recommend-head"><span className="rank">#{item.rank}</span>{demo && <Badge tone="warning">MOCK</Badge>}</div>
    <h3>{item.developer_id}</h3>
    <div className="score">Ranking score <b>{item.score == null ? 'Not calculated' : `${(item.score * 100).toFixed(1)}%`}</b></div>
    <div className="evidence-grid"><span>Component expertise <b>{item.expertise_score == null ? 'Not calculated' : item.expertise_score}</b></span>
      <span>Recent activity <b>{item.recency_score == null ? 'Not calculated' : item.recency_score}</b></span></div>
    <h4>Why this developer?</h4><p>{item.explanation}</p>
    {item.evidence && Object.keys(item.evidence).length > 0 && <ul className="evidence-list">{Object.entries(item.evidence).map(([key, value]) => <li key={key}>{key}: {String(value)}</li>)}</ul>}
  </article>
}

function DeveloperList({ data, navigate, search, setSearch }) {
  return <>
    <Header eyebrow="TEAM" title="Developer directory" description="Experience and component expertise from recorded assignments." />
    <div className="controls"><input aria-label="Search developers" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search developer name or ID…" /></div>
    <section className="panel table-panel">{data?.items?.length ? <div className="table-scroll"><table><thead><tr><th>Developer</th><th>ID</th><th>Bugs handled</th><th>Resolved</th></tr></thead><tbody>
      {data.items.map((row) => <tr key={row.developer_id} onClick={() => navigate('developer-detail', row.developer_id)}><td>{row.name}</td><td>{row.developer_id}</td><td>{row.bugs_handled || 0}</td><td>{row.resolved_bugs || 0}</td></tr>)}
    </tbody></table></div> : <Empty title="No developer profiles yet" text="Profiles will appear when developer data or assignment records are integrated." />}</section>
  </>
}

function DeveloperDetail({ data }) {
  if (!data?.developer) return <Empty title="Developer unavailable" text="Choose a developer from the directory." />
  const developer = data.developer
  return <>
    <Header eyebrow="DEVELOPER PROFILE" title={developer.name} description={developer.developer_id} />
    <section className="stat-grid"><Stat label="Bugs handled" value={data.stats?.bugs_handled ?? 0} icon="▤" /><Stat label="Resolved bugs" value={data.stats?.resolved_bugs ?? 0} icon="✓" /><Stat label="Expertise areas" value={data.expertise?.length ?? 0} icon="✧" /></section>
    <section className="panel"><h2>Component expertise</h2>{data.expertise?.length ? <AssignmentTable rows={data.expertise.map((item) => ({ ...item, title: item.component, assignment_date: item.last_activity_at, status: `${item.resolved_bugs} resolved / ${item.bugs_handled} handled` }))} /> : <Empty title="No expertise evidence" text="No component-level activity is recorded for this developer." />}</section>
    <section className="panel spaced"><h2>Recent contributions</h2>{data.recent_assignments?.length ? <AssignmentTable rows={data.recent_assignments} /> : <Empty title="No recent assignments" text="Developer activity will appear when assignment history is available." />}</section>
  </>
}

function AssignmentList({ data, search, setSearch, filter, setFilter, sortOrder, setSortOrder }) {
  return <>
    <Header eyebrow="HISTORY" title="Assignment history" description="Review recorded bug assignments with search and status filters." />
    <SearchControls search={search} setSearch={setSearch} filter={filter} setFilter={setFilter} sortOrder={sortOrder} setSortOrder={setSortOrder} assignment />
    <section className="panel table-panel">{data?.items?.length ? <AssignmentTable rows={data.items} /> : <Empty title="No assignments found" text="Assignment history appears after a developer is assigned to a report." />}</section>
  </>
}

function AssignmentTable({ rows }) {
  return <div className="table-scroll"><table><thead><tr><th>Bug / Component</th><th>Developer</th><th>Assignment date</th><th>Severity</th><th>Status</th></tr></thead><tbody>
    {rows.map((row, index) => <tr key={row.assignment_id || row.expertise_id || index}><td>#{row.bug_id || '—'} · {row.bug_title || row.component || row.title}</td><td>{row.developer_name || row.developer_id || '—'}</td><td>{date(row.assignment_date || row.last_activity_at)}</td><td>{row.severity || '—'}</td><td>{row.status || '—'}</td></tr>)}
  </tbody></table></div>
}

function Explainability({ data }) {
  const item = data?.recommendations?.[0]
  return <>
    <Header eyebrow="TRANSPARENCY" title="Explainability" description="Review evidence returned with recommendations; unsupported reasons are not inferred by the UI." />
    {item?.mode === 'demo' && <div className="notice">Current recommendations are demo placeholders. No expertise, recency, or ranking score has been calculated.</div>}
    {item ? <RecommendationCard item={item} /> : <section className="panel"><Empty title="No recommendation evidence selected" text="Open a bug report to inspect the explanation payload returned by the recommendation service." /></section>}
    <section className="panel spaced"><h2>Integration status</h2><p className="muted">The API currently returns explicitly labeled demo placeholders. The Member 2 recommender and Member 3 scoring engine must provide numeric evidence and explanations before real ranking results are displayed.</p></section>
  </>
}

function Badge({ children, tone }) { return <span className={`badge ${tone || ''}`}>{children}</span> }
function Empty({ title, text }) { return <div className="empty"><span>◇</span><b>{title}</b><p>{text}</p></div> }
function date(value) { return value ? new Date(value).toLocaleString() : '—' }
