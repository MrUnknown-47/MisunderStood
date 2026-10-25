import React, { useState, useEffect } from 'react';
import {
  createSession,
  joinSession,
  getSession,
  getSessionParticipants,
  getSessionStatus,
  getMyInterpretation,
  submitInterpretation,
  submitParticipant,
  triggerAnalysis,
  getIssues,
  updateIssueStatus,
  getAgreement,
  confirmAgreement,
  getBridgeTest,
  getSessionAuth,
  clearSessionAuth,
  getStoredSessionId,
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
  Check,
  ArrowRight,
  Lock,
  Sparkles,
  FileText,
  Layers,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';

export default function App() {
  const [session, setSession] = useState(null);
  const [sessionId, setSessionId] = useState(getStoredSessionId);
  const [auth, setAuth] = useState(() => getSessionAuth(sessionId));
  const [participants, setParticipants] = useState([]);
  const [sessionStatus, setSessionStatus] = useState(null);
  const [mySubmission, setMySubmission] = useState(null);
  const [showMySubmission, setShowMySubmission] = useState(true);
  const [mySubmissionLoading, setMySubmissionLoading] = useState(false);
  const [mySubmissionError, setMySubmissionError] = useState('');

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [copySuccess, setCopySuccess] = useState(false);

  // Tab navigation
  // When no session: 'create' | 'join' | 'demo'
  // When session active: 'overview' | 'interpret' | 'issues' | 'agreement' | 'bridge'
  const [activeTab, setActiveTab] = useState('create');

  // Create session form inputs
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDesc, setTaskDesc] = useState('');
  const [taskContext, setTaskContext] = useState('');
  const [creatorName, setCreatorName] = useState('');
  const [minParticipants, setMinParticipants] = useState(2);

  // Join session form inputs
  const [joinCodeInput, setJoinCodeInput] = useState('');
  const [joinDisplayName, setJoinDisplayName] = useState('');

  // Participant submission inputs
  const [participantName, setParticipantName] = useState('');
  const [participantId, setParticipantId] = useState('');
  const [interpretation, setInterpretation] = useState('');
  const [assumptions, setAssumptions] = useState('');
  const [successCriteria, setSuccessCriteria] = useState('');

  // Issues & Agreement state
  const [issues, setIssues] = useState([]);
  const [issueFilter, setIssueFilter] = useState('all');
  const [expandedEvidence, setExpandedEvidence] = useState({});
  const [agreement, setAgreement] = useState(null);
  const [bridgeTest, setBridgeTest] = useState(null);
  const [confirmingParticipant, setConfirmingParticipant] = useState('');
  const [resolvingIssueId, setResolvingIssueId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  // Load session whenever sessionId changes
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

      const currentAuth = getSessionAuth(id);
      setAuth(currentAuth);

      // Attempt authenticated queries if token exists
      if (currentAuth && currentAuth.token) {
        try {
          const parts = await getSessionParticipants(id);
          setParticipants(parts.participants || []);
        } catch {
          setParticipants([]);
        }

        try {
          const stat = await getSessionStatus(id);
          setSessionStatus(stat);
          if (stat?.user_has_submitted) {
            if (stat.user_interpretation) {
              setMySubmission({
                interpretation: stat.user_interpretation,
                assumptions: stat.user_assumptions,
                success_criteria: stat.user_success_criteria,
              });
            } else {
              const myData = await getMyInterpretation(id).catch(() => null);
              if (myData && myData.has_submitted) {
                setMySubmission(myData);
              }
            }
          } else {
            setMySubmission(null);
          }
        } catch {
          setSessionStatus(null);
          setMySubmission(null);
        }
      }

      // Load issues and downstream artifacts if completed or reviewing
      if (data.status === 'completed' || data.status === 'reviewing_issues') {
        const issuesData = await getIssues(id).catch(() => []);
        setIssues(issuesData || []);
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
      setSuccessMessage('');

      const newSession = await createSession({
        title: taskTitle.trim(),
        description: taskDesc.trim() || null,
        context: taskContext.trim() || null,
        creator_name: creatorName.trim() || null,
        min_participants: Number(minParticipants) || 2,
      });

      setSession(newSession);
      setSessionId(newSession.id);
      const newAuth = getSessionAuth(newSession.id);
      setAuth(newAuth);

      setTaskTitle('');
      setTaskDesc('');
      setTaskContext('');
      setCreatorName('');

      setActiveTab('overview');
      setSuccessMessage('Session created successfully! Share the join code with your team.');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create session.');
    } finally {
      setLoading(false);
    }
  };

  const handleJoinSession = async (e) => {
    e?.preventDefault();
    const code = joinCodeInput.trim().toUpperCase();
    const name = joinDisplayName.trim();

    if (!code || !name) {
      setErrorMessage('Please enter both the join code and your display name.');
      return;
    }

    try {
      setLoading(true);
      setErrorMessage('');
      setSuccessMessage('');

      const joinResult = await joinSession(code, name);
      setSessionId(joinResult.session_id);
      const joinedAuth = getSessionAuth(joinResult.session_id);
      setAuth(joinedAuth);

      await loadSession(joinResult.session_id);
      setJoinCodeInput('');
      setJoinDisplayName('');
      setActiveTab('interpret');
      setSuccessMessage(`Joined session as "${name}"! Submit your independent interpretation below.`);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to join session. Please verify the code.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    try {
      setLoading(true);
      setErrorMessage('');
      setSuccessMessage('');

      const demoSession = await createSession(
        'Prepare the application for launch',
        'Finish essential functionality and verify release readiness before product launch.'
      );

      setSession(demoSession);
      setSessionId(demoSession.id);
      setAuth(getSessionAuth(demoSession.id));

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
      setActiveTab('overview');
      setSuccessMessage('Official 3-party demo loaded with divergent realities! Click "Run AI Analysis" to inspect gaps.');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to initialize demo scenario.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitInterpretation = async (e) => {
    e.preventDefault();
    if (!session || !interpretation.trim()) return;

    try {
      setLoading(true);
      setErrorMessage('');
      setSuccessMessage('');

      if (auth && auth.token) {
        await submitInterpretation(session.id, {
          response_text: interpretation.trim(),
          assumptions: assumptions.trim() || null,
          success_criteria: successCriteria.trim() || null,
        });
        setMySubmission({
          interpretation: interpretation.trim(),
          assumptions: assumptions.trim() || null,
          success_criteria: successCriteria.trim() || null,
        });
        setShowMySubmission(true);
      } else {
        const pid = (participantId.trim() || participantName.trim() || `participant-${Date.now()}`)
          .toLowerCase()
          .replace(/\s+/g, '-');

        await submitParticipant(session.id, {
          participant_id: pid,
          name: participantName.trim() || pid,
          interpretation: interpretation.trim(),
          assumptions: assumptions.trim() || null,
          success_criteria: successCriteria.trim() || null,
        });
        setMySubmission({
          interpretation: interpretation.trim(),
          assumptions: assumptions.trim() || null,
          success_criteria: successCriteria.trim() || null,
        });
        setShowMySubmission(true);
      }

      setParticipantName('');
      setParticipantId('');
      setInterpretation('');
      setAssumptions('');
      setSuccessCriteria('');

      await loadSession(session.id);
      setSuccessMessage('Your interpretation has been recorded securely.');
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
      setSuccessMessage('');

      const result = await triggerAnalysis(session.id);
      setIssues(result.issues || []);

      const agreementData = await getAgreement(session.id).catch(() => null);
      setAgreement(agreementData);
      const bridgeData = await getBridgeTest(session.id).catch(() => null);
      setBridgeTest(bridgeData);

      await loadSession(session.id);
      setActiveTab('issues');
      setSuccessMessage(`Analysis complete! Identified ${result.issue_count || (result.issues ? result.issues.length : 0)} misunderstandings.`);
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

  const handleConfirmAgreement = async (pidToConfirm) => {
    if (!session) return;
    const targetId = (pidToConfirm || confirmingParticipant).trim();
    if (!targetId) return;

    try {
      const updated = await confirmAgreement(session.id, targetId);
      setAgreement(updated);
      const updatedBridge = await getBridgeTest(session.id);
      setBridgeTest(updatedBridge);
      setConfirmingParticipant('');
      setSuccessMessage(`Agreement confirmed for ${targetId}!`);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to confirm agreement.');
    }
  };

  const handleResetSession = () => {
    if (sessionId) {
      clearSessionAuth(sessionId);
    }
    setSession(null);
    setSessionId('');
    setAuth(null);
    setParticipants([]);
    setSessionStatus(null);
    setMySubmission(null);
    setShowMySubmission(true);
    setMySubmissionError('');
    setIssues([]);
    setAgreement(null);
    setBridgeTest(null);
    setErrorMessage('');
    setSuccessMessage('');
    setActiveTab('create');
  };

  const handleReloadMySubmission = async () => {
    if (!session?.id) return;
    try {
      setMySubmissionLoading(true);
      setMySubmissionError('');
      const data = await getMyInterpretation(session.id);
      if (data && data.has_submitted) {
        setMySubmission(data);
      }
    } catch (err) {
      setMySubmissionError(err.message || 'Unable to load your submission.');
    } finally {
      setMySubmissionLoading(false);
    }
  };

  const formatListOrText = (val) => {
    if (!val) return null;
    if (Array.isArray(val)) return val.join(' • ');
    try {
      const parsed = JSON.parse(val);
      if (Array.isArray(parsed)) return parsed.join(' • ');
      return String(parsed);
    } catch {
      return String(val);
    }
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

  const currentUserSubmitted = sessionStatus?.user_has_submitted || false;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header */}
      <header className="header-nav">
        <div className="header-content">
          <div className="brand-logo" onClick={() => !session && setActiveTab('create')} style={{ cursor: 'pointer' }}>
            <div className="brand-icon">
              <span className="brand-dot-coral" />
              <span className="brand-dot-mint" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.01em' }}>
                  MISUNDERSTOOD
                </span>
                <span className="badge" style={{ background: '#1e293b', color: '#94a3b8' }}>
                  Bridge the Gap
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Same conversation. Different realities.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', flexWrap: 'wrap' }}>
            {session && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', background: 'var(--bg-primary)', padding: '0.35rem 0.625rem', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.8125rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Code:</span>
                <strong style={{ color: '#38bdf8', fontFamily: 'monospace', letterSpacing: '0.04em' }}>
                  {session.join_code || session.session_code}
                </strong>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(session.join_code || session.session_code);
                    setCopySuccess(true);
                    setTimeout(() => setCopySuccess(false), 2000);
                  }}
                  title="Copy join code"
                  style={{ background: 'transparent', border: 'none', color: copySuccess ? '#86efac' : 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex' }}
                >
                  {copySuccess ? <Check size={13} /> : <Copy size={13} />}
                </button>
              </div>
            )}

            {auth && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', background: 'var(--bg-surface-elevated)', padding: '0.35rem 0.625rem', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>You:</span>
                <strong style={{ color: 'var(--color-mint)' }}>{auth.displayName}</strong>
                <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>({auth.role})</span>
              </div>
            )}

            {session ? (
              <button
                type="button"
                onClick={handleResetSession}
                className="btn btn-secondary"
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}
              >
                Switch Session
              </button>
            ) : (
              <button
                type="button"
                onClick={handleLoadDemo}
                disabled={loading}
                className="btn btn-secondary"
                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}
              >
                <Sparkles size={14} style={{ color: 'var(--color-coral)' }} />
                1-Click Demo
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="container" style={{ flex: 1, paddingBottom: '3rem' }}>
        {errorMessage && (
          <div style={{ background: '#451a1a', border: '1px solid #7f1d1d', color: '#fca5a5', padding: '0.875rem 1rem', borderRadius: '6px', marginBottom: '1.25rem', display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1, fontSize: '0.875rem' }}>{errorMessage}</div>
            <button
              type="button"
              onClick={() => setErrorMessage('')}
              style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        )}

        {successMessage && (
          <div style={{ background: 'var(--color-mint-soft)', border: '1px solid rgba(175, 231, 206, 0.3)', color: '#86efac', padding: '0.875rem 1rem', borderRadius: '6px', marginBottom: '1.25rem', display: 'flex', alignItems: 'flex-start', gap: '0.625rem' }}>
            <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#16a34a' }} />
            <div style={{ flex: 1, fontSize: '0.875rem' }}>{successMessage}</div>
            <button
              type="button"
              onClick={() => setSuccessMessage('')}
              style={{ background: 'transparent', border: 'none', color: '#86efac', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        )}

        {/* STEP PROGRESSION BAR (When Session is Active) */}
        {session && (
          <div className="step-nav">
            <button
              type="button"
              onClick={() => setActiveTab('overview')}
              className={`step-pill ${activeTab === 'overview' ? 'active' : ''}`}
            >
              <span className="step-badge-circle done">
                <Check size={12} strokeWidth={3} />
              </span>
              <span>1. Overview</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('interpret')}
              className={`step-pill ${activeTab === 'interpret' ? 'active' : ''}`}
            >
              <span className={`step-badge-circle ${currentUserSubmitted ? 'done' : ''}`}>
                {currentUserSubmitted ? <Check size={12} strokeWidth={3} /> : '2'}
              </span>
              <span>2. Blind Submission</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('issues')}
              className={`step-pill ${activeTab === 'issues' ? 'active' : ''}`}
            >
              <span className={`step-badge-circle ${issues.length > 0 ? 'done' : ''}`}>
                {issues.length > 0 ? <Check size={12} strokeWidth={3} /> : '3'}
              </span>
              <span>3. Misunderstandings ({issues.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('agreement')}
              className={`step-pill ${activeTab === 'agreement' ? 'active' : ''}`}
            >
              <span className={`step-badge-circle ${agreement?.is_fully_confirmed ? 'done' : ''}`}>
                {agreement?.is_fully_confirmed ? <Check size={12} strokeWidth={3} /> : '4'}
              </span>
              <span>4. Agreement</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('bridge')}
              className={`step-pill ${activeTab === 'bridge' ? 'active' : ''}`}
            >
              <span className={`step-badge-circle ${bridgeTest?.bridge_status === 'bridged' ? 'done' : ''}`}>
                {bridgeTest?.bridge_status === 'bridged' ? <Check size={12} strokeWidth={3} /> : '5'}
              </span>
              <span>5. Bridge Test</span>
            </button>
          </div>
        )}

        {/* STATE A: NO ACTIVE SESSION */}
        {!session ? (
          <div style={{ maxWidth: '640px', margin: '2rem auto' }}>
            <div className="card">
              {/* Tab Selector */}
              <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--border)', marginBottom: '1.25rem', paddingBottom: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setActiveTab('create')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'create' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: 600, paddingBottom: '0.5rem', borderBottom: activeTab === 'create' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Create Session
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('join')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'join' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: 600, paddingBottom: '0.5rem', borderBottom: activeTab === 'join' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Join with Code
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('demo')}
                  style={{ background: 'transparent', border: 'none', color: activeTab === 'demo' ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: 600, paddingBottom: '0.5rem', borderBottom: activeTab === 'demo' ? '2px solid var(--primary)' : 'none', cursor: 'pointer' }}
                >
                  Preset Demo
                </button>
              </div>

              {/* CREATE SESSION FORM */}
              {activeTab === 'create' && (
                <form onSubmit={handleCreateSession}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="task-title">
                      Task Instruction or Goal *
                    </label>
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
                    <label className="form-label" htmlFor="task-desc">
                      Scope & Details (Optional)
                    </label>
                    <textarea
                      id="task-desc"
                      className="form-textarea"
                      rows={2}
                      placeholder="e.g. Finish core functionality and verify release readiness before product launch."
                      value={taskDesc}
                      onChange={(e) => setTaskDesc(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="task-context">
                      Background Context (Optional)
                    </label>
                    <input
                      id="task-context"
                      type="text"
                      className="form-input"
                      placeholder="e.g. V1 launch, web client + PostgreSQL backend"
                      value={taskContext}
                      onChange={(e) => setTaskContext(e.target.value)}
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '0.75rem' }}>
                    <div className="form-group">
                      <label className="form-label" htmlFor="creator-name">
                        Your Display Name (Optional)
                      </label>
                      <input
                        id="creator-name"
                        type="text"
                        className="form-input"
                        placeholder="e.g. Sarah (Lead Dev)"
                        value={creatorName}
                        onChange={(e) => setCreatorName(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label" htmlFor="min-participants">
                        Min Participants
                      </label>
                      <input
                        id="min-participants"
                        type="number"
                        min={2}
                        max={10}
                        className="form-input"
                        value={minParticipants}
                        onChange={(e) => setMinParticipants(e.target.value)}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !taskTitle.trim()}
                    className="btn btn-primary"
                    style={{ width: '100%', marginTop: '0.5rem' }}
                  >
                    {loading ? <span className="spinner" /> : 'Create Session'}
                  </button>
                </form>
              )}

              {/* JOIN SESSION WITH CODE */}
              {activeTab === 'join' && (
                <form onSubmit={handleJoinSession}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="join-code">
                      Session Join Code *
                    </label>
                    <input
                      id="join-code"
                      type="text"
                      className="form-input"
                      placeholder="e.g. GAP-7K3M9P"
                      value={joinCodeInput}
                      onChange={(e) => setJoinCodeInput(e.target.value.toUpperCase().replace(/\s/g, ''))}
                      maxLength={14}
                      style={{ fontFamily: 'monospace', letterSpacing: '0.08em', fontWeight: 700 }}
                      required
                    />
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      Enter the alphanumeric code provided by your session creator.
                    </span>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="join-name">
                      Your Display Name *
                    </label>
                    <input
                      id="join-name"
                      type="text"
                      className="form-input"
                      placeholder="e.g. Alex (Engineering)"
                      value={joinDisplayName}
                      onChange={(e) => setJoinDisplayName(e.target.value)}
                      required
                    />
                  </div>

                  <div className="callout callout-info" style={{ marginTop: '0.75rem' }}>
                    <Lock size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span style={{ fontSize: '0.75rem' }}>
                      Joining creates a secure participant session. Your interpretation will remain private
                      until everyone has submitted.
                    </span>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !joinCodeInput.trim() || !joinDisplayName.trim()}
                    className="btn btn-primary"
                    style={{ width: '100%', marginTop: '0.5rem' }}
                  >
                    {loading ? <span className="spinner" /> : 'Join Session'}
                  </button>
                </form>
              )}

              {/* 1-CLICK PRESET DEMO CARD */}
              {activeTab === 'demo' && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      "Prepare the application for launch"
                    </span>
                    <span className="badge" style={{ background: '#252a3b', color: '#94a3b8' }}>
                      3 Realities
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.875rem' }}>
                    Simulates a classic cross-functional team disconnect:
                  </p>

                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem', fontSize: '0.8125rem' }}>
                    <li style={{ background: 'var(--bg-primary)', padding: '0.5rem 0.75rem', borderRadius: '4px', borderLeft: '3px solid #38bdf8' }}>
                      <strong>Alex (Lead Dev):</strong> Assumes email+password auth and Postgres database.
                    </li>
                    <li style={{ background: 'var(--bg-primary)', padding: '0.5rem 0.75rem', borderRadius: '4px', borderLeft: '3px solid var(--color-coral)' }}>
                      <strong>Jordan (PM):</strong> Assumes phone login, self-service registration, and password recovery.
                    </li>
                    <li style={{ background: 'var(--bg-primary)', padding: '0.5rem 0.75rem', borderRadius: '4px', borderLeft: '3px solid var(--color-mint)' }}>
                      <strong>Taylor (Designer):</strong> Assumes onboarding tutorial walkthrough and mobile responsive layout.
                    </li>
                  </ul>

                  <button
                    type="button"
                    onClick={handleLoadDemo}
                    disabled={loading}
                    className="btn btn-primary"
                    style={{ width: '100%' }}
                  >
                    {loading ? <span className="spinner" /> : 'Load Official 3-Party Demo'}
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* STATE B: ACTIVE SESSION */
          <div>
            {/* TAB 1: OVERVIEW & WAITING ROOM */}
            {activeTab === 'overview' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.25rem', alignItems: 'start' }}>
                <div className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                        <span className={`badge badge-${session.status === 'completed' ? 'resolved' : session.status === 'failed' ? 'critical' : 'open'}`}>
                          {session.status.replace('_', ' ')}
                        </span>
                        <span style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                          {session.participant_count} submission(s)
                        </span>
                      </div>
                      <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.25rem' }}>
                        {session.title}
                      </h2>
                      {session.description && (
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                          {session.description}
                        </p>
                      )}
                      {session.context && (
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                          <strong>Context:</strong> {session.context}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="callout callout-info">
                    <Lock size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <div>
                      <strong>Blind Submission Guarantee:</strong> Responses stay strictly confidential until
                      everyone submits. Team members cannot read peer answers during the collection phase.
                    </div>
                  </div>

                  <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => setActiveTab('interpret')}
                      className="btn btn-primary"
                    >
                      <FileText size={15} />
                      {currentUserSubmitted ? 'View My Submission' : 'Submit My Interpretation'}
                    </button>

                    <button
                      type="button"
                      onClick={handleRunAnalysis}
                      disabled={analyzing || (session.participant_count || 0) < 2}
                      className="btn btn-secondary"
                    >
                      {analyzing ? (
                        <>
                          <span className="spinner" />
                          Analyzing Divergent Realities...
                        </>
                      ) : (
                        <>
                          <Sparkles size={15} style={{ color: 'var(--color-coral)' }} />
                          {issues.length > 0 ? 'Re-run Analysis' : 'Run AI Analysis'}
                        </>
                      )}
                    </button>
                  </div>

                  {(session.participant_count || 0) < 2 && (
                    <p style={{ fontSize: '0.75rem', color: '#fca5a5', marginTop: '0.5rem' }}>
                      At least 2 participant submissions are required to run comparative analysis.
                    </p>
                  )}
                </div>

                {/* Session Waiting Room / Participants */}
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Users size={16} style={{ color: 'var(--primary)' }} />
                      <h3 style={{ fontSize: '0.9375rem', fontWeight: 600 }}>Team Waiting Room</h3>
                    </div>
                    <span className="badge" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                      Min: {session.min_participants || 2}
                    </span>
                  </div>

                  {/* Dynamic Waiting Room Guidance */}
                  {((participants.length > 0 ? participants.length : (sessionStatus?.participant_count ?? (session.participant_count || 0))) < 2) ? (
                    <div
                      style={{
                        background: 'rgba(244, 63, 94, 0.08)',
                        border: '1px solid rgba(244, 63, 94, 0.25)',
                        borderRadius: '6px',
                        padding: '0.75rem 0.875rem',
                        marginBottom: '0.875rem',
                        fontSize: '0.8125rem',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                        <Users size={16} style={{ color: 'var(--color-coral)', flexShrink: 0, marginTop: '2px' }} />
                        <div>
                          <strong style={{ color: 'var(--text-primary)' }}>
                            Waiting for team members ({participants.length > 0 ? participants.length : (sessionStatus?.participant_count ?? 1)} of {session.min_participants || 2} joined)
                          </strong>
                          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', lineHeight: 1.4 }}>
                            At least 2 participant submissions are needed to uncover misunderstandings.
                          </p>
                          <div style={{ marginTop: '0.5rem', background: 'var(--bg-primary)', padding: '0.5rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border)' }}>
                            <strong style={{ fontSize: '0.75rem', color: '#38bdf8' }}>Testing this alone right now?</strong>
                            <ol style={{ paddingLeft: '1.25rem', margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: 1.45 }}>
                              <li>Open a second browser window in <strong>Incognito / Private</strong> mode.</li>
                              <li>Join with session code <strong style={{ color: '#38bdf8', fontFamily: 'monospace' }}>{session.join_code || session.session_code}</strong>.</li>
                            </ol>
                          </div>
                          <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                            Or click <button type="button" onClick={handleLoadDemo} style={{ background: 'transparent', border: 'none', color: 'var(--color-coral)', textDecoration: 'underline', cursor: 'pointer', padding: 0, fontWeight: 600 }}>1-Click Demo</button> in the top bar to test the full 3-party flow immediately.
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        background: 'rgba(175, 231, 206, 0.08)',
                        border: '1px solid rgba(175, 231, 206, 0.25)',
                        borderRadius: '6px',
                        padding: '0.625rem 0.75rem',
                        marginBottom: '0.875rem',
                        fontSize: '0.75rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        color: 'var(--color-mint-dark)',
                      }}
                    >
                      <CheckCircle2 size={15} style={{ color: '#16a34a', flexShrink: 0 }} />
                      <span>{participants.length || sessionStatus?.participant_count || session.participant_count} participants joined. Ready for independent submissions.</span>
                    </div>
                  )}

                  {participants.length > 0 ? (
                    <div>
                      {participants.map((p) => (
                        <div key={p.id} className="participant-item">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontWeight: 600 }}>{p.display_name}</span>
                            {p.role === 'creator' && (
                              <span className="badge" style={{ background: '#1e293b', color: '#38bdf8', fontSize: '0.625rem' }}>
                                Creator
                              </span>
                            )}
                          </div>
                          <div>
                            {p.has_submitted ? (
                              <span className="badge badge-resolved" style={{ fontSize: '0.6875rem' }}>
                                ✓ Submitted
                              </span>
                            ) : (
                              <span className="badge" style={{ background: '#262c36', color: '#94a3b8', fontSize: '0.6875rem' }}>
                                Pending
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '1rem 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                      <p style={{ marginBottom: '0.5rem' }}>
                        {session.participant_count} total submission(s) recorded.
                      </p>
                      <p style={{ fontSize: '0.75rem' }}>
                        Share the join code <strong style={{ color: '#38bdf8' }}>{session.join_code || session.session_code}</strong> with teammates.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: BLIND INTERPRETATION SUBMISSION */}
            {activeTab === 'interpret' && (
              <div style={{ maxWidth: '680px', margin: '0 auto' }}>
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <ShieldCheck size={18} style={{ color: 'var(--color-mint)' }} />
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Blind Interpretation</h3>
                  </div>

                  <div className="callout callout-mint">
                    <Lock size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span style={{ fontSize: '0.8125rem' }}>
                      Submit your perspective independently. Peer responses remain hidden to ensure
                      unbiased, authentic interpretations.
                    </span>
                  </div>

                  {currentUserSubmitted ? (
                    <div>
                      <div style={{ background: 'var(--bg-primary)', padding: '1.25rem', borderRadius: '8px', border: '1px solid rgba(175, 231, 206, 0.3)', textAlign: 'center', marginTop: '1rem' }}>
                        <CheckCircle2 size={32} style={{ color: 'var(--color-mint-dark)', margin: '0 auto 0.5rem auto' }} />
                        <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                          Interpretation Submitted!
                        </h4>
                        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.875rem' }}>
                          Your response has been securely persisted. Peer responses remain private until everyone has submitted.
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            onClick={() => setShowMySubmission(!showMySubmission)}
                            className="btn btn-secondary"
                            style={{ fontSize: '0.8125rem', padding: '0.4rem 0.85rem' }}
                          >
                            {showMySubmission ? (
                              <>
                                <ChevronUp size={14} /> Hide My Submission
                              </>
                            ) : (
                              <>
                                <ChevronDown size={14} /> View My Submission
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => setActiveTab('issues')}
                            className="btn btn-primary"
                            style={{ fontSize: '0.8125rem', padding: '0.4rem 0.85rem' }}
                          >
                            Proceed to Misunderstandings <ArrowRight size={14} />
                          </button>
                        </div>
                      </div>

                      {/* Read-Only Collapsible Panel for Participant's Own Persisted Submission */}
                      {showMySubmission && (
                        <div
                          className="card-elevated"
                          style={{
                            marginTop: '1rem',
                            borderLeft: '4px solid var(--color-mint)',
                            background: 'var(--bg-surface-elevated)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <Lock size={15} style={{ color: 'var(--color-mint)' }} />
                              <strong style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                                Your Submitted Interpretation (Confidential to You)
                              </strong>
                            </div>
                            <button
                              type="button"
                              onClick={handleReloadMySubmission}
                              disabled={mySubmissionLoading}
                              title="Refresh my submission"
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}
                            >
                              <RefreshCw size={13} className={mySubmissionLoading ? 'spinner' : ''} />
                              Refresh
                            </button>
                          </div>

                          {mySubmissionLoading && (
                            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                              <span className="spinner" style={{ marginRight: '0.5rem' }} /> Loading your persisted response...
                            </div>
                          )}

                          {mySubmissionError && (
                            <div style={{ background: '#451a1a', border: '1px solid #7f1d1d', color: '#fca5a5', padding: '0.625rem 0.75rem', borderRadius: '4px', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                              {mySubmissionError}
                            </div>
                          )}

                          {!mySubmissionLoading && (
                            <>
                              <div style={{ marginBottom: '0.75rem' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                                  What you interpreted
                                </span>
                                <div
                                  style={{
                                    marginTop: '0.35rem',
                                    padding: '0.75rem',
                                    background: 'var(--bg-primary)',
                                    borderRadius: '4px',
                                    border: '1px solid var(--border)',
                                    fontSize: '0.875rem',
                                    color: 'var(--text-primary)',
                                    lineHeight: 1.5,
                                    whiteSpace: 'pre-wrap',
                                  }}
                                >
                                  {mySubmission?.interpretation || (
                                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                      No interpretation text recorded.
                                    </span>
                                  )}
                                </div>
                              </div>

                              {mySubmission?.assumptions && (
                                <div style={{ marginBottom: '0.75rem' }}>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                                    Key Assumptions
                                  </span>
                                  <div
                                    style={{
                                      marginTop: '0.35rem',
                                      padding: '0.5rem 0.75rem',
                                      background: 'var(--bg-primary)',
                                      borderRadius: '4px',
                                      border: '1px solid var(--border)',
                                      fontSize: '0.8125rem',
                                      color: 'var(--text-secondary)',
                                    }}
                                  >
                                    {formatListOrText(mySubmission.assumptions)}
                                  </div>
                                </div>
                              )}

                              {mySubmission?.success_criteria && (
                                <div style={{ marginBottom: '0.75rem' }}>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                                    Acceptance Criteria
                                  </span>
                                  <div
                                    style={{
                                      marginTop: '0.35rem',
                                      padding: '0.5rem 0.75rem',
                                      background: 'var(--bg-primary)',
                                      borderRadius: '4px',
                                      border: '1px solid var(--border)',
                                      fontSize: '0.8125rem',
                                      color: 'var(--text-secondary)',
                                    }}
                                  >
                                    {formatListOrText(mySubmission.success_criteria)}
                                  </div>
                                </div>
                              )}

                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                                <Lock size={12} style={{ color: 'var(--color-mint)' }} />
                                <span>Blind submission privacy active: peers cannot see your answers until analysis.</span>
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <form onSubmit={handleSubmitInterpretation}>
                      {!auth && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem', marginBottom: '0.5rem' }}>
                          <div className="form-group">
                            <label className="form-label" htmlFor="manual-name">Your Name</label>
                            <input
                              id="manual-name"
                              type="text"
                              className="form-input"
                              placeholder="e.g. Alex"
                              value={participantName}
                              onChange={(e) => setParticipantName(e.target.value)}
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label" htmlFor="manual-id">Role / Identifier</label>
                            <input
                              id="manual-id"
                              type="text"
                              className="form-input"
                              placeholder="e.g. dev-lead"
                              value={participantId}
                              onChange={(e) => setParticipantId(e.target.value)}
                            />
                          </div>
                        </div>
                      )}

                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-interpretation">
                          What is your interpretation of this task? *
                        </label>
                        <textarea
                          id="participant-interpretation"
                          className="form-textarea"
                          rows={4}
                          placeholder="What specific deliverables, functionality, or milestones are expected?"
                          value={interpretation}
                          onChange={(e) => setInterpretation(e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-assumptions">
                          Key Assumptions (Optional)
                        </label>
                        <input
                          id="participant-assumptions"
                          type="text"
                          className="form-input"
                          placeholder="e.g. PostgreSQL used, mobile-first design, auth API exists"
                          value={assumptions}
                          onChange={(e) => setAssumptions(e.target.value)}
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="participant-success">
                          Acceptance / Success Criteria (Optional)
                        </label>
                        <input
                          id="participant-success"
                          type="text"
                          className="form-input"
                          placeholder="e.g. Sign up flow works with 0 errors, Lighthouse score > 90"
                          value={successCriteria}
                          onChange={(e) => setSuccessCriteria(e.target.value)}
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={loading || !interpretation.trim()}
                        className="btn btn-primary"
                        style={{ width: '100%', marginTop: '0.5rem' }}
                      >
                        {loading ? <span className="spinner" /> : 'Submit Blind Interpretation'}
                      </button>
                    </form>
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: MISUNDERSTANDINGS (ISSUES & EVIDENCE) */}
            {activeTab === 'issues' && (
              <div>
                <div className="card" style={{ marginBottom: '1.25rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div>
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 700 }}>Misunderstanding Map</h3>
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                        Identified differences backed strictly by verbatim quotes from team submissions.
                      </p>
                    </div>

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
                            padding: '0.25rem 0.6rem',
                            borderRadius: '4px',
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

                  {/* Non-Blaming Collaborative Clarification Guidance (Visible in empty & populated states) */}
                  <div
                    style={{
                      background: 'rgba(56, 189, 248, 0.08)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '6px',
                      padding: '0.75rem 0.875rem',
                      marginBottom: '1rem',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.625rem',
                    }}
                  >
                    <HelpCircle size={16} style={{ color: '#38bdf8', flexShrink: 0, marginTop: '2px' }} />
                    <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Collaborative Alignment Note:</strong>{' '}
                      Detected differences are discussion prompts to clarify assumptions and build shared alignment,
                      not proof of individual error or fault. Divergence is a normal and valuable signal in cross-functional collaboration.
                    </div>
                  </div>

                  {issues.length === 0 ? (
                    <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      <p style={{ fontSize: '0.9375rem', marginBottom: '0.75rem' }}>
                        No misunderstandings analyzed yet.
                      </p>
                      <button
                        type="button"
                        onClick={handleRunAnalysis}
                        disabled={analyzing || (session.participant_count || 0) < 2}
                        className="btn btn-primary"
                      >
                        {analyzing ? <span className="spinner" /> : 'Run AI Analysis Now'}
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
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

                          <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.25rem' }}>
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

                          {/* Verbatim Evidence Quotes */}
                          <div style={{ marginBottom: '0.625rem' }}>
                            <button
                              type="button"
                              onClick={() => toggleEvidence(issue.id)}
                              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem', padding: 0 }}
                            >
                              {expandedEvidence[issue.id] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                              {expandedEvidence[issue.id] ? 'Hide Evidence' : `Evidence Quotes (${issue.evidence?.length || 0})`}
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
                              <label className="form-label" htmlFor={`decision-notes-${issue.id}`}>
                                Document Team Decision:
                              </label>
                              <input
                                id={`decision-notes-${issue.id}`}
                                type="text"
                                className="form-input"
                                placeholder="e.g. Post-launch milestone; email login only for v1."
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
                                    onClick={() => handleUpdateIssue(issue.id, 'dismissed', 'Marked out of scope')}
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
                  )}
                </div>
              </div>
            )}

            {/* TAB 4: SHARED AGREEMENT */}
            {activeTab === 'agreement' && (
              <div style={{ maxWidth: '780px', margin: '0 auto' }}>
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                    <div>
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 700 }}>Shared Confirmed Agreement</h3>
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                        Aligned contract compiled from resolved decisions and common understandings.
                      </p>
                    </div>
                    <span className={`badge badge-${agreement?.is_fully_confirmed ? 'resolved' : 'medium'}`}>
                      {agreement?.is_fully_confirmed ? 'Confirmed' : 'Pending'}
                    </span>
                  </div>

                  {agreement ? (
                    <div>
                      <div style={{ marginBottom: '1.25rem' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                          Agreed In-Scope Items:
                        </div>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                          {agreement.items?.map((item, idx) => (
                            <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.8125rem' }}>
                              <CheckCircle2 size={15} style={{ color: '#16a34a', flexShrink: 0, marginTop: '2px' }} />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {agreement.excluded_items?.length > 0 && (
                        <div style={{ marginBottom: '1.25rem' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            Agreed Out of Scope:
                          </div>
                          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                            {agreement.excluded_items.map((item, idx) => (
                              <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                                <XCircle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div style={{ background: 'var(--bg-surface-elevated)', padding: '0.875rem', borderRadius: '6px', border: '1px solid var(--border)' }}>
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                          <strong>Confirmed Participants:</strong>{' '}
                          {agreement.confirmed_by?.length > 0 ? (
                            <span style={{ color: 'var(--color-mint)' }}>{agreement.confirmed_by.join(', ')}</span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>None yet</span>
                          )}
                        </div>

                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                          {auth && !agreement.confirmed_by?.includes(auth.participantId) && !agreement.confirmed_by?.includes(auth.displayName) && (
                            <button
                              type="button"
                              onClick={() => handleConfirmAgreement(auth.participantId || auth.displayName)}
                              className="btn btn-success"
                              style={{ fontSize: '0.8125rem' }}
                            >
                              Confirm Agreement as {auth.displayName}
                            </button>
                          )}

                          <input
                            type="text"
                            className="form-input"
                            style={{ maxWidth: '220px', padding: '0.35rem 0.625rem', fontSize: '0.8125rem' }}
                            placeholder="Participant ID or Name"
                            value={confirmingParticipant}
                            onChange={(e) => setConfirmingParticipant(e.target.value)}
                          />
                          <button
                            type="button"
                            onClick={() => handleConfirmAgreement(confirmingParticipant)}
                            disabled={!confirmingParticipant.trim()}
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.8125rem' }}
                          >
                            Confirm
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                      Agreement will be generated once AI analysis runs.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* TAB 5: THE BRIDGE TEST */}
            {activeTab === 'bridge' && (
              <div style={{ maxWidth: '820px', margin: '0 auto' }}>
                {bridgeTest ? (
                  <div className="card-elevated" style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1.125rem', fontWeight: 700 }}>The Bridge Test</h3>
                        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                          Measures convergence between divergent perspectives into shared alignment.
                        </p>
                      </div>
                      <span className={`badge badge-${bridgeTest.bridge_status === 'bridged' ? 'resolved' : bridgeTest.bridge_status === 'in_progress' ? 'medium' : 'critical'}`}>
                        {bridgeTest.bridge_status.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="progress-bar-bg" style={{ height: '10px' }}>
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${bridgeTest.resolution_percentage}%`,
                          background: bridgeTest.bridge_status === 'bridged' ? '#16a34a' : 'var(--primary)',
                        }}
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      <span>Resolution Progress</span>
                      <strong>{bridgeTest.resolution_percentage}%</strong>
                    </div>

                    <div className="stat-grid">
                      <div className="stat-card">
                        <div className="stat-card-label">Initial Gaps</div>
                        <div className="stat-card-value">{bridgeTest.initial_issues_count}</div>
                      </div>
                      <div className="stat-card stat-card-mint">
                        <div className="stat-card-label">Resolved</div>
                        <div className="stat-card-value" style={{ color: '#86efac' }}>
                          {bridgeTest.resolved_count}
                        </div>
                      </div>
                      <div className="stat-card stat-card-coral">
                        <div className="stat-card-label">Unresolved</div>
                        <div className="stat-card-value" style={{ color: '#fca5a5' }}>
                          {bridgeTest.open_count}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-card-label">Dismissed</div>
                        <div className="stat-card-value" style={{ color: 'var(--text-muted)' }}>
                          {bridgeTest.dismissed_count}
                        </div>
                      </div>
                      <div className="stat-card">
                        <div className="stat-card-label">Resolution Rate</div>
                        <div className="stat-card-value">{bridgeTest.resolution_percentage}%</div>
                      </div>
                      <div className={`stat-card ${agreement?.is_fully_confirmed ? 'stat-card-mint' : ''}`}>
                        <div className="stat-card-label">Agreement</div>
                        <div className="stat-card-value" style={{ fontSize: '1.125rem' }}>
                          {agreement?.is_fully_confirmed ? 'Confirmed' : 'Pending'}
                        </div>
                      </div>
                    </div>

                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.75rem', fontStyle: 'italic' }}>
                      {bridgeTest.disclaimer}
                    </p>
                  </div>
                ) : (
                  <div className="card" style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                      Bridge Test metrics calculate automatically once AI analysis is triggered.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
