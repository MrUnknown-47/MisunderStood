import {
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Copy,
  Eye,
  EyeOff,
  Flag,
  GitCompareArrows,
  Lightbulb,
  Link2,
  ListChecks,
  MessageCircleQuestion,
  Minus,
  Plus,
  Quote,
  RefreshCw,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  Users,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, messageFromError } from "./api";
import {
  Button,
  EmptyPanel,
  ErrorPanel,
  Field,
  InlineLink,
  LoadingPanel,
  PageIntro,
  PeopleIcon,
  ProgressBar,
  StatCard,
  StepBadge,
  inputClass,
} from "./components";
import { draftKey, useSession } from "./session";
import type {
  Agreement,
  AgreementItem,
  ComplementaryPerspective,
  Issue,
  Participant,
  SessionDetails,
  SessionProgress,
} from "./types";

const pageContainer = "mx-auto w-full max-w-7xl px-5 py-10 sm:px-8 sm:py-14";
const formCard = "rounded-[28px] border border-ink/10 bg-white p-5 shadow-card sm:p-8";

function SectionBack({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="mb-7 inline-flex items-center gap-2 rounded-lg text-sm font-bold text-muted transition hover:text-ink focus:outline-none focus:ring-4 focus:ring-coral/20"
    >
      <ArrowLeft className="size-4" /> {children}
    </Link>
  );
}

function cleanList(values: string[]) {
  return values.map((value) => value.trim()).filter(Boolean);
}

