import React, { useState, useEffect } from 'react';
import {
  createSession,
  getSession,
  submitParticipant,
  triggerAnalysis,
  getIssues,
  updateIssueStatus,
  getAgreement,
  confirmAgreement,
  getBridgeTest,
} from './api';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Users,
  Copy,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export default function App() {
  const [session, setSession] = useState(null);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('misunderstood_session_id') || '');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeTab, setActiveTab] = useState('create');

  // New session inputs
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [joinCodeInput, setJoinCodeInput] = useState('');

  // Participant submission inputs
  const [participantName, setParticipantName] = useState('');
  const [participantId, setParticipantId] = useState('');
  const [interpretation, setInterpretation] = useState('');
  const [assumptions, setAssumptions] = useState('');
  const [successCriteria, setSuccessCriteria] = useState('');

  // Results & Agreement state
  const [issues, setIssues] = useState([]);
  const [issueFilter, setIssueFilter] = useState('all');
  const [expandedEvidence, setExpandedEvidence] = useState({});
  const [agreement, setAgreement] = useState(null);
  const [bridgeTest, setBridgeTest] = useState(null);
  const [confirmingParticipant, setConfirmingParticipant] = useState('');
  const [resolvingIssueId, setResolvingIssueId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId);
    }
  }, [sessionId]);

  const loadSession = async (id) => {
    try {
      setLoading(true);
      setErrorMessage('');
      const data = await getSession(id);
      setSession(data);

      if (data.status === 'completed') {
        const issuesData = await getIssues(id);
        setIssues(issuesData);
        const agreementData = await getAgreement(id).catch(() => null);
        setAgreement(agreementData);
        const bridgeData = await getBridgeTest(id).catch(() => null);
        setBridgeTest(bridgeData);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Could not load session.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (e) => {
    e?.preventDefault();
    if (!taskTitle.trim()) return;

    try {
      setLoading(true);
      setErrorMessage('');
      const newSession = await createSession(taskTitle.trim(), taskDesc.trim());
      setSession(newSession);
      setSessionId(newSession.id);
      localStorage.setItem('misunderstood_session_id', newSession.id);
      setTaskTitle('');
      setTaskDesc('');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create session.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    try {
      setLoading(true);
      setErrorMessage('');

      const demoSession = await createSession(
        'Prepare the application for launch',
        'Finish essential functionality and verify release readiness before product launch.'
      );
      setSession(demoSession);
      setSessionId(demoSession.id);
      localStorage.setItem('misunderstood_session_id', demoSession.id);

      await submitParticipant(demoSession.id, {
        participant_id: 'participant-a',
        name: 'Alex (Lead Developer)',
        interpretation: 'Complete email and password login.',
        assumptions: 'PostgreSQL database will be used.',
        success_criteria: 'Unit tests pass and auth API returns 200.',
      });

      await submitParticipant(demoSession.id, {
        participant_id: 'participant-b',
        name: 'Jordan (Project Manager)',
        interpretation: 'Complete email or phone login, registration, and password recovery.',
        assumptions: 'Self-service account recovery is mandatory for launch.',
        success_criteria: 'Users can sign up, log in with phone or email, and reset passwords without support tickets.',
      });

      await submitParticipant(demoSession.id, {
        participant_id: 'participant-c',
        name: 'Taylor (Product Designer)',
        interpretation: 'Complete onboarding and mobile-responsive UI.',
        assumptions: 'All screen sizes must render seamlessly.',
        success_criteria: 'Onboarding walkthrough displays on first login with 100% responsive styling.',
      });

      await loadSession(demoSession.id);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to initialize demo scenario.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitInterpretation = async (e) => {
    e.preventDefault();
    if (!session || !interpretation.trim()) return;

    const pid = (participantId.trim() || participantName.trim() || `participant-${Date.now()}`)
      .toLowerCase()
      .replace(/\s+/g, '-');

    try {
      setLoading(true);
      setErrorMessage('');
      await submitParticipant(session.id, {
        participant_id: pid,
        name: participantName.trim() || pid,
        interpretation: interpretation.trim(),
        assumptions: assumptions.trim() || null,
        success_criteria: successCriteria.trim() || null,
      });

      setParticipantName('');
      setParticipantId('');
      setInterpretation('');
      setAssumptions('');
      setSuccessCriteria('');

      await loadSession(session.id);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to submit interpretation.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!session) return;
    try {
      setAnalyzing(true);
      setErrorMessage('');
      const result = await triggerAnalysis(session.id);
      setIssues(result.issues || []);

      const agreementData = await getAgreement(session.id).catch(() => null);
      setAgreement(agreementData);
      const bridgeData = await getBridgeTest(session.id).catch(() => null);
      setBridgeTest(bridgeData);

      await loadSession(session.id);
    } catch (err) {
      setErrorMessage(err.message || 'AI analysis failed. Please verify submissions and retry.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpdateIssue = async (issueId, newStatus, notes = null) => {
    if (!session) return;
    try {
      await updateIssueStatus(session.id, issueId, newStatus, notes);
      setResolvingIssueId(null);
      setResolutionNotes('');

      const updatedIssues = await getIssues(session.id);
      setIssues(updatedIssues);
      const updatedAgreement = await getAgreement(session.id);
      setAgreement(updatedAgreement);
      const updatedBridge = await getBridgeTest(session.id);
      setBridgeTest(updatedBridge);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to update issue.');
    }
  };

  const handleConfirmAgreement = async () => {
    if (!session || !confirmingParticipant.trim()) return;
    try {
      const updated = await confirmAgreement(session.id, confirmingParticipant.trim());
      setAgreement(updated);
      const updatedBridge = await getBridgeTest(session.id);
      setBridgeTest(updatedBridge);
      setConfirmingParticipant('');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to confirm agreement.');
    }
  };

  const handleResetSession = () => {
    localStorage.removeItem('misunderstood_session_id');
    setSession(null);
    setSessionId('');
    setIssues([]);
    setAgreement(null);
    setBridgeTest(null);
    setErrorMessage('');
  };

  const toggleEvidence = (issueId) => {
    setExpandedEvidence((prev) => ({
      ...prev,
      [issueId]: !prev[issueId],
    }));
  };

  const filteredIssues = issues.filter((iss) => {
    if (issueFilter === 'all') return true;
    return iss.resolution_status === issueFilter;
  });

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="header-nav">
        <div className="header-content">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
              <h1 style={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.01em' }}>
                MISUNDERSTOOD
              </h1>
              <span className="badge" style={{ background: '#252a3b', color: '#94a3b8' }}>
                Bridge the Gap
              </span>
            </div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
              Same conversation. Different realities.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            {session && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', background: 'var(--bg-primary)', padding: '0.35rem 0.625rem', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Code:</span>
                <strong style={{ color: '#38bdf8', fontFamily: 'monospace' }}>{session.session_code}</strong>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(session.session_code)}
                  title="Copy session code"
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex' }}
                >
                  <Copy size={13} />
                </button>
              </div>
            )}
            {session && (
              <button type="button" onClick={handleResetSession} className="btn btn-secondary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}>
                New Session
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="container" style={{ flex: 1, paddingBottom: '3rem' }}>
        {errorMessage && (
          <div style={{ background: '#451a1a', border: '1px solid #7f1d1d', color: '#fca5a5', padding: '0.875rem 1rem', borderRadius: '6px', marginBottom: '1.25rem', display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, fontSize: '0.875rem' }}>{errorMessage}</div>
            <button type="button" onClick={() => setErrorMessage('')} style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer' }}>✕</button>
          </div>
        )}

        {!session ? (
          <div style={{ maxWidth: '640px', margin: '2rem auto' }}>
            <div className="card">
              <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--border)', marginBottom: '1.25rem', paddingBottom: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setActiveTab('create')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'create' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: 600, paddingBottom: '0.5rem', borderBottom: activeTab === 'create' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Create Task Session
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('join')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'join' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: 600, paddingBottom: '0.5rem', borderBottom: activeTab === 'join' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Join with Code
                </button>
              </div>

              {activeTab === 'create' ? (
                <form onSubmit={handleCreateSession}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="task-title">Task Instruction *</label>
                    <input
                      id="task-title"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Prepare the application for launch"
                      value={taskTitle}
                      onChange={(e) => setTaskTitle(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="task-desc">Context or Details (Optional)</label>
                    <textarea
                      id="task-desc"
                      className="form-textarea"
                      rows={3}
                      placeholder="e.g. Target milestone, known constraints, deliverables..."
                      value={taskDesc}
                      onChange={(e) => setTaskDesc(e.target.value)}
                    />
                  </div>

                  <button type="submit" disabled={loading || !taskTitle.trim()} className="btn btn-primary" style={{ width: '100%' }}>
                    {loading ? <span className="spinner" /> : 'Create Session'}
                  </button>
                </form>
              ) : (
                <div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="join-code">Session Code</label>
                    <input
                      id="join-code"
                      type="text"
                      className="form-input"
                      placeholder="e.g. WLCJLN"
                      value={joinCodeInput}
                      onChange={(e) => setJoinCodeInput(e.target.value.toUpperCase())}
                      maxLength={12}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setErrorMessage('For demonstration, create a session or load the demo scenario below.')}
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                  >
                    Lookup Session
                  </button>
                </div>
              )}

              <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    Preset Scenario
                  </span>
                  <span className="badge" style={{ background: '#252a3b', color: '#94a3b8' }}>
                    3 Participants
                  </span>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                  Loads the scenario <em>"Prepare the application for launch"</em> with pre-configured Developer, Project Manager, and Designer submissions.
                </p>
                <button
                  type="button"
                  onClick={handleLoadDemo}
                  disabled={loading}
                  className="btn btn-secondary"
                  style={{ width: '100%' }}
                >
                  Load Official 3-Party Demo
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div>
            <div className="card" style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                    <span className={`badge badge-${session.status === 'completed' ? 'resolved' : session.status === 'failed' ? 'critical' : 'open'}`}>
                      {session.status}
                    </span>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                      {session.participant_count} participant(s)
                    </span>
                  </div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                    {session.title}
                  </h2>
                  {session.description && (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {session.description}
                    </p>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', alignItems: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={analyzing || (session.participant_count || 0) < 2}
                    className="btn btn-primary"
                    style={{ minWidth: '160px' }}
                  >
                    {analyzing ? (
                      <>
                        <span className="spinner" />
                        Analyzing...
                      </>
                    ) : (
                      issues.length > 0 ? 'Re-run Analysis' : 'Run AI Analysis'
                    )}
                  </button>
                  {(session.participant_count || 0) < 2 && (
                    <span style={{ fontSize: '0.75rem', color: '#fca5a5' }}>
                      Requires ≥ 2 participant submissions
                    </span>
                  )}
                </div>
              </div>

              {analyzing && (
                <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#172b4d', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                  <span className="spinner" />
                  <span style={{ fontSize: '0.8125rem', color: '#93c5fd' }}>
                    Analyzing participant interpretations and validating evidence...
                  </span>
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: issues.length > 0 ? '1fr 1.6fr' : '1fr', gap: '1.25rem' }}>
              <div>
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Users size={16} style={{ color: 'var(--primary)' }} />
                    <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Independent Submissions</h3>
                  </div>

                  <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)', padding: '0.625rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    <strong>Blind submission:</strong> Participants submit independently to prevent bias.
                  </div>

                  <form onSubmit={handleSubmitInterpretation}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-name">Your Name</label>
                        <input
                          id="participant-name"
                          type="text"
                          className="form-input"
                          placeholder="e.g. Alex"
                          value={participantName}
                          onChange={(e) => setParticipantName(e.target.value)}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-id">Role / Identifier</label>
                        <input
                          id="participant-id"
                          type="text"
                          className="form-input"
                          placeholder="e.g. dev-lead"
                          value={participantId}
                          onChange={(e) => setParticipantId(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-interpretation">
                        Task Interpretation *
                      </label>
                      <textarea
                        id="participant-interpretation"
                        className="form-textarea"
                        rows={3}
                        placeholder="What needs to be done for this task to be complete?"
                        value={interpretation}
                        onChange={(e) => setInterpretation(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-assumptions">Assumptions (Optional)</label>
                      <input
                        id="participant-assumptions"
                        type="text"
                        className="form-input"
                        placeholder="e.g. Database schema already finalized"
                        value={assumptions}
                        onChange={(e) => setAssumptions(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-success">Success Criteria (Optional)</label>
                      <input
                        id="participant-success"
                        type="text"
                        className="form-input"
                        placeholder="e.g. Unit tests pass, API responds 200"
                        value={successCriteria}
                        onChange={(e) => setSuccessCriteria(e.target.value)}
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={loading || !interpretation.trim()}
                      className="btn btn-secondary"
                      style={{ width: '100%' }}
                    >
                      {loading ? <span className="spinner" /> : 'Submit Interpretation'}
                    </button>
                  </form>
                </div>
              </div>

              {issues.length > 0 && (
                <div>
                  {bridgeTest && (
                    <div className="card-elevated" style={{ marginBottom: '1.25rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>The Bridge Test</h3>
                        <span className={`badge badge-${bridgeTest.bridge_status === 'bridged' ? 'resolved' : bridgeTest.bridge_status === 'in_progress' ? 'medium' : 'critical'}`}>
                          {bridgeTest.bridge_status.replace('_', ' ')}
                        </span>
                      </div>

                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ width: `${bridgeTest.resolution_percentage}%` }} />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginTop: '0.625rem', textAlign: 'center' }}>
                        <div style={{ background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: '6px' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Detected</span>
                          <div style={{ fontSize: '1.125rem', fontWeight: 700 }}>{bridgeTest.initial_issues_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: '6px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#86efac' }}>Resolved</span>
                          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#16a34a' }}>{bridgeTest.resolved_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: '6px' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dismissed</span>
                          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--text-muted)' }}>{bridgeTest.dismissed_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-primary)', padding: '0.5rem', borderRadius: '6px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#fca5a5' }}>Open</span>
                          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#dc2626' }}>{bridgeTest.open_count}</div>
                        </div>
                      </div>

                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.625rem' }}>
                        {bridgeTest.disclaimer}
                      </p>
                    </div>
                  )}

                  <div className="card" style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Misunderstanding Map</h3>

                      <div style={{ display: 'flex', gap: '0.25rem', background: 'var(--bg-primary)', padding: '0.2rem', borderRadius: '4px' }}>
                        {['all', 'open', 'resolved', 'dismissed'].map((f) => (
                          <button
                            key={f}
                            type="button"
                            onClick={() => setIssueFilter(f)}
                            style={{
                              background: issueFilter === f ? 'var(--bg-surface-elevated)' : 'transparent',
                              border: 'none',
                              color: issueFilter === f ? 'var(--text-primary)' : 'var(--text-muted)',
                              padding: '0.2rem 0.5rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 500,
                              cursor: 'pointer',
                              textTransform: 'capitalize',
                            }}
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
                      {filteredIssues.map((issue) => (
                        <div
                          key={issue.id}
                          className="card-elevated"
                          style={{
                            borderLeft: `3px solid ${
                              issue.priority === 'critical'
                                ? 'var(--priority-critical)'
                                : issue.priority === 'high'
                                ? 'var(--priority-high)'
                                : issue.priority === 'medium'
                                ? 'var(--priority-medium)'
                                : 'var(--priority-low)'
                            }`,
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.375rem' }}>
                            <div style={{ display: 'flex', gap: '0.375rem', alignItems: 'center' }}>
                              <span className={`badge badge-${issue.priority}`}>
                                {issue.priority}
                              </span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                                {issue.type.replace('_', ' ')}
                              </span>
                            </div>
                            <span className={`badge badge-${issue.resolution_status}`}>
                              {issue.resolution_status}
                            </span>
                          </div>

                          <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                            {issue.title}
                          </h4>
                          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.625rem' }}>
                            {issue.description}
                          </p>

                          <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border)', padding: '0.625rem', borderRadius: '6px', marginBottom: '0.625rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: '#93c5fd', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                              <HelpCircle size={13} />
                              Clarification Question:
                            </div>
                            <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                              "{issue.clarification_question}"
                            </div>
                          </div>

                          <div style={{ marginBottom: '0.625rem' }}>
                            <button
                              type="button"
                              onClick={() => toggleEvidence(issue.id)}
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem', padding: 0 }}
                            >
                              {expandedEvidence[issue.id] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                              {expandedEvidence[issue.id] ? 'Hide Evidence' : `Evidence (${issue.evidence?.length || 0})`}
                            </button>

                            {expandedEvidence[issue.id] && (
                              <div style={{ marginTop: '0.375rem' }}>
                                {issue.evidence?.map((ev, idx) => (
                                  <div key={idx} className="evidence-quote">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.15rem' }}>
                                      <span><strong>{ev.participant_id}</strong>:</span>
                                      <span style={{ color: 'var(--text-muted)' }}>{ev.source_field}</span>
                                    </div>
                                    <div style={{ color: 'var(--text-primary)', fontStyle: 'italic' }}>
                                      "{ev.quote}"
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {issue.resolution_notes && (
                            <div style={{ fontSize: '0.8125rem', color: '#86efac', background: '#113524', padding: '0.4rem 0.625rem', borderRadius: '4px', marginBottom: '0.625rem' }}>
                              <strong>Decision:</strong> {issue.resolution_notes}
                            </div>
                          )}

                          {resolvingIssueId === issue.id ? (
                            <div style={{ background: 'var(--bg-primary)', padding: '0.625rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                              <label className="form-label" htmlFor={`decision-notes-${issue.id}`}>Document Agreed Decision:</label>
                              <input
                                id={`decision-notes-${issue.id}`}
                                type="text"
                                className="form-input"
                                placeholder="e.g. Phone login excluded from v1; email login only"
                                value={resolutionNotes}
                                onChange={(e) => setResolutionNotes(e.target.value)}
                                style={{ marginBottom: '0.5rem' }}
                              />
                              <div style={{ display: 'flex', gap: '0.375rem' }}>
                                <button
                                  type="button"
                                  onClick={() => handleUpdateIssue(issue.id, 'resolved', resolutionNotes)}
                                  className="btn btn-success"
                                  style={{ padding: '0.35rem 0.625rem', fontSize: '0.75rem' }}
                                >
                                  Save Resolution
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setResolvingIssueId(null)}
                                  className="btn btn-secondary"
                                  style={{ padding: '0.35rem 0.625rem', fontSize: '0.75rem' }}
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', gap: '0.375rem', flexWrap: 'wrap' }}>
                              {issue.resolution_status === 'open' && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setResolvingIssueId(issue.id);
                                      setResolutionNotes('');
                                    }}
                                    className="btn btn-secondary"
                                    style={{ padding: '0.3rem 0.625rem', fontSize: '0.75rem', color: '#86efac' }}
                                  >
                                    Resolve
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleUpdateIssue(issue.id, 'dismissed', 'Marked out-of-scope by team')}
                                    className="btn btn-secondary"
                                    style={{ padding: '0.3rem 0.625rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}
                                  >
                                    Dismiss
                                  </button>
                                </>
                              )}
                              {issue.resolution_status !== 'open' && (
                                <button
                                  type="button"
                                  onClick={() => handleUpdateIssue(issue.id, 'open', null)}
                                  className="btn btn-secondary"
                                  style={{ padding: '0.3rem 0.625rem', fontSize: '0.75rem' }}
                                >
                                  Re-open
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {agreement && (
                    <div className="card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Shared Confirmed Agreement</h3>
                        <span className={`badge badge-${agreement.is_fully_confirmed ? 'resolved' : 'medium'}`}>
                          {agreement.is_fully_confirmed ? 'Confirmed' : 'Pending'}
                        </span>
                      </div>

                      <div style={{ marginBottom: '1rem' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.375rem', textTransform: 'uppercase' }}>
                          Agreed Requirements:
                        </div>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          {agreement.items?.map((item, idx) => (
                            <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.375rem', fontSize: '0.8125rem' }}>
                              <CheckCircle2 size={14} style={{ color: '#16a34a', flexShrink: 0, marginTop: '2px' }} />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {agreement.excluded_items?.length > 0 && (
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem', textTransform: 'uppercase' }}>
                            Confirmed Out of Scope:
                          </div>
                          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            {agreement.excluded_items.map((item, idx) => (
                              <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                                <XCircle size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.375rem' }}>
                          <strong>Confirmed By:</strong>{' '}
                          {agreement.confirmed_by?.length > 0 ? agreement.confirmed_by.join(', ') : 'None yet'}
                        </div>

                        <div style={{ display: 'flex', gap: '0.375rem', alignItems: 'center' }}>
                          <input
                            type="text"
                            className="form-input"
                            style={{ maxWidth: '200px', padding: '0.35rem 0.625rem', fontSize: '0.75rem' }}
                            placeholder="Your participant ID"
                            value={confirmingParticipant}
                            onChange={(e) => setConfirmingParticipant(e.target.value)}
                          />
                          <button
                            type="button"
                            onClick={handleConfirmAgreement}
                            disabled={!confirmingParticipant.trim()}
                            className="btn btn-success"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                          >
                            Confirm
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
