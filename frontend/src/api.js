/**
 * API client connecting the React frontend to FastAPI backend endpoints.
 */

const BASE_URL = '/api';

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail || `Server error (${res.status})`;
    const error = new Error(errorMsg);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

export async function createSession(title, description) {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description: description || null }),
  });
  return handleResponse(res);
}

export async function getSession(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`);
  return handleResponse(res);
}

export async function submitParticipant(sessionId, participantData) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/participants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(participantData),
  });
  return handleResponse(res);
}

export async function triggerAnalysis(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/analyze`, {
    method: 'POST',
  });
  return handleResponse(res);
}

export async function getIssues(sessionId, statusFilter = null) {
  const url = statusFilter
    ? `${BASE_URL}/sessions/${sessionId}/issues?resolution_status=${statusFilter}`
    : `${BASE_URL}/sessions/${sessionId}/issues`;
  const res = await fetch(url);
  return handleResponse(res);
}

export async function updateIssueStatus(sessionId, issueId, resolutionStatus, resolutionNotes = null) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/issues/${issueId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      resolution_status: resolutionStatus,
      resolution_notes: resolutionNotes,
    }),
  });
  return handleResponse(res);
}

export async function getAgreement(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/agreement`);
  return handleResponse(res);
}

export async function confirmAgreement(sessionId, participantId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/agreement/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ participant_id: participantId }),
  });
  return handleResponse(res);
}

export async function getBridgeTest(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/bridge-test`);
  return handleResponse(res);
}