function formatStatus(value?: string) {
  if (!value) return "Unknown";
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function LandingPage() {
  const [gapRevealed, setGapRevealed] = useState(false);
  const flow = [
    { icon: EyeOff, title: "Interpret privately", text: "Everyone responds before seeing the others." },
    { icon: SearchCheck, title: "Find the gaps", text: "AI highlights evidence-backed differences." },
    { icon: Link2, title: "Build agreement", text: "Turn clarification into a shared checklist." },
  ];

  return (
    <div className="overflow-hidden">
      <section className="relative border-b border-ink/8">
        <div className="hero-orb hero-orb-one" />
        <div className="hero-orb hero-orb-two" />
        <div className={`${pageContainer} relative grid min-h-[650px] items-center gap-12 lg:grid-cols-[1.1fr_.9fr]`}>
          <div className="max-w-3xl py-8">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-coral/20 bg-coral-soft px-3 py-1.5 text-xs font-black uppercase tracking-[0.14em] text-coral-dark">
              <Sparkles className="size-3.5" /> Bridge the gap
            </div>
            <h1 className="font-display text-[clamp(3rem,8vw,6.8rem)] font-black leading-[0.88] tracking-[-0.055em] text-ink">
              Same conversation.
              <span className="mt-2 block text-coral">Different realities.</span>
            </h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-muted sm:text-xl">
              Compare what your team actually understood, clarify the differences, and leave with one
              shared plan—before assumptions become rework.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link to="/create">
                <Button className="w-full px-6 sm:w-auto">
                  Create a session <ArrowRight className="size-4" />
                </Button>
              </Link>
              <Link to="/join">
                <Button variant="secondary" className="w-full px-6 sm:w-auto">
                  Join with a code
                </Button>
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold text-muted">
              <span className="inline-flex items-center gap-2"><ShieldCheck className="size-4 text-mint-dark" /> Independent responses</span>
              <span className="inline-flex items-center gap-2"><Quote className="size-4 text-coral" /> Evidence-backed findings</span>
            </div>
          </div>

          <div className="relative hidden min-h-[520px] lg:block" aria-hidden="true">
            <div className="float-card float-card-a absolute left-4 top-12 w-[78%] rotate-[-4deg] rounded-[28px] border border-ink/10 bg-white p-6 shadow-float">
              <div className="flex items-center gap-3">
                <div className="grid size-10 place-items-center rounded-full bg-yellow-soft font-black">A</div>
                <div><p className="text-xs font-bold text-muted">PARTICIPANT A</p><p className="font-bold text-ink">“Email login only.”</p></div>
              </div>
              <div className="mt-5 h-2 w-full rounded-full bg-ink/7" />
              <div className="mt-2 h-2 w-3/4 rounded-full bg-ink/7" />
            </div>
            <div className="float-card float-card-b absolute right-0 top-48 w-[80%] rotate-[3deg] rounded-[28px] border border-ink/10 bg-ink p-6 text-white shadow-float">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-coral px-3 py-1 text-[10px] font-black uppercase tracking-wider">Potential gap</span>
                <GitCompareArrows className="size-5 text-mint" />
              </div>
              <p className="mt-5 font-display text-2xl font-black">“Email and phone login.”</p>
              <p className="mt-2 text-sm leading-6 text-white/65">Participant B included a wider authentication scope.</p>
            </div>
            <div className="float-card float-card-c absolute bottom-10 left-12 w-[78%] rotate-[-2deg] rounded-[28px] border border-mint/40 bg-mint-soft p-6 shadow-float">
              <div className="flex items-center gap-3"><MessageCircleQuestion className="size-6 text-mint-dark" /><p className="font-black text-ink">Hidden mismatch revealed</p></div>
              <p className="mt-4 text-sm font-semibold leading-6 text-ink/75">Should phone login be included in the first release?</p>
            </div>
          </div>
        </div>
      </section>

      <section className={`${pageContainer} py-16 sm:py-24`}>
        <div className="mb-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-coral">How it works</p>
            <h2 className="mt-3 font-display text-3xl font-black text-ink sm:text-5xl">From “got it” to real alignment.</h2>
          </div>
          <p className="max-w-md text-sm leading-6 text-muted">One focused workflow. No meeting transcript, no blame, and no made-up certainty.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {flow.map(({ icon: Icon, title, text }, index) => (
            <article key={title} className="group rounded-[26px] border border-ink/10 bg-white p-6 transition hover:-translate-y-1 hover:shadow-card">
              <div className="flex items-center justify-between">
                <div className="grid size-12 place-items-center rounded-2xl bg-cream-dark text-ink"><Icon className="size-5" /></div>
                <span className="font-display text-4xl font-black text-ink/8">0{index + 1}</span>
              </div>
              <h3 className="mt-7 font-display text-xl font-black text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-ink/8 bg-white/55">
        <div className={`${pageContainer} py-16 sm:py-24`}>
          <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:items-center">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-coral">Interactive sample · not live data</p>
              <h2 className="mt-3 font-display text-3xl font-black leading-tight text-ink sm:text-5xl">Reveal the gap.</h2>
              <p className="mt-4 text-base leading-7 text-muted">Two responses can sound compatible until you inspect the scope hiding underneath.</p>
              <Button className="mt-6" onClick={() => setGapRevealed((current) => !current)} aria-expanded={gapRevealed}>
                {gapRevealed ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                {gapRevealed ? "Hide the mismatch" : "Reveal the mismatch"}
              </Button>
            </div>
            <div className="rounded-[30px] border border-ink/10 bg-cream p-4 shadow-card sm:p-6">
              <p className="mb-4 text-xs font-black uppercase tracking-[0.14em] text-muted">Task: Prepare authentication for launch</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-white p-5"><p className="text-xs font-black text-coral">PARTICIPANT A</p><p className="mt-3 font-display text-lg font-bold text-ink">“Complete email and password login.”</p></div>
                <div className="rounded-2xl bg-ink p-5 text-white"><p className="text-xs font-black text-mint">PARTICIPANT B</p><p className="mt-3 font-display text-lg font-bold">“Complete email or phone login.”</p></div>
              </div>
              <div className={`gap-reveal mt-3 overflow-hidden rounded-2xl border border-coral/20 bg-coral-soft transition-all duration-500 ${gapRevealed ? "max-h-72 p-5 opacity-100" : "max-h-0 p-0 opacity-0"}`} aria-hidden={!gapRevealed}>
                <div className="flex items-start gap-3"><GitCompareArrows className="mt-0.5 size-5 shrink-0 text-coral" /><div><p className="text-xs font-black uppercase tracking-[0.13em] text-coral-dark">Potential scope difference</p><p className="mt-2 font-bold text-ink">Is phone login part of the first release?</p><p className="mt-2 text-sm leading-6 text-muted">Neither participant is marked wrong. The difference becomes a targeted decision for the team.</p></div></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={`${pageContainer} py-16 sm:py-24`}>
        <div className="grid gap-6 lg:grid-cols-2">
          <article className="rounded-[30px] bg-ink p-7 text-white sm:p-9">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-mint">Why it is different</p>
            <h2 className="mt-4 font-display text-3xl font-black">The Assumption Gap Detector.</h2>
            <p className="mt-4 leading-7 text-white/65">Most tools summarize what was said. MISUNDERSTOOD looks for what one person treated as agreed even though nobody else confirmed it.</p>
            <div className="mt-7 rounded-2xl bg-white/8 p-5"><p className="text-sm font-bold text-white">“Password recovery is required.”</p><p className="mt-2 text-sm leading-6 text-white/55">If only one participant includes it, the app raises an unconfirmed scope item—not a fabricated requirement.</p></div>
          </article>
          <article className="rounded-[30px] border border-ink/10 bg-white p-7 shadow-card sm:p-9">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-[0.16em] text-coral">Bridge Test preview</p><h2 className="mt-3 font-display text-3xl font-black text-ink">Before → after</h2></div><span className="rounded-full bg-yellow-soft px-3 py-1 text-[10px] font-black uppercase tracking-wider text-yellow-800">Illustrative sample</span></div>
            <div className="mt-7 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
              <div className="rounded-2xl bg-coral-soft p-5 text-center"><p className="text-xs font-black uppercase tracking-wider text-coral-dark">Before</p><p className="mt-2 font-display text-4xl font-black text-ink">3</p><p className="mt-1 text-xs text-muted">unresolved gaps</p></div>
              <ArrowRight className="size-5 text-muted" />
              <div className="rounded-2xl bg-mint-soft p-5 text-center"><p className="text-xs font-black uppercase tracking-wider text-mint-dark">After</p><p className="mt-2 font-display text-4xl font-black text-ink">1</p><p className="mt-1 text-xs text-muted">unresolved gap</p></div>
            </div>
            <p className="mt-5 text-sm leading-6 text-muted">Live sessions calculate these metrics from persisted issue states. The product never substitutes these sample values for real results.</p>
          </article>
        </div>
      </section>
    </div>
  );
}

export function CreateSessionPage() {
  const navigate = useNavigate();
  const { identity, setIdentity } = useSession();
  const [form, setForm] = useState({ title: "", description: "", context: "", displayName: "" });
  const [created, setCreated] = useState<{ id: string; join_code: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function registerCreator(session: { id: string; join_code: string }) {
    const joined = await api.joinSession({
      join_code: session.join_code,
      display_name: form.displayName.trim(),
    });
    setIdentity({
      sessionId: session.id,
      participantId: joined.participant_id,
      displayName: form.displayName.trim(),
      joinCode: session.join_code,
      isCreator: true,
      hasSubmitted: false,
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await api.createSession({
        title: form.title.trim(),
        description: form.description.trim(),
        ...(form.context.trim() ? { context: form.context.trim() } : {}),
      });
      setCreated(result);
      setIdentity({
        sessionId: result.id,
        joinCode: result.join_code,
        isCreator: true,
        hasSubmitted: false,
      });
      try {
        await registerCreator(result);
      } catch (joinError) {
        setError(`Session create ho gayi, lekin creator registration complete nahi hui: ${messageFromError(joinError)}`);
      }
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function copyCode() {
    if (!created) return;
    await navigator.clipboard.writeText(created.join_code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className={pageContainer}>
      <SectionBack to="/">Back home</SectionBack>
      <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr] lg:gap-16">
        <PageIntro eyebrow="Start a shared session" title="Put the task on the table." description="Describe the work once. Every participant will interpret the same source independently." />

        {created ? (
          <section className={`${formCard} self-start`}>
            {error ? <div className="mb-5"><ErrorPanel message={error} /></div> : null}
            <div className="grid size-12 place-items-center rounded-2xl bg-mint-soft text-mint-dark"><CheckCircle2 className="size-6" /></div>
            <h2 className="mt-5 font-display text-2xl font-black text-ink">Your session is ready.</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Share this join code with everyone who needs to contribute.</p>
            <div className="mt-7 rounded-2xl border border-dashed border-ink/20 bg-cream p-5 text-center">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-muted">Join code</p>
              <p className="mt-2 font-display text-4xl font-black tracking-[0.14em] text-ink">{created.join_code}</p>
              <Button variant="secondary" className="mt-4" onClick={copyCode}>
                {copied ? <Check className="size-4" /> : <Copy className="size-4" />} {copied ? "Copied" : "Copy code"}
              </Button>
            </div>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              {identity.participantId ? (
                <Button className="flex-1" onClick={() => navigate(`/sessions/${created.id}/interpret`)}>
                  Add my interpretation <ArrowRight className="size-4" />
                </Button>
              ) : (
                <Button className="flex-1" loading={loading} onClick={async () => {
                  setLoading(true); setError("");
                  try { await registerCreator(created); }
                  catch (joinError) { setError(messageFromError(joinError)); }
                  finally { setLoading(false); }
                }}>
                  Retry creator registration
                </Button>
              )}
              <Button variant="secondary" onClick={() => navigate(`/sessions/${created.id}/waiting`)}>Open waiting room</Button>
            </div>
          </section>
        ) : (
          <form onSubmit={submit} className={`${formCard} space-y-6`}>
            {error ? <ErrorPanel message={error} /> : null}
            <Field label="Your display name" required hint="Used inside this session">
              <input className={inputClass} maxLength={80} required placeholder="Your name" value={form.displayName} onChange={(e) => setForm({ ...form, displayName: e.target.value })} />
            </Field>
            <Field label="Task title" required hint={`${form.title.length}/160`}>
              <input className={inputClass} maxLength={160} required placeholder="Prepare the application for launch" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Task description" required hint={`${form.description.length}/3000`}>
              <textarea className={`${inputClass} min-h-36 resize-y`} maxLength={3000} required placeholder="What needs to be done? Keep it open enough for each person to explain their understanding." value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <Field label="Context" hint="Optional">
              <textarea className={`${inputClass} min-h-24 resize-y`} maxLength={1500} placeholder="Deadline, constraints, audience, or project background" value={form.context} onChange={(e) => setForm({ ...form, context: e.target.value })} />
            </Field>
            <div className="rounded-2xl bg-yellow-soft p-4 text-sm leading-6 text-ink/75">
              <strong className="text-ink">Tip:</strong> Describe the task, not the answer. Participants should still have room to reveal what they assumed.
            </div>
            <Button className="w-full" type="submit" loading={loading}>Create session <ArrowRight className="size-4" /></Button>
          </form>
        )}
      </div>
    </div>
  );
}

export function JoinSessionPage() {
  const navigate = useNavigate();
  const { setIdentity } = useSession();
  const [joinCode, setJoinCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await api.joinSession({
        join_code: joinCode.trim().toUpperCase(),
        display_name: displayName.trim(),
      });
      setIdentity({
        sessionId: result.session_id,
        participantId: result.participant_id,
        displayName: displayName.trim(),
        joinCode: joinCode.trim().toUpperCase(),
        isCreator: false,
        hasSubmitted: false,
      });
      navigate(`/sessions/${result.session_id}/interpret`);
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`${pageContainer} max-w-6xl`}>
      <SectionBack to="/">Back home</SectionBack>
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
        <div>
          <PageIntro eyebrow="Join the conversation" title="Bring your point of view." description="Your first response stays private until you submit it, so the team sees what you genuinely understood." />
          <div className="mt-8 space-y-4">
            <div className="flex gap-3"><StepBadge number={1} /><div><p className="font-bold text-ink">Enter the shared code</p><p className="mt-1 text-sm text-muted">Ask the session creator if you do not have it.</p></div></div>
            <div className="flex gap-3"><StepBadge number={2} /><div><p className="font-bold text-ink">Read the original task</p><p className="mt-1 text-sm text-muted">Everyone starts from the same source.</p></div></div>
            <div className="flex gap-3"><StepBadge number={3} /><div><p className="font-bold text-ink">Submit independently</p><p className="mt-1 text-sm text-muted">Other answers remain hidden until submission.</p></div></div>
          </div>
        </div>
        <form onSubmit={submit} className={`${formCard} self-start space-y-6`}>
          {error ? <ErrorPanel message={error} /> : null}
          <Field label="Session code" required>
            <input className={`${inputClass} font-display text-lg font-black uppercase tracking-[0.16em]`} maxLength={12} required autoCapitalize="characters" placeholder="GAP42X" value={joinCode} onChange={(e) => setJoinCode(e.target.value.toUpperCase().replace(/\s/g, ""))} />
          </Field>
          <Field label="Display name" required hint="Visible to this session">
            <input className={inputClass} maxLength={80} required placeholder="Your name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </Field>
          <Button className="w-full" type="submit" loading={loading}>Join session <ArrowRight className="size-4" /></Button>
          <p className="text-center text-xs leading-5 text-muted">By joining, your interpretation will be sent to the session backend for comparison.</p>
        </form>
      </div>
    </div>
  );
}

function useSessionOverview(sessionId?: string) {
  const [details, setDetails] = useState<SessionDetails | null>(null);
  const [progress, setProgress] = useState<SessionProgress | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    if (!sessionId) return;
    try {
      const [session, status, participantList] = await Promise.all([
        api.getSession(sessionId, signal),
        api.getStatus(sessionId, signal),
        api.getParticipants(sessionId, signal).catch(() => []),
      ]);
      setDetails(session);
      setProgress(status);
      setParticipants(participantList);
      setError("");
    } catch (requestError) {
      if ((requestError as Error).name !== "AbortError") setError(messageFromError(requestError));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    const timer = window.setInterval(() => void load(controller.signal), 4000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [load]);

  return { details, progress, participants, loading, error, reload: () => load() };
}

export function WaitingRoomPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { identity } = useSession();
  const { details, progress, participants, loading, error, reload } = useSessionOverview(sessionId);
  const [starting, setStarting] = useState(false);
  const [actionError, setActionError] = useState("");

  const participantCount = progress?.participant_count ?? details?.participant_count ?? participants.length;
  const submittedCount = progress?.submitted_count ?? details?.submitted_count ?? participants.filter((p) => p.submitted || p.has_submitted).length;
  const submissionPercent = participantCount ? Math.round((submittedCount / participantCount) * 100) : 0;
  const status = String(progress?.status || details?.status || "").toLowerCase();
  const allSubmitted = participantCount >= 2 && submittedCount >= participantCount;
  const canStart = progress?.can_start_analysis ?? details?.can_start_analysis ?? (identity.isCreator && allSubmitted);
  const analyzing = status.includes("analyz");
  const analysisDone = ["completed", "reviewing_issues", "agreement_pending", "confirmed"].includes(status);

  useEffect(() => {
    if (analysisDone) navigate(`/sessions/${sessionId}/map`, { replace: true });
  }, [analysisDone, navigate, sessionId]);

  async function startAnalysis() {
    setStarting(true);
    setActionError("");
    try {
      const result = await api.startAnalysis(sessionId);
      if (String(result.status).toLowerCase() === "completed") {
        navigate(`/sessions/${sessionId}/map`);
      } else {
        await reload();
      }
    } catch (requestError) {
      setActionError(messageFromError(requestError));
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <div className={pageContainer}><LoadingPanel label="Opening the waiting room…" /></div>;

  return (
    <div className={pageContainer}>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <PageIntro eyebrow="Waiting room" title="Collect every reality first." description="Responses stay independent until they are submitted. Analysis begins only when the session is ready." />
        {identity.joinCode || details?.join_code ? (
          <div className="rounded-2xl border border-ink/10 bg-white px-5 py-4 text-center shadow-sm">
            <p className="text-[10px] font-black uppercase tracking-[0.15em] text-muted">Join code</p>
            <p className="mt-1 font-display text-2xl font-black tracking-[0.12em] text-ink">{identity.joinCode || details?.join_code}</p>
          </div>
        ) : null}
      </div>
      <div className="mt-10 grid gap-6 lg:grid-cols-[1.05fr_.95fr]">
        <section className={`${formCard} space-y-6`}>
          {error ? <ErrorPanel message={error} onRetry={reload} /> : null}
          <div>
            <p className="text-xs font-black uppercase tracking-[0.15em] text-coral">The task</p>
            <h2 className="mt-3 font-display text-2xl font-black text-ink">{details?.title || "Session task"}</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">{details?.description}</p>
            {details?.context ? <div className="mt-4 rounded-2xl bg-cream p-4 text-sm leading-6 text-ink/70"><strong className="text-ink">Context:</strong> {details.context}</div> : null}
          </div>
          {!identity.hasSubmitted && identity.participantId ? (
            <Button onClick={() => navigate(`/sessions/${sessionId}/interpret`)}>Add my interpretation <ArrowRight className="size-4" /></Button>
          ) : (
            <div className="flex items-center gap-3 rounded-2xl bg-mint-soft p-4 text-sm font-bold text-ink"><CheckCircle2 className="size-5 text-mint-dark" /> Your interpretation is safely submitted.</div>
          )}
        </section>

        <section className={`${formCard}`}>
          <div className="flex items-center justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-[0.15em] text-muted">Submission progress</p><p className="mt-2 font-display text-3xl font-black text-ink">{submittedCount} <span className="text-lg text-muted">of {participantCount || "—"}</span></p></div><PeopleIcon /></div>
          <div className="mt-5"><ProgressBar value={submissionPercent} /></div>
          <div className="mt-6 space-y-3">
            {participants.length ? participants.map((participant, index) => {
              const submitted = participant.submitted || participant.has_submitted;
              return <div key={participant.id || participant.participant_id || index} className="flex items-center justify-between gap-4 rounded-xl border border-ink/8 px-4 py-3"><div className="flex items-center gap-3"><div className="grid size-8 place-items-center rounded-full bg-cream-dark text-xs font-black text-ink">{participant.display_name?.charAt(0).toUpperCase() || index + 1}</div><span className="text-sm font-bold text-ink">{participant.display_name || `Participant ${index + 1}`}</span></div><span className={`text-xs font-bold ${submitted ? "text-mint-dark" : "text-muted"}`}>{submitted ? "Submitted" : "Waiting"}</span></div>;
            }) : <p className="rounded-xl bg-cream p-4 text-sm text-muted">Participant names will appear when the backend returns them.</p>}
          </div>
          <div className="mt-6 border-t border-ink/8 pt-6">
            {actionError ? <div className="mb-4"><ErrorPanel message={actionError} /></div> : null}
            {analyzing ? <div className="rounded-2xl bg-yellow-soft p-4 text-sm"><div className="flex items-center gap-2 font-bold text-ink"><RefreshCw className="size-4 animate-spin" /> Comparing interpretations…</div><p className="mt-1 text-muted">Submitted responses are safe. This page will update automatically.</p></div> : identity.isCreator ? <Button className="w-full" disabled={!canStart} loading={starting} onClick={startAnalysis}><Sparkles className="size-4" /> Start analysis</Button> : <p className="text-center text-sm text-muted">The session creator will start analysis when everyone is ready.</p>}
            {identity.isCreator && !canStart && !analyzing ? <p className="mt-3 text-center text-xs text-muted">At least two completed interpretations are required.</p> : null}
          </div>
        </section>
      </div>
    </div>
  );
}

function ListInput({ label, values, onChange, placeholder }: { label: string; values: string[]; onChange: (values: string[]) => void; placeholder: string }) {
  function setAt(index: number, value: string) {
    const next = [...values]; next[index] = value; onChange(next);
  }
  return (
    <div>
      <div className="mb-2 flex items-center justify-between"><p className="text-sm font-bold text-ink">{label}</p><span className="text-xs font-medium text-muted">Optional</span></div>
      <div className="space-y-2">
        {values.map((value, index) => <div key={index} className="flex gap-2"><input className={inputClass} value={value} maxLength={500} placeholder={placeholder} onChange={(e) => setAt(index, e.target.value)} /><button type="button" className="rounded-xl border border-ink/10 px-3 text-muted hover:bg-red-50 hover:text-red-600" onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))} aria-label={`Remove ${label.toLowerCase()} ${index + 1}`}><Trash2 className="size-4" /></button></div>)}
      </div>
      <button type="button" className="mt-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-bold text-coral hover:bg-coral-soft" onClick={() => onChange([...values, ""])}><Plus className="size-3.5" /> Add another</button>
    </div>
  );
}

export function InterpretationPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { identity, patchIdentity } = useSession();
  const [details, setDetails] = useState<SessionDetails | null>(null);
  const [interpretation, setInterpretation] = useState("");
  const [assumptions, setAssumptions] = useState<string[]>([""]);
  const [criteria, setCriteria] = useState<string[]>([""]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const storageKey = draftKey(sessionId, identity.participantId || "creator");

  useEffect(() => {
    const controller = new AbortController();
    api.getSession(sessionId, controller.signal)
      .then(setDetails)
      .catch((requestError) => {
        if ((requestError as Error).name !== "AbortError") {
          setError(messageFromError(requestError));
        }
      })
      .finally(() => setLoading(false));
    try {
      const draft = localStorage.getItem(storageKey);
      if (draft) {
        const parsed = JSON.parse(draft);
        setInterpretation(parsed.interpretation || "");
        setAssumptions(parsed.assumptions?.length ? parsed.assumptions : [""]);
        setCriteria(parsed.criteria?.length ? parsed.criteria : [""]);
      }
    } catch { /* Ignore an unreadable local draft. */ }
    return () => controller.abort();
  }, [sessionId, storageKey]);

  useEffect(() => {
    const timer = window.setTimeout(() => localStorage.setItem(storageKey, JSON.stringify({ interpretation, assumptions, criteria })), 250);
    return () => window.clearTimeout(timer);
  }, [interpretation, assumptions, criteria, storageKey]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!identity.participantId) {
      setError("Participant ID missing hai. Join code se session dobara join karein.");
      return;
    }
    setSaving(true); setError("");
    try {
      await api.submitInterpretation(sessionId, { participant_id: identity.participantId, response_text: interpretation.trim(), assumptions: cleanList(assumptions), success_criteria: cleanList(criteria) });
      localStorage.removeItem(storageKey);
      patchIdentity({ hasSubmitted: true });
      navigate(`/sessions/${sessionId}/waiting`);
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally { setSaving(false); }
  }

  if (loading) return <div className={pageContainer}><LoadingPanel label="Loading the original task…" /></div>;

  return (
    <div className={`${pageContainer} max-w-6xl`}>
      <SectionBack to={`/sessions/${sessionId}/waiting`}>Waiting room</SectionBack>
      <div className="grid gap-8 lg:grid-cols-[.85fr_1.15fr] lg:gap-12">
        <aside className="self-start lg:sticky lg:top-24">
          <div className="rounded-[28px] bg-ink p-6 text-white sm:p-8">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.15em] text-mint"><EyeOff className="size-4" /> Private until submitted</div>
            <h1 className="mt-5 font-display text-3xl font-black leading-tight">What did this task mean to you?</h1>
            <div className="mt-7 border-t border-white/10 pt-6"><p className="text-xs font-black uppercase tracking-[0.15em] text-white/45">Original task</p><h2 className="mt-3 font-display text-xl font-black">{details?.title}</h2><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-white/65">{details?.description}</p>{details?.context ? <p className="mt-4 rounded-xl bg-white/7 p-3 text-xs leading-5 text-white/60">Context: {details.context}</p> : null}</div>
          </div>
        </aside>
        <form onSubmit={submit} className={`${formCard} space-y-7`}>
          {error ? <ErrorPanel message={error} /> : null}
          <Field label="Your interpretation" required hint={`${interpretation.length}/4000`}>
            <textarea autoFocus className={`${inputClass} min-h-52 resize-y text-base leading-7`} maxLength={4000} required placeholder="In your own words, what do you believe needs to be delivered? Include scope, behavior, responsibilities, or constraints that matter." value={interpretation} onChange={(e) => setInterpretation(e.target.value)} />
          </Field>
          <ListInput label="Assumptions you are making" values={assumptions} onChange={setAssumptions} placeholder="e.g. Phone login is outside the first release" />
          <ListInput label="What would count as success?" values={criteria} onChange={setCriteria} placeholder="e.g. A user can sign in and stay signed in" />
          <div className="rounded-2xl border border-ink/8 bg-cream p-4 text-sm leading-6 text-muted"><strong className="text-ink">Your words matter.</strong> The analysis should quote actual responses, so be specific enough for teammates to understand what you expected.</div>
          <Button type="submit" className="w-full" loading={saving}>Submit my interpretation <ArrowRight className="size-4" /></Button>
          <p className="flex items-center justify-center gap-2 text-xs text-muted"><ShieldCheck className="size-3.5" /> Draft saved on this device until submission succeeds.</p>
        </form>
      </div>
    </div>
  );
}

const issueTypeLabels: Record<string, string> = { contradiction: "Contradiction", assumption: "Assumption", omission: "Missing detail", scope_difference: "Scope difference", success_criteria_difference: "Success criteria" };

function IssueCard({ issue, onUpdated }: { issue: Issue; onUpdated: (issue: Issue) => void }) {
  const [mode, setMode] = useState<"closed" | "resolve">("closed");
  const [answer, setAnswer] = useState(issue.resolution_text || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isClosed = issue.status === "resolved" || issue.status === "dismissed";

  async function update(status: "resolved" | "dismissed") {
    if (status === "resolved" && !answer.trim()) { setError("Resolve karne se pehle clarification ka answer likhein."); return; }
    setLoading(true); setError("");
    try {
      const updated = await api.updateIssue(issue.id, { status, ...(answer.trim() ? { resolution_text: answer.trim() } : {}) });
      onUpdated({ ...issue, ...updated, status, resolution_text: answer.trim() || updated.resolution_text });
      setMode("closed");
    } catch (requestError) { setError(messageFromError(requestError)); }
    finally { setLoading(false); }
  }

  const priorityClass = issue.priority === "high" ? "bg-red-50 text-red-700 border-red-200" : issue.priority === "medium" ? "bg-yellow-soft text-yellow-800 border-yellow-200" : "bg-mint-soft text-mint-dark border-mint/40";

  return (
    <article className={`overflow-hidden rounded-[26px] border bg-white shadow-sm transition ${isClosed ? "border-ink/8 opacity-80" : "border-ink/12 hover:shadow-card"}`}>
      <div className="p-5 sm:p-7">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-ink px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-white">{issueTypeLabels[issue.type] || formatStatus(issue.type)}</span>
          <span className={`rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${priorityClass}`}>{issue.priority} priority</span>
          <span className={`ml-auto rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${issue.status === "resolved" ? "bg-mint-soft text-mint-dark" : issue.status === "dismissed" ? "bg-ink/7 text-muted" : "bg-coral-soft text-coral-dark"}`}>{formatStatus(issue.status)}</span>
        </div>
        <h2 className="mt-5 font-display text-2xl font-black leading-tight text-ink">{issue.title}</h2>
        <p className="mt-3 text-sm leading-7 text-muted">{issue.description}</p>
        {issue.impact ? <p className="mt-3 text-sm leading-6 text-ink/75"><strong className="text-ink">Why it matters:</strong> {issue.impact}</p> : null}

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {issue.evidence?.map((evidence, index) => <blockquote key={`${evidence.participant_id}-${index}`} className="rounded-2xl border border-ink/8 bg-cream p-4"><Quote className="size-4 text-coral" /><p className="mt-3 text-sm font-semibold leading-6 text-ink">“{evidence.quote}”</p><footer className="mt-3 text-xs font-bold text-muted">{evidence.display_name || evidence.participant_id}</footer></blockquote>)}
        </div>

        <div className="mt-6 rounded-2xl bg-ink p-5 text-white">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.13em] text-mint"><MessageCircleQuestion className="size-4" /> Clarify this</div>
          <p className="mt-3 font-display text-lg font-bold leading-7">{issue.clarification_question}</p>
        </div>

        {issue.resolution_text ? <div className="mt-4 flex gap-3 rounded-2xl bg-mint-soft p-4"><CheckCircle2 className="mt-0.5 size-5 shrink-0 text-mint-dark" /><div><p className="text-xs font-black uppercase tracking-[0.12em] text-mint-dark">Recorded decision</p><p className="mt-1 text-sm leading-6 text-ink">{issue.resolution_text}</p></div></div> : null}

        {!isClosed && mode === "closed" ? <div className="mt-5 flex flex-col gap-2 sm:flex-row"><Button onClick={() => setMode("resolve")}><MessageCircleQuestion className="size-4" /> Answer & resolve</Button><Button variant="secondary" loading={loading} onClick={() => update("dismissed")}><X className="size-4" /> Dismiss finding</Button></div> : null}
        {!isClosed && mode === "resolve" ? <div className="mt-5 rounded-2xl border border-coral/20 bg-coral-soft p-4"><Field label="Team decision"><textarea className={`${inputClass} min-h-24 resize-y`} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Record the specific decision the team agreed on." /></Field>{error ? <p className="mt-2 text-sm font-semibold text-red-700">{error}</p> : null}<div className="mt-3 flex gap-2"><Button loading={loading} onClick={() => update("resolved")}><Check className="size-4" /> Save resolution</Button><Button variant="ghost" onClick={() => setMode("closed")}>Cancel</Button></div></div> : null}
      </div>
    </article>
  );
}

export function MisunderstandingMapPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { identity, setAgreement } = useSession();
  const [issues, setIssues] = useState<Issue[]>([]);
  const [perspectives, setPerspectives] = useState<ComplementaryPerspective[]>([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "open" | "resolved" | "dismissed">("all");
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    if (!identity.hasSubmitted && identity.participantId) { setError("Apni interpretation submit karne ke baad hi findings dekhi ja sakti hain."); setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const analysis = await api.getIssues(sessionId);
      setIssues(analysis.issues);
      setPerspectives(analysis.complementary_perspectives);
      setSummary(analysis.summary || "");
    }
    catch (requestError) { setError(messageFromError(requestError)); }
    finally { setLoading(false); }
  }, [identity.hasSubmitted, identity.participantId, sessionId]);

  useEffect(() => { void load(); }, [load]);

  const counts = useMemo(() => ({ open: issues.filter((i) => i.status === "open").length, resolved: issues.filter((i) => i.status === "resolved").length, dismissed: issues.filter((i) => i.status === "dismissed").length }), [issues]);
  const visibleIssues = filter === "all" ? issues : issues.filter((issue) => issue.status === filter);

  async function createAgreement() {
    setGenerating(true); setError("");
    try { const result = await api.generateAgreement(sessionId); setAgreement(result); navigate(`/sessions/${sessionId}/agreement`); }
    catch (requestError) { setError(messageFromError(requestError)); }
    finally { setGenerating(false); }
  }

  return (
    <div className={pageContainer}>
      <SectionBack to={`/sessions/${sessionId}/waiting`}>Waiting room</SectionBack>
      <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
        <PageIntro eyebrow="Misunderstanding Map" title="Here’s where realities diverged." description="Each finding is a question to investigate—not a verdict about who is right." />
        <Button loading={generating} onClick={createAgreement}><ListChecks className="size-4" /> Generate agreement</Button>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="All findings" value={issues.length} />
        <StatCard label="Open" value={counts.open} tone="coral" />
        <StatCard label="Resolved" value={counts.resolved} tone="mint" />
        <StatCard label="Dismissed" value={counts.dismissed} tone="yellow" />
      </div>
      {summary ? <div className="mt-5 rounded-2xl border border-ink/8 bg-white p-5"><p className="text-xs font-black uppercase tracking-[0.13em] text-muted">Analysis summary</p><p className="mt-2 text-sm leading-7 text-ink">{summary}</p></div> : null}
      <div className="mt-7 flex flex-wrap gap-2">
        {(["all", "open", "resolved", "dismissed"] as const).map((item) => <button key={item} onClick={() => setFilter(item)} className={`rounded-full px-4 py-2 text-xs font-black capitalize transition ${filter === item ? "bg-ink text-white" : "border border-ink/10 bg-white text-muted hover:text-ink"}`}>{item}</button>)}
      </div>
      <div className="mt-6">
        {error ? <ErrorPanel message={error} onRetry={load} /> : loading ? <LoadingPanel label="Loading evidence-backed findings…" /> : !visibleIssues.length ? <EmptyPanel title={issues.length ? "Nothing in this filter" : "No potential gaps returned"} description={issues.length ? "Choose another status to see the remaining findings." : "The backend returned no issues for this session. You can still generate an agreement from the available task data."} /> : <div className="grid gap-5 lg:grid-cols-2">{visibleIssues.map((issue) => <IssueCard key={issue.id} issue={issue} onUpdated={(updated) => setIssues((current) => current.map((item) => item.id === updated.id ? updated : item))} />)}</div>}
      </div>
      {perspectives.length ? (
        <section className="mt-12">
          <div className="mb-5 flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-[0.16em] text-mint-dark">Compatible, not conflicting</p><h2 className="mt-2 font-display text-2xl font-black text-ink">Complementary perspectives</h2></div><span className="rounded-full bg-mint-soft px-3 py-1 text-xs font-black text-mint-dark">{perspectives.length}</span></div>
          <div className="grid gap-4 lg:grid-cols-2">
            {perspectives.map((perspective) => (
              <article key={perspective.id} className="rounded-[24px] border border-mint/40 bg-mint-soft p-5 sm:p-6">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.13em] text-mint-dark"><CheckCircle2 className="size-4" /> Adds useful context</div>
                <h3 className="mt-4 font-display text-xl font-black text-ink">{perspective.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{perspective.description}</p>
                <div className="mt-4 space-y-2">{perspective.evidence.map((evidence, index) => <blockquote key={`${evidence.participant_id}-${index}`} className="rounded-xl bg-white/70 p-3 text-sm font-semibold leading-6 text-ink">“{evidence.quote}”<footer className="mt-1 text-xs font-bold text-muted">{evidence.display_name || evidence.participant_id}</footer></blockquote>)}</div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function agreementCategory(item: AgreementItem) {
  if (item.category) return item.category;
  if (item.source === "resolved_issue" || item.source === "original_task") return "confirmed";
  if (item.source === "unresolved_issue") return "unresolved";
  return "suggestion";
}

export function AgreementPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { identity, setAgreement } = useSession();
  const [agreement, setLocalAgreement] = useState<Agreement | null>(identity.agreement || null);
  const [loading, setLoading] = useState(!identity.agreement);
  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const [confirming, setConfirming] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const result = await api.generateAgreement(sessionId); setAgreement(result); setLocalAgreement(result); }
    catch (requestError) { setError(messageFromError(requestError)); }
    finally { setLoading(false); }
  }, [sessionId, setAgreement]);

  useEffect(() => { if (!agreement) void load(); }, [agreement, load]);

  const grouped = useMemo(() => ({ confirmed: agreement?.items.filter((item) => agreementCategory(item) === "confirmed") || [], unresolved: agreement?.items.filter((item) => agreementCategory(item) === "unresolved") || [], suggestion: agreement?.items.filter((item) => !["confirmed", "unresolved"].includes(agreementCategory(item))) || [] }), [agreement]);

  async function confirm() {
    if (!identity.participantId || !agreement) { setError("Agreement confirm karne ke liye participant ID required hai."); return; }
    setConfirming(true); setError("");
    try { await api.confirmAgreement(agreement.agreement_id, { participant_id: identity.participantId, confirmed: true, comment: comment.trim() || null }); navigate(`/sessions/${sessionId}/bridge-test`); }
    catch (requestError) { setError(messageFromError(requestError)); }
    finally { setConfirming(false); }
  }

  if (loading) return <div className={pageContainer}><LoadingPanel label="Building the shared agreement…" /></div>;

  const sections = [
    { key: "confirmed" as const, title: "Confirmed requirements", description: "Decisions supported by the task or resolved issues.", icon: CheckCircle2, tone: "bg-mint-soft text-mint-dark" },
    { key: "unresolved" as const, title: "Unresolved decisions", description: "Questions the team still needs to close.", icon: CircleDot, tone: "bg-coral-soft text-coral-dark" },
    { key: "suggestion" as const, title: "Optional suggestions", description: "Ideas that are not accepted requirements yet.", icon: Lightbulb, tone: "bg-yellow-soft text-yellow-800" },
  ];

  return (
    <div className={`${pageContainer} max-w-6xl`}>
      <SectionBack to={`/sessions/${sessionId}/map`}>Misunderstanding Map</SectionBack>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><PageIntro eyebrow="Shared agreement" title="One plan everyone can point to." description="The checklist separates accepted decisions from questions and suggestions, so nothing quietly becomes a requirement." />{agreement ? <span className="rounded-full border border-ink/10 bg-white px-4 py-2 text-xs font-black uppercase tracking-wider text-muted">{formatStatus(agreement.status)}</span> : null}</div>
      {error ? <div className="mt-7"><ErrorPanel message={error} onRetry={load} /></div> : null}
      <div className="mt-9 grid gap-5">
        {sections.map(({ key, title, description, icon: Icon, tone }) => <section key={key} className={formCard}><div className="flex items-start gap-4"><div className={`grid size-11 shrink-0 place-items-center rounded-2xl ${tone}`}><Icon className="size-5" /></div><div className="flex-1"><div className="flex items-center justify-between gap-3"><h2 className="font-display text-xl font-black text-ink">{title}</h2><span className="text-sm font-black text-muted">{grouped[key].length}</span></div><p className="mt-1 text-sm text-muted">{description}</p><div className="mt-5 space-y-2">{grouped[key].length ? grouped[key].map((item, index) => <div key={item.id || index} className="flex items-start gap-3 rounded-xl border border-ink/8 bg-cream/70 p-4"><span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full ${key === "confirmed" ? "bg-mint text-ink" : "bg-white text-muted"}`}>{key === "confirmed" ? <Check className="size-3" /> : <Minus className="size-3" />}</span><p className="text-sm font-semibold leading-6 text-ink">{item.text}</p></div>) : <p className="rounded-xl border border-dashed border-ink/12 p-4 text-sm text-muted">No items returned in this category.</p>}</div></div></div></section>)}
      </div>
      <section className="mt-6 rounded-[28px] bg-ink p-6 text-white sm:p-8"><div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end"><div><div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-mint"><BookOpenCheck className="size-4" /> Your confirmation</div><h2 className="mt-3 font-display text-2xl font-black">Does this reflect the shared decision?</h2><textarea className="mt-4 min-h-20 w-full resize-y rounded-xl border border-white/15 bg-white/8 px-4 py-3 text-sm text-white outline-none placeholder:text-white/35 focus:border-mint" placeholder="Optional comment" value={comment} onChange={(e) => setComment(e.target.value)} /></div><Button className="bg-mint text-ink hover:bg-[#9ee4c5]" loading={confirming} onClick={confirm}>Confirm agreement <Check className="size-4" /></Button></div></section>
    </div>
  );
}

export function BridgeTestPage() {
  const { sessionId = "" } = useParams();
  const [metrics, setMetrics] = useState<Awaited<ReturnType<typeof api.getBridgeMetrics>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { setMetrics(await api.getBridgeMetrics(sessionId)); } catch (requestError) { setError(messageFromError(requestError)); } finally { setLoading(false); } }, [sessionId]);
  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className={pageContainer}><LoadingPanel label="Calculating the Bridge Test from saved records…" /></div>;
  const rate = metrics?.resolution_rate_percent;

  return (
    <div className={`${pageContainer} max-w-6xl`}>
      <SectionBack to={`/sessions/${sessionId}/agreement`}>Shared agreement</SectionBack>
      <div className="grid gap-10 lg:grid-cols-[.9fr_1.1fr] lg:items-start">
        <div><PageIntro eyebrow="Bridge Test" title="See how much of the gap was closed." description="These numbers come from saved issue states. They describe this session—not a universal score for human understanding." /><div className="mt-8 rounded-[28px] bg-ink p-7 text-white"><p className="text-xs font-black uppercase tracking-[0.15em] text-mint">Resolution rate</p><div className="mt-3 flex items-end gap-2"><span className="font-display text-7xl font-black tracking-[-0.06em]">{rate === null || rate === undefined ? "—" : rate}</span>{rate !== null && rate !== undefined ? <span className="mb-2 text-2xl font-black text-white/50">%</span> : null}</div><div className="mt-6"><ProgressBar value={rate ?? 0} /></div><p className="mt-4 text-sm leading-6 text-white/60">{rate === null ? "No initial issues were recorded, so a percentage is not applicable." : `The backend reports ${metrics?.resolved_issue_count ?? 0} resolved issue${metrics?.resolved_issue_count === 1 ? "" : "s"} from ${metrics?.initial_issue_count ?? 0} initially detected.`}</p></div></div>
        <div>{error ? <ErrorPanel message={error} onRetry={load} /> : metrics ? <><div className="grid grid-cols-2 gap-3"><StatCard label="Initial issues" value={metrics.initial_issue_count} /><StatCard label="Resolved" value={metrics.resolved_issue_count} tone="mint" /><StatCard label="Unresolved" value={metrics.unresolved_issue_count} tone="coral" /><StatCard label="Dismissed" value={metrics.dismissed_issue_count} tone="yellow" /></div><div className={`${formCard} mt-5`}><div className="flex items-center justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-[0.14em] text-muted">Agreement status</p><p className="mt-2 font-display text-2xl font-black text-ink">{formatStatus(metrics.agreement_status)}</p></div><div className="grid size-12 place-items-center rounded-2xl bg-mint-soft text-mint-dark"><Flag className="size-5" /></div></div><div className="mt-6 border-t border-ink/8 pt-6"><p className="text-sm leading-6 text-muted">A strong result is not always 100%. Remaining questions are useful when the team can see and address them explicitly.</p><Link to={`/sessions/${sessionId}/map`} className="mt-4 inline-block"><InlineLink>Review the map</InlineLink></Link></div></div></> : null}</div>
      </div>
    </div>
  );
}

export function NotFoundPage() {
  return <div className={`${pageContainer} grid min-h-[65vh] place-items-center text-center`}><div><p className="font-display text-8xl font-black text-ink/10">404</p><h1 className="mt-3 font-display text-3xl font-black text-ink">This reality doesn’t exist.</h1><p className="mt-3 text-muted">The page may have moved, or the session link is incomplete.</p><Link to="/" className="mt-6 inline-block"><Button>Return home <ArrowRight className="size-4" /></Button></Link></div></div>;
}
