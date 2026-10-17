"""Deterministic evidence and finding validator for MISUNDERSTOOD.

Enforces zero-hallucination rules:
1. Verifies participant IDs against the submitted participant list.
2. Verifies that every quote is an exact contiguous excerpt from the participant's
   actual submitted interpretation, assumptions, or success criteria.
3. Uses conservative whitespace normalization without fuzzy/approximate matching.
4. Requires multi-participant evidence for contradiction and scope_difference findings.
5. Rejects findings that lack required evidence; never silently rewrites quotes.
"""

from typing import Optional
from backend.ai.schemas import (
    ComplementaryPerspective,
    Evidence,
    Issue,
    IssueType,
    ParticipantInput,
    SourceField,
)


def normalize_whitespace(text: Optional[str]) -> str:
    """Normalize whitespace by stripping leading/trailing whitespace and collapsing

    consecutive whitespace characters into single ASCII spaces.
    """
    if not text:
        return ""
    return " ".join(text.split())


class EvidenceValidator:
    """Deterministic validator for quotes and candidate findings."""

    def __init__(self, participants: list[ParticipantInput]):
        """Index participant text fields by participant_id."""
        self.participants_map: dict[str, dict[SourceField, str]] = {}
        for p in participants:
            self.participants_map[p.participant_id] = {
                SourceField.INTERPRETATION: normalize_whitespace(p.interpretation),
                SourceField.ASSUMPTIONS: normalize_whitespace(p.assumptions or ""),
                SourceField.SUCCESS_CRITERIA: normalize_whitespace(
                    p.success_criteria or ""
                ),
            }

    def verify_quote(self, evidence: Evidence) -> Optional[Evidence]:
        """Verify that an evidence quote exists in the referenced participant's text.

        Returns an updated Evidence with the verified source_field,
        or None if the participant is unknown or the quote is fabricated.
        """
        pid = evidence.participant_id
        if pid not in self.participants_map:
            return None

        norm_quote = normalize_whitespace(evidence.quote)
        if not norm_quote:
            return None

        norm_quote_lower = norm_quote.lower()
        fields = self.participants_map[pid]

        # Check candidate fields in priority order: interpretation, assumptions, success_criteria
        for source_field in [
            SourceField.INTERPRETATION,
            SourceField.ASSUMPTIONS,
            SourceField.SUCCESS_CRITERIA,
        ]:
            field_text = fields[source_field]
            if not field_text:
                continue

            field_text_lower = field_text.lower()
            if norm_quote_lower in field_text_lower:
                # Extract the exact-cased slice from the participant's original normalized text
                start_idx = field_text_lower.find(norm_quote_lower)
                exact_slice = field_text[start_idx : start_idx + len(norm_quote)]

                return Evidence(
                    participant_id=pid,
                    quote=exact_slice,
                    source_field=source_field,
                )

        return None

    def validate_issues(
        self, candidate_issues: list[Issue]
    ) -> tuple[list[Issue], int, list[str]]:
        """Validate candidate issues against deterministic evidence rules.

        Returns:
            (verified_issues, dropped_quotes_count, rejection_reasons)
        """
        verified_issues: list[Issue] = []
        dropped_quotes_count = 0
        rejection_reasons: list[str] = []

        for issue in candidate_issues:
            verified_evidence: list[Evidence] = []
            for ev in issue.evidence:
                verified_ev = self.verify_quote(ev)
                if verified_ev is not None:
                    verified_evidence.append(verified_ev)
                else:
                    dropped_quotes_count += 1

            if not verified_evidence:
                rejection_reasons.append(
                    f"Issue '{issue.title}' rejected: no verified evidence found."
                )
                continue

            # Multi-participant check:
            # Contradictions and scope differences claim a disagreement between participants,
            # so they MUST cite evidence from at least 2 distinct participants.
            if issue.type in (IssueType.CONTRADICTION, IssueType.SCOPE_DIFFERENCE):
                distinct_participants = {ev.participant_id for ev in verified_evidence}
                if len(distinct_participants) < 2:
                    rejection_reasons.append(
                        f"Issue '{issue.title}' ({issue.type.value}) rejected: "
                        f"requires evidence from at least 2 distinct participants, "
                        f"found only {len(distinct_participants)}."
                    )
                    continue

            # Construct verified issue with verified evidence list
            verified_issue = Issue(
                type=issue.type,
                title=issue.title,
                description=issue.description,
                evidence=verified_evidence,
                impact=issue.impact,
                priority=issue.priority,
                confidence=issue.confidence,
                clarification_question=issue.clarification_question,
            )
            verified_issues.append(verified_issue)

        return verified_issues, dropped_quotes_count, rejection_reasons

    def validate_complementary_perspectives(
        self, candidate_complements: list[ComplementaryPerspective]
    ) -> tuple[list[ComplementaryPerspective], int, list[str]]:
        """Validate complementary perspectives against deterministic evidence rules.

        Returns:
            (verified_complements, dropped_quotes_count, rejection_reasons)
        """
        verified_complements: list[ComplementaryPerspective] = []
        dropped_quotes_count = 0
        rejection_reasons: list[str] = []

        for comp in candidate_complements:
            verified_evidence: list[Evidence] = []
            for ev in comp.evidence:
                verified_ev = self.verify_quote(ev)
                if verified_ev is not None:
                    verified_evidence.append(verified_ev)
                else:
                    dropped_quotes_count += 1

            if not verified_evidence:
                rejection_reasons.append(
                    f"Complementary perspective '{comp.title}' rejected: no verified evidence."
                )
                continue

            verified_comp = ComplementaryPerspective(
                title=comp.title,
                description=comp.description,
                evidence=verified_evidence,
            )
            verified_complements.append(verified_comp)

        return verified_complements, dropped_quotes_count, rejection_reasons


