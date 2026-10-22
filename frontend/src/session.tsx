import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Agreement, SessionIdentity } from "./types";

const STORAGE_KEY = "misunderstood.session";

const emptyIdentity: SessionIdentity = {
  sessionId: "",
  isCreator: false,
  hasSubmitted: false,
};

function loadIdentity(): SessionIdentity {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value ? { ...emptyIdentity, ...JSON.parse(value) } : emptyIdentity;
  } catch {
    return emptyIdentity;
  }
}

interface SessionContextValue {
  identity: SessionIdentity;
  setIdentity: (identity: SessionIdentity) => void;
  patchIdentity: (patch: Partial<SessionIdentity>) => void;
  setAgreement: (agreement: Agreement) => void;
  clearIdentity: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentityState] = useState<SessionIdentity>(loadIdentity);

  const persist = useCallback((next: SessionIdentity) => {
    setIdentityState(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const setIdentity = useCallback((next: SessionIdentity) => persist(next), [persist]);

  const patchIdentity = useCallback(
    (patch: Partial<SessionIdentity>) => persist({ ...identity, ...patch }),
    [identity, persist],
  );

  const setAgreement = useCallback(
    (agreement: Agreement) => patchIdentity({ agreement }),
    [patchIdentity],
  );

  const clearIdentity = useCallback(() => {
    setIdentityState(emptyIdentity);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const value = useMemo(
    () => ({ identity, setIdentity, patchIdentity, setAgreement, clearIdentity }),
    [identity, setIdentity, patchIdentity, setAgreement, clearIdentity],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}

export function draftKey(sessionId: string, participantId: string) {
  return `misunderstood.draft.${sessionId}.${participantId}`;
}
