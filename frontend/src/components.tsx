import {
  AlertCircle,
  ArrowRight,
  Check,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Users,
} from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Logo() {
  return (
    <div className="flex items-center gap-2.5" aria-label="MISUNDERSTOOD">
      <div className="relative grid size-9 place-items-center rounded-xl bg-ink text-white shadow-sm">
        <span className="absolute left-[8px] top-[10px] h-3 w-3 rounded-full border-2 border-coral" />
        <span className="absolute bottom-[9px] right-[8px] h-3 w-3 rounded-full border-2 border-mint" />
      </div>
      <span className="font-display text-sm font-black tracking-[0.12em] text-ink sm:text-base">
        MISUNDERSTOOD
      </span>
    </div>
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
};

export function Button({
  className = "",
  variant = "primary",
  loading,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const variants = {
    primary: "bg-ink text-white hover:bg-[#28283a] shadow-[0_8px_20px_rgba(31,31,46,.16)]",
    secondary: "border border-ink/15 bg-white text-ink hover:border-ink/35 hover:bg-cream",
    ghost: "text-ink hover:bg-ink/5",
    danger: "border border-red-200 bg-red-50 text-red-700 hover:bg-red-100",
  };
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition focus:outline-none focus:ring-4 focus:ring-coral/20 disabled:cursor-not-allowed disabled:opacity-55 ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle className="size-4 animate-spin" /> : null}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="flex items-center justify-between gap-3 text-sm font-bold text-ink">
        <span>
          {label} {required ? <span className="text-coral">*</span> : null}
        </span>
        {hint ? <span className="text-xs font-medium text-muted">{hint}</span> : null}
      </span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-muted/70 focus:border-coral focus:ring-4 focus:ring-coral/10";

export function PageIntro({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-2xl">
      <p className="mb-3 text-xs font-black uppercase tracking-[0.18em] text-coral">{eyebrow}</p>
      <h1 className="font-display text-3xl font-black leading-tight text-ink sm:text-5xl">{title}</h1>
      <p className="mt-4 text-base leading-7 text-muted sm:text-lg">{description}</p>
    </div>
  );
}

export function ErrorPanel({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800">
      <AlertCircle className="mt-0.5 size-5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-bold">Request complete nahi hui</p>
        <p className="mt-1 break-words text-sm leading-6">{message}</p>
      </div>
      {onRetry ? (
        <button className="rounded-lg p-2 hover:bg-red-100" onClick={onRetry} aria-label="Retry">
          <RefreshCw className="size-4" />
        </button>
      ) : null}
    </div>
  );
}

export function LoadingPanel({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="grid min-h-56 place-items-center rounded-3xl border border-ink/10 bg-white/70 p-8 text-center">
      <div>
        <LoaderCircle className="mx-auto size-7 animate-spin text-coral" />
        <p className="mt-3 text-sm font-semibold text-muted">{label}</p>
      </div>
    </div>
  );
}

export function EmptyPanel({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-ink/20 bg-white/60 p-8 text-center">
      <CircleAlert className="mx-auto size-7 text-muted" />
      <h2 className="mt-3 font-display text-xl font-bold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{description}</p>
    </div>
  );
}

export function ProgressBar({ value }: { value: number }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2.5 overflow-hidden rounded-full bg-ink/8" aria-label={`${safeValue}% complete`}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-coral to-[#f7b267] transition-[width] duration-500"
        style={{ width: `${safeValue}%` }}
      />
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "coral" | "mint" | "yellow";
}) {
  const tones = {
    default: "bg-white",
    coral: "bg-coral-soft",
    mint: "bg-mint-soft",
    yellow: "bg-yellow-soft",
  };
  return (
    <div className={`rounded-2xl border border-ink/8 p-5 ${tones[tone]}`}>
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-2 font-display text-3xl font-black text-ink">{value}</p>
    </div>
  );
}

export function StepBadge({ number, done }: { number: number; done?: boolean }) {
  return (
    <div
      className={`grid size-8 shrink-0 place-items-center rounded-full text-xs font-black ${
        done ? "bg-mint text-ink" : "bg-ink text-white"
      }`}
    >
      {done ? <Check className="size-4" /> : number}
    </div>
  );
}

export function InlineLink({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 font-bold text-coral">
      {children} <ArrowRight className="size-4" />
    </span>
  );
}

export function PeopleIcon() {
  return (
    <div className="grid size-11 place-items-center rounded-2xl bg-mint-soft text-ink">
      <Users className="size-5" />
    </div>
  );
}
