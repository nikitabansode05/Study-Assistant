import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, BookOpen, FileText, FileUp, GraduationCap, LoaderCircle, LogIn, LogOut, MessageSquare, Send, ShieldCheck, Trash2, UploadCloud, UserCheck, Wifi, X } from 'lucide-react'
import { askQuestion, deleteDocument, getDocuments, getHealth, loginMentor, logoutMentor, setMentorToken, uploadDocument, uploadRepositoryZip } from './api'
import MarkdownMessage from './MarkdownMessage.jsx'
import LoginModal from './LoginModal.jsx'
import taplogo from './assests/taplogo.jpeg'
import mentor_mentee from './assests/mentor_mentee.png'

const ROLES = { STUDENT: 'student', MENTOR: 'mentor' }
const SKIPPED_FOLDERS = /(^|\/)(node_modules|\.git|\.venv|venv|dist|build|__pycache__|\.next)\//

const starterMessage = {
  role: 'assistant',
  kind: 'welcome',
  content: 'Hi! I’m **Nikita**, your mentor from Transflower Learning.\n\nAsk me any question about your **TAP learning** material — I’ll answer from the knowledge base and help you build your skills.',
  sources: [],
}

function App() {
  // Single source of truth for the UI role. Always starts as "student" and is never persisted,
  // so reloading the page returns to the default chat-only view.
  const [currentRole, setCurrentRole] = useState(ROLES.STUDENT)
  const [mentorUser, setMentorUser] = useState('')
  const [showLogin, setShowLogin] = useState(false)
  const [notice, setNotice] = useState('')

  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState([starterMessage])
  const [question, setQuestion] = useState('')
  const [studentId, setStudentId] = useState('')
  const [importingZip, setImportingZip] = useState(false)
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState('')
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef(null)
  const zipInput = useRef(null)
  const folderInput = useRef(null)
  const chatEnd = useRef(null)

  const isMentor = currentRole === ROLES.MENTOR
  const indexedCount = isMentor ? documents.length : (health?.indexed_documents ?? 0)

  const refreshHealth = useCallback(async () => {
    try { setHealth(await getHealth()) } catch { setHealth(null) }
  }, [])

  const refreshDocuments = useCallback(async () => {
    try {
      const d = await getDocuments()
      setDocuments(d.documents || [])
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const refresh = useCallback(async () => {
    await Promise.all([refreshHealth(), isMentor ? refreshDocuments() : Promise.resolve()])
  }, [refreshHealth, refreshDocuments, isMentor])

  useEffect(() => {
    refreshHealth()
    const timer = setInterval(refreshHealth, 15000)
    return () => clearInterval(timer)
  }, [refreshHealth])
  useEffect(() => { if (isMentor) refreshDocuments() }, [isMentor, refreshDocuments])
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  // ---------------------------------------------------------------- role switching
  const resetToStudent = useCallback((message = '') => {
    setMentorToken(null)
    setCurrentRole(ROLES.STUDENT)
    setMentorUser('')
    setDocuments([])
    setError('')
    setUploadStatus('')
    setDragging(false)
    setNotice(message)
  }, [])

  const handleLogin = useCallback(async (userId, password) => {
    const result = await loginMentor(userId, password) // throws on wrong credentials
    setMentorToken(result.token)
    setMentorUser(result.user_id)
    setCurrentRole(ROLES.MENTOR)
    setNotice('')
    setShowLogin(false)
  }, [])

  async function handleLogout() {
    try { await logoutMentor() } catch { /* backend offline: still clear the local mentor state */ }
    resetToStudent()
    refreshHealth()
  }

  const closeLogin = useCallback(() => setShowLogin(false), [])

  // Returns true if the error meant the mentor session is no longer valid (e.g. backend restarted).
  function handleAuthFailure(e) {
    if (e?.status === 401) {
      resetToStudent('Your mentor session has ended (the backend may have restarted). Please log in again.')
      return true
    }
    return false
  }

  // ---------------------------------------------------------------- mentor document management
  async function handleFiles(fileList) {
    const files = Array.from(fileList || [])
    if (!files.length) return
    setUploading(true)
    setError('')
    let success = 0
    const failures = []
    for (const [i, file] of files.entries()) {
      setUploadStatus(`Indexing ${file.name} (${i + 1} of ${files.length})…`)
      try {
        await uploadDocument(file)
        success += 1
      } catch (e) {
        if (handleAuthFailure(e)) { setUploading(false); return }
        failures.push(`${file.name}: ${e.message}`)
      }
    }
    await refresh()
    setUploading(false)
    setUploadStatus(`Indexed ${success} of ${files.length} file${files.length === 1 ? '' : 's'}.`)
    if (failures.length) setError(failures.slice(0, 3).join(' | '))
    if (fileInput.current) fileInput.current.value = ''
  }

  async function handleRepositoryZip(file) {
    if (!file) return
    setImportingZip(true)
    setError('')
    setUploadStatus(`Importing ${file.name}…`)
    try {
      const result = await uploadRepositoryZip(file)
      await refresh()
      setUploadStatus(`ZIP import finished: indexed ${result.indexed_files} of ${result.markdown_files_found} Markdown files.`)
      setMessages(prev => [...prev, {
        role: 'assistant',
        kind: 'notice',
        content: `ZIP import finished for **${result.repository}**. Found ${result.markdown_files_found} Markdown files and indexed ${result.indexed_files}. You can now ask questions about this repository.`,
        sources: [],
      }])
      if (result.failed_files?.length) setError(`Some Markdown files could not be indexed: ${result.failed_files.slice(0, 3).join(' | ')}`)
    } catch (e) {
      if (!handleAuthFailure(e)) { setError(e.message); setUploadStatus('') }
    } finally {
      setImportingZip(false)
      if (zipInput.current) zipInput.current.value = ''
    }
  }

  async function handleFolderFiles(fileList) {
    const files = Array.from(fileList || [])
      .filter(file => /\.(md|markdown)$/i.test(file.name))
      .filter(file => !SKIPPED_FOLDERS.test(file.webkitRelativePath || ''))
    if (folderInput.current) folderInput.current.value = ''
    if (!files.length) {
      setError('No .md or .markdown files were found in that folder. Select the extracted GitHub repository folder.')
      return
    }
    setUploading(true)
    setError('')
    let success = 0
    const failures = []
    for (const [i, file] of files.entries()) {
      const name = file.webkitRelativePath || file.name
      setUploadStatus(`Indexing ${name} (${i + 1} of ${files.length})…`)
      try { await uploadDocument(file, name); success += 1 }
      catch (e) {
        if (handleAuthFailure(e)) { setUploading(false); return }
        failures.push(`${name}: ${e.message}`)
      }
    }
    await refresh()
    setUploadStatus(`Folder import finished: indexed ${success} of ${files.length} Markdown files.`)
    setMessages(prev => [...prev, {
      role: 'assistant',
      kind: 'notice',
      content: `Folder import finished. Indexed **${success} of ${files.length}** Markdown files.${failures.length ? `\n\n**Failed files:**\n${failures.slice(0, 5).map(f => `- ${f}`).join('\n')}` : ''}`,
      sources: [],
    }])
    if (failures.length) setError(failures.slice(0, 2).join(' | '))
    setUploading(false)
  }

  async function removeDocument(doc) {
    if (!window.confirm(`Delete "${doc.filename}" and its indexed chunks?`)) return
    setError('')
    try {
      await deleteDocument(doc.id)
      setUploadStatus(`Deleted ${doc.filename}.`)
      await refresh()
    } catch (e) {
      if (!handleAuthFailure(e)) setError(e.message)
    }
  }

  // ---------------------------------------------------------------- chat (both roles)
  async function sendQuestion(e) {
    e?.preventDefault()
    const q = question.trim()
    if (!q || busy) return
    setMessages(prev => [...prev, { role: 'user', content: q, sources: [] }])
    setQuestion('')
    setBusy(true)
    try {
      const history = messages
        .filter(m => ['user', 'assistant'].includes(m.role) && !m.kind)
        .slice(-10)
        .map(m => ({ role: m.role, content: String(m.content ?? '') }))
      const result = await askQuestion(q, history, studentId)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: typeof result?.answer === 'string' ? result.answer : '',
        sources: Array.isArray(result?.sources) ? result.sources : [],
      }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', kind: 'error', content: `I couldn't complete that request: ${err.message}`, sources: [] }])
    } finally {
      setBusy(false)
    }
  }

  // ---------------------------------------------------------------- status helpers
  const ollama = health?.ollama
  const modelState = !health ? 'offline'
    : !ollama?.reachable ? 'offline'
      : (ollama.chat_model_available && ollama.embed_model_available) ? 'ok' : 'warn'
  const modelTitle = !health ? 'Backend offline'
    : !ollama?.reachable ? (ollama?.error || 'Ollama is not reachable')
      : modelState === 'ok' ? `Ollama ready · chat: ${health.chat_model} · embeddings: ${health.embedding_model}`
        : `Ollama is running but a model is missing. Run: ${[!ollama.chat_model_available && `ollama pull ${health.chat_model}`, !ollama.embed_model_available && `ollama pull ${health.embedding_model}`].filter(Boolean).join(' and ')}`

  const placeholder = !health ? 'Backend offline — start the FastAPI server…'
    : indexedCount ? 'Ask a question about your learning material…'
      : isMentor ? 'Upload a document to get started…' : 'The knowledge base is empty — ask your mentor to add documents…'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-icon"><img src={taplogo} alt="Company Logo" /></div><div><strong>TFLRAG</strong><span>Information at your fingertip</span></div></div>
        <div className="side-label">TFL WORKSPACE</div>
        <div className="nav-item active"><MessageSquare size={17} /> {isMentor ? 'Chat & knowledge base' : 'Ask your mentor'}</div>
        <div className="side-label docs-label">{isMentor ? 'YOUR KNOWLEDGE' : 'KNOWLEDGE BASE'} <span>{indexedCount}</span></div>
        {isMentor ? (
          <div className="doc-list">
            {documents.length === 0 && <p className="empty-docs">Your uploaded documents will appear here.</p>}
            {documents.map(doc => <div className="doc-row" key={doc.id}><FileText size={17} /><div className="doc-meta"><strong title={doc.filename}>{doc.filename}</strong><span>{doc.chunks} chunks</span></div><button className="icon-button delete-button" title="Delete document" aria-label={`Delete ${doc.filename}`} onClick={() => removeDocument(doc)}><Trash2 size={15} /></button></div>)}
          </div>
        ) : (
          <p className="empty-docs">{indexedCount ? `${indexedCount} document${indexedCount === 1 ? '' : 's'} curated by your mentor.` : 'Your mentor has not added documents yet.'}</p>
        )}
        <div className="sidebar-bottom"><div className="privacy-icon"><ShieldCheck size={17} /></div><div><p>TAP your potential</p></div></div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><div className="eyebrow">TRANSFLOWER</div><h1>TFL CoMentor(Java)</h1><p>Mentor as a Service (MaaS).</p></div>
          <div className="topbar-actions">
            <div className={`connection ${health ? 'connected' : 'disconnected'}`}><span className="status-dot" />{health ? 'Backend connected' : 'Backend offline'}</div>
            {isMentor
              ? <div className="role-badge mentor" title={mentorUser}><UserCheck size={14} /> Mentor</div>
              : <div className="role-badge student"><GraduationCap size={14} /> Student</div>}
            {isMentor
              ? <button type="button" className="auth-button logout" onClick={handleLogout}><LogOut size={15} /> Logout</button>
              : <button type="button" className="auth-button" onClick={() => setShowLogin(true)}><LogIn size={15} /> Login</button>}
          </div>
        </header>

        {notice && <div className="notice-banner" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss"><X size={14} /></button></div>}

        <section className={`workspace ${isMentor ? 'mentor-layout' : 'student-layout'}`}>
          {isMentor && (
            <div className="upload-card">
              <div className="section-heading"><div className="heading-icon"><UploadCloud size={19} /></div><div><h2>Add your documents</h2><p>Upload files to build your searchable knowledge base.</p></div></div>
              <div className="repo-import">
                <label>Import a GitHub repository without entering a URL</label>
                <p className="import-help">On GitHub, open the repository → Code → Download ZIP, then select that ZIP here. The app indexes its Markdown files locally.</p>
                <input ref={zipInput} type="file" accept=".zip,application/zip" hidden onChange={e => handleRepositoryZip(e.target.files?.[0])} />
                <button type="button" className="import-all-button" onClick={() => zipInput.current?.click()} disabled={importingZip || uploading}>
                  {importingZip ? 'Importing ZIP and indexing Markdown…' : 'Choose GitHub repository ZIP'}
                </button>
                <input ref={folderInput} type="file" webkitdirectory="" directory="" multiple hidden onChange={e => handleFolderFiles(e.target.files)} />
                <button type="button" className="preset-repo" onClick={() => folderInput.current?.click()} disabled={uploading || importingZip}>Choose extracted repository folder</button>
                <small>ZIP import keeps repository-relative source paths. Folder import indexes .md/.markdown files only.</small>
              </div>
              <div className={`drop-zone ${dragging ? 'dragging' : ''} ${uploading ? 'busy' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (!uploading) handleFiles(e.dataTransfer.files) }} onClick={() => !uploading && fileInput.current?.click()} role="button" tabIndex="0" onKeyDown={e => e.key === 'Enter' && !uploading && fileInput.current?.click()}>
                <input ref={fileInput} type="file" multiple accept=".pdf,.docx,.txt,.md,.markdown,.png,.jpg,.jpeg,.tif,.tiff,.bmp" onChange={e => handleFiles(e.target.files)} hidden />
                <div className="upload-icon"><FileUp size={22} /></div>
                <strong>{uploading ? 'Processing and indexing…' : 'Drop files here or browse'}</strong>
                <span>PDF, DOCX, TXT, MD, images · Multiple files supported</span>
                {uploading && <LoaderCircle className="spin" size={18} />}
              </div>
              {uploadStatus && <div className="status-line">{(uploading || importingZip) && <LoaderCircle className="spin" size={13} />}{uploadStatus}</div>}
              <div className="upload-foot"><span><ShieldCheck size={14} /> Private local storage</span><span><Activity size={14} /> {documents.length} document{documents.length === 1 ? '' : 's'} indexed</span></div>
              {error && <div className="error-banner"><X size={16} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={14} /></button></div>}
            </div>
          )}

          <div className="chat-card">
            <div className="chat-heading"><div className="section-heading"><div className="heading-icon purple"><img src={mentor_mentee} alt="Mentor" /></div><div><h2>Ask your mentor</h2><p>Answers generated by TFL language model.</p></div></div><div className={`model-pill ${modelState}`} title={modelTitle}><span className="status-dot" />{health?.chat_model || 'Ollama'}{modelState === 'offline' && health ? ' · offline' : ''}{modelState === 'warn' ? ' · model missing' : ''}</div></div>
            <div className="messages">
              {messages.map((msg, i) => (
                <div className={`message ${msg.role} ${msg.kind || ''}`} key={`${i}-${msg.role}`}>
                  <div className="avatar">{msg.role === 'assistant' ? <img src={mentor_mentee} alt="Mentor" /> : <span>Y</span>}</div>
                  <div className="message-body">
                    <div className="message-author">{msg.role === 'assistant' ? 'TFLCoMentor' : 'You'}</div>
                    {msg.role === 'assistant' && msg.kind !== 'error'
                      ? <MarkdownMessage content={msg.content} />
                      : <div className="message-text">{msg.content}</div>}
                    {Array.isArray(msg.sources) && msg.sources.length > 0 && (
                      <div className="sources">
                        <div className="sources-title"><BookOpen size={14} /> Sources used</div>
                        {msg.sources.map((s, j) => <div className="source" key={`${s?.chunk_id ?? j}-${j}`}><div className="source-name"><FileText size={14} /><strong>{s?.document || 'Unknown document'}</strong>{s?.page ? <span>Page {s.page}</span> : null}</div>{s?.excerpt && <p>{s.excerpt}</p>}</div>)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {busy && <div className="message assistant"><div className="avatar"><img src={mentor_mentee} alt="Mentor" /></div><div className="message-body"><div className="message-author">TFLCoMentor</div><div className="typing"><LoaderCircle className="spin" size={16} /> Searching documents and generating an answer…</div></div></div>}
              <div ref={chatEnd} />
            </div>
            <form className="composer" onSubmit={sendQuestion}>
              <label className="student-id-label" htmlFor="student-id">Student ID <span>(needed for performance questions)</span></label>
              <input
                id="student-id"
                className="student-id-input"
                value={studentId}
                onChange={e => setStudentId(e.target.value)}
                placeholder="Enter your student ID"
                autoComplete="off"
                maxLength={100}
                disabled={busy}
              />
              <div className="composer-input"><textarea value={question} onChange={e => setQuestion(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion() } }} placeholder={placeholder} rows="1" disabled={busy} aria-label="Ask a question" /><button type="submit" className="send-button" disabled={!question.trim() || busy} aria-label="Send question">{busy ? <LoaderCircle className="spin" size={17} /> : <Send size={17} />}</button></div>
              <div className="composer-note"><span><Wifi size={13} /> Doing ordinary things extra ordinarilly</span><span>Enter to send · Shift+Enter for new line</span></div>
            </form>
          </div>
        </section>
        <footer className="footer"><span>TFL · A learning experience</span><span>Built for Transflower</span></footer>
      </main>

      {showLogin && !isMentor && <LoginModal onClose={closeLogin} onLogin={handleLogin} />}
    </div>
  )
}

export default App
