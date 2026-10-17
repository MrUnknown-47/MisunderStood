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
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Layers,
  CheckSquare,
  RefreshCw,
  Copy,
  ChevronDown,
  ChevronUp,
  Award,
} from 'lucide-react';

export default function App() {
  // Session & UI state
  const [session, setSession] = useState(null);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('misunderstood_session_id') || '');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeTab, setActiveTab] = useState('create'); // 'create', 'join'

  // Form states
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [joinCodeInput, setJoinCodeInput] = useState('');

  // Participant form
  const [participantName, setParticipantName] = useState('');
  const [participantId, setParticipantId] = useState('');
  const [interpretation, setInterpretation] = useState('');
  const [assumptions, setAssumptions] = useState('');
  const [successCriteria, setSuccessCriteria] = useState('');

  // Analysis & Issues state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [issues, setIssues] = useState([]);
  const [issueFilter, setIssueFilter] = useState('all'); // 'all', 'open', 'resolved', 'dismissed'
  const [expandedEvidence, setExpandedEvidence] = useState({});

  // Agreement & Bridge Test state
  const [agreement, setAgreement] = useState(null);
  const [bridgeTest, setBridgeTest] = useState(null);
  const [confirmingParticipant, setConfirmingParticipant] = useState('');
  const [resolvingIssueId, setResolvingIssueId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  // Load session on startup if stored
  useEffect(() => {
    if (sessionId) {
      loadSessionData(sessionId);
    }
  }, [sessionId]);

  const loadSessionData = async (id) => {
    try {
      setLoading(true);
      setErrorMessage('');
      const sessionData = await getSession(id);
      setSession(sessionData);

      // Load issues if session completed
      if (sessionData.status === 'completed') {
        const issuesData = await getIssues(id);
        setIssues(issuesData);
        const agreementData = await getAgreement(id).catch(() => null);
        setAgreement(agreementData);
        const bridgeData = await getBridgeTest(id).catch(() => null);
        setBridgeTest(bridgeData);
      }
    } catch (err) {
      console.error('Failed to load session:', err);
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

  const handleLoadDemoScenario = async () => {
    try {
      setLoading(true);
      setErrorMessage('');

      // 1. Create Hackathon Demo Session
      const demoSession = await createSession(
        'Prepare the application for launch',
        'Finish essential functionality and verify release readiness before product launch.'
      );
      setSession(demoSession);
      setSessionId(demoSession.id);
      localStorage.setItem('misunderstood_session_id', demoSession.id);

      // 2. Add Developer (Participant A)
      await submitParticipant(demoSession.id, {
        participant_id: 'participant-a',
        name: 'Alex (Lead Developer)',
        interpretation: 'Complete email and password login.',
        assumptions: 'PostgreSQL database will be used.',
        success_criteria: 'Unit tests pass and auth API returns 200.',
      });

      // 3. Add Project Manager (Participant B)
      await submitParticipant(demoSession.id, {
        participant_id: 'participant-b',
        name: 'Jordan (Project Manager)',
        interpretation: 'Complete email or phone login, registration, and password recovery.',
        assumptions: 'Self-service account recovery is mandatory for launch.',
        success_criteria: 'Users can sign up, log in with phone or email, and reset passwords without support tickets.',
      });

      // 4. Add Designer (Participant C)
      await submitParticipant(demoSession.id, {
        participant_id: 'participant-c',
        name: 'Taylor (Product Designer)',
        interpretation: 'Complete onboarding and mobile-responsive UI.',
        assumptions: 'All screen sizes must render seamlessly.',
        success_criteria: 'Onboarding walkthrough displays on first login with 100% responsive styling.',
      });

      // Refresh session
      await loadSessionData(demoSession.id);
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

      await loadSessionData(session.id);
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
      setAnalysisResult(result);
      setIssues(result.issues || []);

      // Load agreement and bridge metrics
      const agreementData = await getAgreement(session.id).catch(() => null);
      setAgreement(agreementData);
      const bridgeData = await getBridgeTest(session.id).catch(() => null);
      setBridgeTest(bridgeData);

      await loadSessionData(session.id);
    } catch (err) {
      console.error('Analysis failed:', err);
      setErrorMessage(err.message || 'AI Analysis failed. Please check participant submissions and try again.');
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

      // Refresh issues, agreement, and bridge test
      const updatedIssues = await getIssues(session.id);
      setIssues(updatedIssues);
      const updatedAgreement = await getAgreement(session.id);
      setAgreement(updatedAgreement);
      const updatedBridge = await getBridgeTest(session.id);
      setBridgeTest(updatedBridge);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to update issue status.');
    }
  };

  const handleConfirmAgreement = async () => {
    if (!session || !confirmingParticipant) return;
    try {
      const updatedAg = await confirmAgreement(session.id, confirmingParticipant);
      setAgreement(updatedAg);
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
    setAnalysisResult(null);
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
      {/* Header */}
      <header className="header-nav">
        <div className="header-content">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ fontSize: '1.75rem' }}>🌉</span>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.025em' }}>
                  MISUNDERSTOOD
                </h1>
                <span className="badge" style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c4b5fd', border: '1px solid rgba(139, 92, 246, 0.4)' }}>
                  Theme: Bridge the Gap
                </span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                Same conversation. Different realities.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {session && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-surface-elevated)', padding: '0.375rem 0.75rem', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Code:</span>
                <strong style={{ color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>{session.session_code}</strong>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(session.session_code)}
                  title="Copy code"
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
                >
                  <Copy size={13} />
                </button>
              </div>
            )}
            {session && (
              <button type="button" onClick={handleResetSession} className="btn btn-secondary" style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}>
                New Session
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container" style={{ flex: 1, paddingBottom: '3rem' }}>
        {/* Error Banner */}
        {errorMessage && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#fca5a5', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <strong style={{ display: 'block', marginBottom: '0.25rem' }}>Attention:</strong>
              <span>{errorMessage}</span>
            </div>
            <button type="button" onClick={() => setErrorMessage('')} style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer', fontWeight: 'bold' }}>✕</button>
          </div>
        )}

        {!session ? (
          /* ================================================================ */
          /* STAGE 1: CREATE OR JOIN SESSION                                  */
          /* ================================================================ */
          <div style={{ maxWidth: '680px', margin: '2rem auto' }}>
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--border)', marginBottom: '1.5rem', paddingBottom: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setActiveTab('create')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'create' ? 'var(--primary)' : 'var(--text-secondary)', fontWeight: 700, paddingBottom: '0.5rem', borderBottom: activeTab === 'create' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Create Task Session
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('join')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'join' ? 'var(--primary)' : 'var(--text-secondary)', fontWeight: 700, paddingBottom: '0.5rem', borderBottom: activeTab === 'join' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Join with Code
                </button>
              </div>

              {activeTab === 'create' ? (
                <form onSubmit={handleCreateSession}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="task-title">Task Instruction / Statement *</label>
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
                    <label className="form-label" htmlFor="task-desc">Context or Technical Details (Optional)</label>
                    <textarea
                      id="task-desc"
                      className="form-textarea"
                      rows={3}
                      placeholder="e.g. Milestone 1 scope, auth requirements, deadline, constraints..."
                      value={taskDesc}
                      onChange={(e) => setTaskDesc(e.target.value)}
                    />
                  </div>

                  <button type="submit" disabled={loading || !taskTitle.trim()} className="btn btn-primary" style={{ width: '100%', marginBottom: '1rem' }}>
                    {loading ? <span className="spinner" /> : <ArrowRight size={16} />}
                    Create Collaboration Session
                  </button>
                </form>
              ) : (
                <div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="join-code">Enter 6-Character Session Code</label>
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
                    onClick={() => setErrorMessage('For demonstration, please create a session or click the One-Click Demo button below.')}
                    className="btn btn-secondary"
                    style={{ width: '100%' }}
                  >
                    Lookup Session
                  </button>
                </div>
              )}

              {/* Devlympics Hackathon Preset Demo Button */}
              <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    🏆 HACKATHON EVALUATION PRESET
                  </span>
                  <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#fde047' }}>
                    Instant Demo
                  </span>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                  Instantly spins up the official scenario: <em>"Prepare application for launch"</em> pre-loaded with Developer, PM, and Designer responses.
                </p>
                <button
                  type="button"
                  onClick={handleLoadDemoScenario}
                  disabled={loading}
                  className="btn btn-secondary"
                  style={{ width: '100%', borderColor: '#8b5cf6', color: '#c4b5fd', background: 'rgba(139, 92, 246, 0.1)' }}
                >
                  <Sparkles size={16} />
                  Load Official 3-Party Demo Scenario
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* ================================================================ */
          /* STAGE 2-6: ACTIVE SESSION WORKFLOW                               */
          /* ================================================================ */
          <div>
            {/* Session Header Card */}
            <div className="card" style={{ marginBottom: '1.5rem', position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                    <span className={`badge badge-${session.status === 'completed' ? 'resolved' : session.status === 'failed' ? 'critical' : 'open'}`}>
                      Status: {session.status.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                      {session.participant_count} Participant(s) Joined
                    </span>
                  </div>
                  <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '0.375rem' }}>
                    {session.title}
                  </h2>
                  {session.description && (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>
                      {session.description}
                    </p>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', alignItems: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={handleRunAnalysis}
                    disabled={analyzing || (session.participant_count || 0) < 2}
                    className="btn btn-primary"
                    style={{ minWidth: '180px' }}
                  >
                    {analyzing ? (
                      <>
                        <span className="spinner" />
                        Analyzing with AI...
                      </>
                    ) : (
                      <>
                        <Sparkles size={16} />
                        {issues.length > 0 ? 'Re-run AI Analysis' : 'Run AI Analysis'}
                      </>
                    )}
                  </button>
                  {(session.participant_count || 0) < 2 && (
                    <span style={{ fontSize: '0.75rem', color: '#fca5a5' }}>
                      Requires ≥ 2 participant submissions
                    </span>
                  )}
                </div>
              </div>

              {/* Progress Indicator */}
              {analyzing && (
                <div style={{ marginTop: '1.25rem', padding: '0.875rem', background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span className="spinner" />
                  <span style={{ fontSize: '0.875rem', color: '#93c5fd' }}>
                    Objective mediator active: Comparing interpretations, verifying verbatim evidence, and detecting divergence...
                  </span>
                </div>
              )}
            </div>

            {/* Layout Grid: Left = Submissions / Right = Misunderstanding Map & Bridge Test */}
            <div style={{ display: 'grid', gridTemplateColumns: issues.length > 0 ? '1fr 1.6fr' : '1fr', gap: '1.5rem' }}>
              {/* Left Column: Participant Submissions */}
              <div>
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                    <Users size={18} style={{ color: 'var(--primary)' }} />
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 700 }}>Independent Submissions</h3>
                  </div>

                  <div style={{ background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.25)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.8125rem', color: '#93c5fd', marginBottom: '1.25rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                    <ShieldAlert size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      <strong>Blind Submission Mode:</strong> Participants cannot view other answers before submitting to prevent anchoring bias.
                    </span>
                  </div>

                  <form onSubmit={handleSubmitInterpretation}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-name">Your Name</label>
                        <input
                          id="participant-name"
                          type="text"
                          className="form-input"
                          placeholder="e.g. Morgan"
                          value={participantName}
                          onChange={(e) => setParticipantName(e.target.value)}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-id">Participant ID / Role</label>
                        <input
                          id="participant-id"
                          type="text"
                          className="form-input"
                          placeholder="e.g. dev-frontend"
                          value={participantId}
                          onChange={(e) => setParticipantId(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-interpretation">
                        What does this task require? (In your own words) *
                      </label>
                      <textarea
                        id="participant-interpretation"
                        className="form-textarea"
                        rows={3}
                        placeholder="Explain what must be finished for this task to count as complete..."
                        value={interpretation}
                        onChange={(e) => setInterpretation(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-assumptions">What assumptions are you making? (Optional)</label>
                      <input
                        id="participant-assumptions"
                        type="text"
                        className="form-input"
                        placeholder="e.g. DB schema already exists; OAuth not needed"
                        value={assumptions}
                        onChange={(e) => setAssumptions(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label" htmlFor="participant-success">Success Criteria / Definition of Done (Optional)</label>
                      <input
                        id="participant-success"
                        type="text"
                        className="form-input"
                        placeholder="e.g. CI pipeline green, all tests pass"
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
                      {loading ? <span className="spinner" /> : <CheckCircle2 size={16} />}
                      Submit My Interpretation
                    </button>
                  </form>
                </div>
              </div>

              {/* Right Column: The Misunderstanding Map & Bridge Test */}
              {issues.length > 0 && (
                <div>
                  {/* The Bridge Test Metric Widget */}
                  {bridgeTest && (
                    <div className="card-elevated" style={{ marginBottom: '1.5rem', border: '1px solid var(--accent-purple)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Award size={20} style={{ color: 'var(--accent-purple)' }} />
                          <h3 style={{ fontSize: '1.125rem', fontWeight: 800 }}>The Bridge Test</h3>
                        </div>
                        <span className={`badge badge-${bridgeTest.bridge_status === 'bridged' ? 'resolved' : bridgeTest.bridge_status === 'in_progress' ? 'medium' : 'critical'}`}>
                          {bridgeTest.bridge_status.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>

                      {/* Progress Bar */}
                      <div className="progress-bar-bg">
                        <div className="progress-bar-fill" style={{ width: `${bridgeTest.resolution_percentage}%` }} />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem', marginTop: '0.75rem', textAlign: 'center' }}>
                        <div style={{ background: 'var(--bg-surface)', padding: '0.625rem', borderRadius: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Detected</span>
                          <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>{bridgeTest.initial_issues_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-surface)', padding: '0.625rem', borderRadius: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#6ee7b7' }}>Resolved</span>
                          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10b981' }}>{bridgeTest.resolved_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-surface)', padding: '0.625rem', borderRadius: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Dismissed</span>
                          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-muted)' }}>{bridgeTest.dismissed_count}</div>
                        </div>
                        <div style={{ background: 'var(--bg-surface)', padding: '0.625rem', borderRadius: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#fca5a5' }}>Open Gaps</span>
                          <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ef4444' }}>{bridgeTest.open_count}</div>
                        </div>
                      </div>

                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem', fontStyle: 'italic' }}>
                        * {bridgeTest.disclaimer}
                      </p>
                    </div>
                  )}

                  {/* Misunderstanding Map Issues */}
                  <div className="card" style={{ marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Layers size={18} style={{ color: 'var(--primary)' }} />
                        <h3 style={{ fontSize: '1.125rem', fontWeight: 700 }}>The Misunderstanding Map</h3>
                      </div>

                      {/* Filter Tabs */}
                      <div style={{ display: 'flex', gap: '0.375rem', background: 'var(--bg-primary)', padding: '0.25rem', borderRadius: '8px' }}>
                        {['all', 'open', 'resolved', 'dismissed'].map((f) => (
                          <button
                            key={f}
                            type="button"
                            onClick={() => setIssueFilter(f)}
                            style={{
                              background: issueFilter === f ? 'var(--bg-surface-elevated)' : 'transparent',
                              border: 'none',
                              color: issueFilter === f ? 'var(--text-primary)' : 'var(--text-muted)',
                              padding: '0.25rem 0.625rem',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              textTransform: 'capitalize',
                            }}
                          >
                            {f}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Issue Cards */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {filteredIssues.map((issue) => (
                        <div
                          key={issue.id}
                          className="card-elevated"
                          style={{
                            borderLeft: `4px solid ${
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
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.5rem' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                              <span className={`badge badge-${issue.priority}`}>
                                Priority: {issue.priority}
                              </span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                                {issue.type.replace('_', ' ')}
                              </span>
                            </div>
                            <span className={`badge badge-${issue.resolution_status}`}>
                              {issue.resolution_status}
                            </span>
                          </div>

                          <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.375rem' }}>
                            {issue.title}
                          </h4>
                          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                            {issue.description}
                          </p>

                          {/* Actionable Neutral Clarification Question */}
                          <div style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', padding: '0.75rem', borderRadius: '8px', marginBottom: '0.75rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: '#93c5fd', fontSize: '0.8125rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                              <HelpCircle size={14} />
                              Clarification Question for Team:
                            </div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                              "{issue.clarification_question}"
                            </div>
                          </div>

                          {/* Verbatim Evidence Accordion */}
                          <div style={{ marginBottom: '0.75rem' }}>
                            <button
                              type="button"
                              onClick={() => toggleEvidence(issue.id)}
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem', padding: 0 }}
                            >
                              {expandedEvidence[issue.id] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              {expandedEvidence[issue.id] ? 'Hide Verified Evidence' : `Show Verified Evidence (${issue.evidence?.length || 0})`}
                            </button>

                            {expandedEvidence[issue.id] && (
                              <div style={{ marginTop: '0.5rem' }}>
                                {issue.evidence?.map((ev, idx) => (
                                  <div key={idx} className="evidence-quote">
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                      <span><strong>{ev.participant_id}</strong>:</span>
                                      <span style={{ fontStyle: 'italic' }}>field: {ev.source_field}</span>
                                    </div>
                                    <div style={{ fontStyle: 'italic', color: 'var(--text-primary)' }}>
                                      "{ev.quote}"
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Existing Resolution Notes if resolved */}
                          {issue.resolution_notes && (
                            <div style={{ fontSize: '0.8125rem', color: '#6ee7b7', background: 'rgba(16, 185, 129, 0.1)', padding: '0.5rem 0.75rem', borderRadius: '6px', marginBottom: '0.75rem' }}>
                              <strong>Agreed Decision:</strong> {issue.resolution_notes}
                            </div>
                          )}

                          {/* Action Controls */}
                          {resolvingIssueId === issue.id ? (
                            <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
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
                              <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button
                                  type="button"
                                  onClick={() => handleUpdateIssue(issue.id, 'resolved', resolutionNotes)}
                                  className="btn btn-success"
                                  style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                                >
                                  Save Resolution
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setResolvingIssueId(null)}
                                  className="btn btn-secondary"
                                  style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                              {issue.resolution_status === 'open' && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setResolvingIssueId(issue.id);
                                      setResolutionNotes('');
                                    }}
                                    className="btn btn-secondary"
                                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', color: '#6ee7b7' }}
                                  >
                                    <CheckCircle2 size={14} />
                                    Resolve Issue
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleUpdateIssue(issue.id, 'dismissed', 'Marked out-of-scope by team')}
                                    className="btn btn-secondary"
                                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}
                                  >
                                    <XCircle size={14} />
                                    Dismiss (Out of Scope)
                                  </button>
                                </>
                              )}
                              {issue.resolution_status !== 'open' && (
                                <button
                                  type="button"
                                  onClick={() => handleUpdateIssue(issue.id, 'open', null)}
                                  className="btn btn-secondary"
                                  style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                                >
                                  <RefreshCw size={13} />
                                  Re-open Issue
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Shared Agreement & Confirmation Section */}
                  {agreement && (
                    <div className="card" style={{ marginBottom: '1.5rem', border: '1px solid #10b981' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <CheckSquare size={20} style={{ color: '#10b981' }} />
                          <h3 style={{ fontSize: '1.125rem', fontWeight: 800 }}>Shared Confirmed Agreement</h3>
                        </div>
                        <span className={`badge badge-${agreement.is_fully_confirmed ? 'resolved' : 'medium'}`}>
                          {agreement.is_fully_confirmed ? 'Fully Confirmed' : 'Confirmation Pending'}
                        </span>
                      </div>

                      {/* Checklist */}
                      <div style={{ marginBottom: '1.25rem' }}>
                        <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                          AGREED DELIVERABLES & REQUIREMENTS:
                        </h4>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                          {agreement.items?.map((item, idx) => (
                            <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.875rem' }}>
                              <CheckCircle2 size={16} style={{ color: '#10b981', flexShrink: 0, marginTop: '2px' }} />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Excluded Items */}
                      {agreement.excluded_items?.length > 0 && (
                        <div style={{ marginBottom: '1.25rem' }}>
                          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                            CONFIRMED OUT OF SCOPE / DEFERRED:
                          </h4>
                          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                            {agreement.excluded_items.map((item, idx) => (
                              <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                <XCircle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Multi-Party Confirmation Bar */}
                      <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.875rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                          <strong>Confirmed By:</strong>{' '}
                          {agreement.confirmed_by?.length > 0 ? agreement.confirmed_by.join(', ') : 'No confirmations yet.'}
                        </div>

                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <input
                            type="text"
                            className="form-input"
                            style={{ maxWidth: '240px', padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                            placeholder="Enter your participant ID"
                            value={confirmingParticipant}
                            onChange={(e) => setConfirmingParticipant(e.target.value)}
                          />
                          <button
                            type="button"
                            onClick={handleConfirmAgreement}
                            disabled={!confirmingParticipant.trim()}
                            className="btn btn-success"
                            style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                          >
                            <CheckCircle2 size={14} />
                            Confirm Agreement
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
