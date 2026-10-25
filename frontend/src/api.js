/**
 * API client connecting the React frontend to FastAPI backend endpoints.
 * Provides session-scoped credential management, Bearer token authentication,
 * and endpoint methods aligned with the Phase 1 backend contract.
 */

const BASE_URL = '/api';
const AUTH_PREFIX = 'misunderstood_auth_';
const ACTIVE_SESSION_KEY = 'misunderstood_active_session_id';

/**
 * Retrieve stored authentication credentials for a specific session.
 */
export function getSessionAuth(sessionId) {
  if (!sessionId) return null;
  try {
    const raw = localStorage.getItem(`${AUTH_PREFIX}${sessionId}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Persist authentication credentials scoped strictly to a specific session.
 */
export function setSessionAuth(sessionId, authData) {
  if (!sessionId || !authData) return;
  try {
    localStorage.setItem(`${AUTH_PREFIX}${sessionId}`, JSON.stringify(authData));
    localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
    localStorage.setItem('misunderstood_session_id', sessionId);
  } catch {
    // ignore storage quota errors
  }
}

/**
 * Clear stored credentials for a specific session.
 */
export function clearSessionAuth(sessionId) {
  if (sessionId) {
    try {
      localStorage.removeItem(`${AUTH_PREFIX}${sessionId}`);
    } catch {}
  }
  try {
    if (localStorage.getItem(ACTIVE_SESSION_KEY) === sessionId) {
      localStorage.removeItem(ACTIVE_SESSION_KEY);
    }
    if (localStorage.getItem('misunderstood_session_id') === sessionId) {
      localStorage.removeItem('misunderstood_session_id');
    }
  } catch {}
}

/**
 * Retrieve the most recently active session ID.
 */
export function getStoredSessionId() {
  try {
    return (
      localStorage.getItem(ACTIVE_SESSION_KEY) ||
      localStorage.getItem('misunderstood_session_id') ||
      ''
    );
  } catch {
    return '';
  }
}

/**
 * Helper to execute HTTP requests with optional session-scoped Bearer authentication.
 * Guarantees that credentials from session A are NEVER attached to session B.
 */
async function request(path, options = {}, targetSessionId = null) {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach Authorization header ONLY if credentials exist for this specific targetSessionId
  if (targetSessionId) {
    const auth = getSessionAuth(targetSessionId);
    if (auth && auth.token) {
      headers.set('Authorization', `Bearer ${auth.token}`);
    }
  }

  const url = path.startsWith('http') ? path : `${BASE_URL}${path}`;
  const res = await fetch(url, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
      } else if (data.message) {
        errorMsg = data.message;
      }
    }
    const error = new Error(errorMsg);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

export async function createSession(titleOrPayload, description = null, context = null, creatorName = null, minParticipants = 2) {
  let payload;
  if (typeof titleOrPayload === 'object' && titleOrPayload !== null) {
    payload = titleOrPayload;
  } else {
    payload = {
      title: titleOrPayload,
      description: description || null,
      context: context || null,
      creator_name: creatorName || null,
      min_participants: minParticipants || 2,
    };
  }

  const data = await request('/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  if (data && data.id && data.participant_token) {
    setSessionAuth(data.id, {
      sessionId: data.id,
      participantId: data.creator_participant_id || '',
      token: data.participant_token,
      displayName: payload.creator_name || 'Creator',
      role: 'creator',
    });
  }

  return data;
}

export async function joinSession(joinCode, displayName) {
  const code = (joinCode || '').trim().toUpperCase();
  const name = (displayName || '').trim();

  const data = await request('/sessions/join', {
    method: 'POST',
    body: JSON.stringify({
      join_code: code,
      display_name: name,
    }),
  });

  if (data && data.session_id && data.participant_token) {
    setSessionAuth(data.session_id, {
      sessionId: data.session_id,
      participantId: data.participant_id,
      token: data.participant_token,
      displayName: data.display_name || name,
      role: 'participant',
    });
  }

  return data;
}

export async function getSession(sessionId) {
  return request(`/sessions/${sessionId}`, { method: 'GET' }, sessionId);
}

export async function getSessionParticipants(sessionId) {
  return request(`/sessions/${sessionId}/participants`, { method: 'GET' }, sessionId);
}

export async function getSessionStatus(sessionId) {
  return request(`/sessions/${sessionId}/status`, { method: 'GET' }, sessionId);
}

export async function getMyInterpretation(sessionId) {
  return request(`/sessions/${sessionId}/interpretations/me`, { method: 'GET' }, sessionId);
}

export async function submitInterpretation(sessionId, interpretationData) {
  return request(
    `/sessions/${sessionId}/interpretations`,
    {
      method: 'POST',
      body: JSON.stringify(interpretationData),
    },
    sessionId
  );
}

export async function submitParticipant(sessionId, participantData) {
  return request(
    `/sessions/${sessionId}/participants`,
    {
      method: 'POST',
      body: JSON.stringify(participantData),
    },
    sessionId
  );
}

export async function triggerAnalysis(sessionId) {
  return request(`/sessions/${sessionId}/analyze`, { method: 'POST' }, sessionId);
}

export async function getIssues(sessionId, statusFilter = null) {
  const path = statusFilter
    ? `/sessions/${sessionId}/issues?resolution_status=${statusFilter}`
    : `/sessions/${sessionId}/issues`;
  return request(path, { method: 'GET' }, sessionId);
}

export async function updateIssueStatus(sessionId, issueId, resolutionStatus, resolutionNotes = null) {
  return request(
    `/sessions/${sessionId}/issues/${issueId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        resolution_status: resolutionStatus,
        resolution_notes: resolutionNotes,
      }),
    },
    sessionId
  );
}

export async function getAgreement(sessionId) {
  return request(`/sessions/${sessionId}/agreement`, { method: 'GET' }, sessionId);
}

export async function confirmAgreement(sessionId, participantId) {
  return request(
    `/sessions/${sessionId}/agreement/confirm`,
    {
      method: 'POST',
      body: JSON.stringify({ participant_id: participantId }),
    },
    sessionId
  );
}

export async function getBridgeTest(sessionId) {
  return request(`/sessions/${sessionId}/bridge-test`, { method: 'GET' }, sessionId);
}