# ============================================================================
# Deterministic Issue Deduplication & Overlap Detection
# ============================================================================

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "could", "did", "do", "does",
    "doing", "down", "during", "each", "few", "for", "from", "further", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of",
    "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "s", "same", "she", "should", "so", "some", "such", "t", "than",
    "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours",
    # Question framing & scoping meta-words
    "part", "included", "include", "includes", "including", "addition", "alongside",
    "difference", "differ", "differing", "different", "differences", "participants",
    "participant", "required", "require", "requires", "requiring", "requirement",
    "requirements", "supported", "support", "supporting", "supports", "needed",
    "need", "needs", "needing", "scope", "scoped", "milestone", "initial", "launch",
    "release", "mvp", "prod", "production", "deliverable", "deliverables",
    "consider", "considered", "whether", "based", "work", "feature", "features",
    "overall", "task", "details", "application", "system", "app", "also", "well",
}

GENERIC_TERMS = {
    "login", "auth", "authentication", "feature", "features", "overall", "application",
    "launch", "release", "requirement", "requirements", "work", "functionality", "task",
    "details", "system", "app", "deliverable", "deliverables",
}

SYNONYMS = {
    "auth": "login",
    "authentication": "login",
    "signin": "login",
    "sign-in": "login",
    "log-in": "login",
    "signup": "registration",
    "sign-up": "registration",
    "register": "registration",
    "reset": "recovery",
}


def extract_decision_keywords(text: str) -> set[str]:
    """Extract lowercased content words from text, ignoring structural stopwords

    and normalizing core domain synonyms.
    """
    import re

    words = re.findall(r"[a-zA-Z0-9_-]+", text.lower())
    result = set()
    for w in words:
        if len(w) >= 3 and w not in STOPWORDS:
            norm = SYNONYMS.get(w, w)
            result.add(norm)
    return result


def is_umbrella_issue(issue: Issue) -> bool:
    """An issue is a generic umbrella issue if neither its question nor title

    contains specific domain tokens beyond GENERIC_TERMS.
    """
    q_words = extract_decision_keywords(issue.clarification_question)
    t_words = extract_decision_keywords(issue.title)
    q_specific = q_words - GENERIC_TERMS
    t_specific = t_words - GENERIC_TERMS
    return len(q_specific) == 0 and len(t_specific) == 0


def is_redundant_issue(existing: Issue, candidate: Issue) -> bool:
    """Determine whether candidate merely restates the existing issue rather than

    presenting a distinct clarification decision.

    Retains both if they require different decisions, even if they share evidence.
    Prunes candidate if:
    1. Both questions target the same decision (high Jaccard overlap on decision keywords
       or candidate's specific tokens are a subset of existing specific tokens).
    2. Titles have high lexical overlap.
    3. Candidate is a broad generic umbrella issue whose evidence is already covered
       by existing specific issues.
    """
    # 1. Compare clarification questions
    existing_q_words = extract_decision_keywords(existing.clarification_question)
    candidate_q_words = extract_decision_keywords(candidate.clarification_question)

    if existing_q_words and candidate_q_words:
        intersection = existing_q_words & candidate_q_words
        union = existing_q_words | candidate_q_words
        jaccard = len(intersection) / len(union) if union else 0.0

        if jaccard >= 0.50 or (len(intersection) >= 2 and len(candidate_q_words - existing_q_words) <= 1):
            return True

        # If candidate specific tokens are entirely covered by existing specific tokens
        cand_spec = candidate_q_words - GENERIC_TERMS
        exist_spec = existing_q_words - GENERIC_TERMS
        if cand_spec and exist_spec and cand_spec.issubset(exist_spec):
            return True

    # 2. Check title similarity
    existing_t_words = extract_decision_keywords(existing.title)
    candidate_t_words = extract_decision_keywords(candidate.title)
    if existing_t_words and candidate_t_words:
        t_intersection = existing_t_words & candidate_t_words
        t_union = existing_t_words | candidate_t_words
        t_jaccard = len(t_intersection) / len(t_union) if t_union else 0.0
        if t_jaccard >= 0.65:
            return True

    # 3. Check for generic umbrella issue:
    if is_umbrella_issue(candidate) and not is_umbrella_issue(existing):
        return True

    return False


def deduplicate_issues(issues: list[Issue]) -> tuple[list[Issue], list[str]]:
    """Filter candidate verified issues to eliminate redundant restatements.

    Rules:
    1. Generic umbrella issues must NEVER hide specific findings. If specific findings
       exist, generic umbrella issues are omitted in favor of the specific decisions,
       regardless of the order returned by the model.
    2. Redundant restatements of the same decision are deduplicated.
    3. Genuinely distinct decisions (even when sharing evidence) are preserved.
    """
    has_specific = any(not is_umbrella_issue(iss) for iss in issues)
    filtered_candidates: list[Issue] = []
    dedup_reasons: list[str] = []

    # Step 1: Pre-filter generic umbrella issues if specific findings exist
    for iss in issues:
        if has_specific and is_umbrella_issue(iss):
            dedup_reasons.append(
                f"Issue '{iss.title}' omitted: generic umbrella issue superseded by specific findings."
            )
        else:
            filtered_candidates.append(iss)

    # Step 2: Deduplicate restatements among candidates
    unique_issues: list[Issue] = []
    for candidate in filtered_candidates:
        dup_of: Optional[Issue] = None
        for existing in unique_issues:
            if is_redundant_issue(existing, candidate):
                dup_of = existing
                break

        if dup_of is not None:
            dedup_reasons.append(
                f"Issue '{candidate.title}' omitted: redundant restatement of '{dup_of.title}'."
            )
        else:
            unique_issues.append(candidate)

    return unique_issues, dedup_reasons
