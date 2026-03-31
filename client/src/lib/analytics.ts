/**
 * UMBRA — Analytics client TypeScript
 * Proxy server-side → la clé PostHog ne sort JAMAIS du backend.
 * Usage : import { track, UmbraEvent } from "@/lib/analytics"
 */

export const UmbraEvent = {
  LANDING_VUE:           "landing_vue",
  INSCRIPTION_DEMARREE:  "inscription_démarrée",
  PROFIL_CANDIDAT_CREE:  "profil_candidat_créé",
  OFFRE_PUBLIEE:         "offre_publiée",
  MATCHING_DECLENCHE:    "matching_déclenché",
  CONTACT_INITIE:        "contact_initié",
  CHECKOUT_LANCE:        "checkout_lancé",
  ABONNEMENT_ACTIVE:     "abonnement_activé",
  CV_ANALYSE:            "cv_analysé",
  REVELATION_MUTUELLE:   "révélation_mutuelle",
  PROFIL_VU:             "profil_vu",
  ENTRETIEN_INVERSE_POSE:"entretien_inversé_posé",
} as const;

export type UmbraEventType = typeof UmbraEvent[keyof typeof UmbraEvent];
export type UserType = "candidat" | "employeur";

// ── Distinct ID ───────────────────────────────────────────────────────────────

let _distinctId: string | null = null;

function getDistinctId(): string {
  if (_distinctId) return _distinctId;
  try {
    let id = localStorage.getItem("_umbra_aid");
    if (!id) {
      id = "anon_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem("_umbra_aid", id);
    }
    _distinctId = id;
    return id;
  } catch {
    return "anon_unknown";
  }
}

export function setUserId(accountId: string): void {
  _distinctId = accountId;
  try { localStorage.setItem("_umbra_aid", accountId); } catch {}
}

// ── Track ─────────────────────────────────────────────────────────────────────

export async function track(
  event: UmbraEventType,
  userType?: UserType,
  properties?: Record<string, unknown>
): Promise<void> {
  try {
    await fetch("/api/v1/analytics/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event,
        distinct_id: getDistinctId(),
        user_type: userType ?? null,
        properties: {
          ...properties,
          page: window.location.pathname,
          referrer: document.referrer,
          timestamp: new Date().toISOString(),
        },
      }),
    });

    // GA4
    const g = (window as any).gtag;
    if (typeof g === "function") {
      g("event", event.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/-/g, "_"), {
        event_category: "umbra",
        user_type: userType,
        ...properties,
      });
    }
  } catch {
    // Silencieux — analytics ne doit jamais crasher l'app
  }
}

// ── Sentry ────────────────────────────────────────────────────────────────────

export function captureError(error: Error, context?: Record<string, unknown>): void {
  const Sentry = (window as any).Sentry;
  if (!Sentry) return;
  try {
    Sentry.withScope((scope: any) => {
      if (context) {
        Object.entries(context).forEach(([k, v]) => scope.setExtra(k, v));
      }
      Sentry.captureException(error);
    });
  } catch {}
}

// ── useAnalytics hook ─────────────────────────────────────────────────────────

import { useCallback } from "react";

export function useAnalytics(userType?: UserType) {
  const trackEvent = useCallback(
    (event: UmbraEventType, properties?: Record<string, unknown>) =>
      track(event, userType, properties),
    [userType]
  );
  return { track: trackEvent, captureError };
}
