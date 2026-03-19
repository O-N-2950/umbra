import { useState, useEffect, useCallback, useRef } from "react";

/**
 * usePersistentForm — sauvegarde automatique dans localStorage
 * Usage: const [form, setForm, clearDraft] = usePersistentForm("cv-analyzer", { poste: "", ... })
 */
export function usePersistentForm<T extends Record<string, unknown>>(
  key: string,
  initialState: T,
  options: { debounceMs?: number } = {}
): [T, React.Dispatch<React.SetStateAction<T>>, () => void, string | null] {
  const { debounceMs = 600 } = options;
  const storageKey = `umbra_draft_${key}`;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initialize from localStorage if available
  const [form, setForm] = useState<T>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...initialState, ...parsed.data };
      }
    } catch {
      // ignore
    }
    return initialState;
  });

  const [savedAt, setSavedAt] = useState<string | null>(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.savedAt ?? null;
      }
    } catch {}
    return null;
  });

  // Debounced save to localStorage
  useEffect(() => {
    // Don't save if form equals initial state (nothing typed yet)
    const isInitial = Object.keys(initialState).every(
      k => form[k] === initialState[k]
    );
    if (isInitial) return;

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      try {
        const now = new Date().toISOString();
        localStorage.setItem(storageKey, JSON.stringify({ data: form, savedAt: now }));
        setSavedAt(now);
      } catch {
        // localStorage full or unavailable
      }
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [form]);

  const clearDraft = useCallback(() => {
    localStorage.removeItem(storageKey);
    setSavedAt(null);
    setForm(initialState);
  }, [storageKey]);

  return [form, setForm, clearDraft, savedAt];
}

/**
 * Format human-readable "sauvegardé il y a Xmin"
 */
export function formatDraftAge(savedAt: string | null): string | null {
  if (!savedAt) return null;
  const diff = Math.floor((Date.now() - new Date(savedAt).getTime()) / 1000);
  if (diff < 60) return "à l'instant";
  if (diff < 3600) return `il y a ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `il y a ${Math.floor(diff / 3600)}h`;
  return `il y a ${Math.floor(diff / 86400)} j`;
}
