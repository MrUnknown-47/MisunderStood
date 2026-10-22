export type SessionStatus =
  | "collecting_responses"
  | "analyzing"
  | "completed"
  | "reviewing_issues"
  | "agreement_pending"
  | "confirmed"
  | "failed"
  | string;

export interface SessionDetails {
  id: string;
  title: string;
  description: string;
  context?: string | null;
  join_code?: string;
  status: SessionStatus;
  participant_count?: number;
  submitted_count?: number;
  can_start_analysis?: boolean;
  analysis_error?: string | null;
}

export interface Participant {
  id?: string;
  participant_id?: string;
  display_name: string;
  submitted?: boolean;
  has_submitted?: boolean;
  role?: string;
}

export interface SessionProgress {
  status: SessionStatus;
  participant_count?: number;
  submitted_count?: number;
  can_start_analysis?: boolean;
  analysis_id?: string;
  error?: string | null;
}

export type IssueType =
  | "contradiction"
  | "assumption"
  | "omission"
  | "scope_difference"
  | "success_criteria_difference";

export type IssueStatus = "open" | "resolved" | "dismissed" | string;

export interface Evidence {
  participant_id: string;
  display_name?: string;
  quote: string;
}

export interface Issue {
  id: string;
  type: IssueType;
  title: string;
  description: string;
  impact?: string;
  priority: "high" | "medium" | "low" | string;
  confidence?: number;
  status: IssueStatus;
  evidence: Evidence[];
  clarification_question: string;
  resolution_text?: string | null;
}

export interface ComplementaryPerspective {
  id: string;
  title: string;
  description: string;
  evidence: Evidence[];
}

export interface IssueAnalysis {
  session_id: string;
  summary?: string;
  issues: Issue[];
  complementary_perspectives: ComplementaryPerspective[];
}

export interface AgreementItem {
  id?: string;
  text: string;
  source?: string;
  category?: "confirmed" | "unresolved" | "suggestion" | string;
}

export interface Agreement {
  agreement_id: string;
  status: string;
  version?: number;
  items: AgreementItem[];
}

export interface BridgeMetrics {
  initial_issue_count: number;
  resolved_issue_count: number;
  unresolved_issue_count: number;
  dismissed_issue_count: number;
  resolution_rate_percent: number | null;
  agreement_status: string;
}

export interface SessionIdentity {
  sessionId: string;
  participantId?: string;
  displayName?: string;
  joinCode?: string;
  isCreator: boolean;
  hasSubmitted: boolean;
  agreement?: Agreement;
}
