"use client";
import { useEffect, useRef, useState } from "react";

export type StreamState = "connecting" | "open" | "reconnecting" | "closed";

export function useEventStream(url: string | null, onEvent: (payload: unknown) => void) {
  const [state, setState] = useState<StreamState>(url ? "connecting" : "closed");
  const sequenceRef = useRef(0);
  const callbackRef = useRef(onEvent);
  callbackRef.current = onEvent;

  useEffect(() => {
    if (!url) { setState("closed"); return; }
    let source: EventSource | null = null;
    let cancelled = false;
    let retry: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      const separator = url.includes("?") ? "&" : "?";
      source = new EventSource(`${url}${separator}after_sequence=${sequenceRef.current}`);
      setState(sequenceRef.current ? "reconnecting" : "connecting");
      source.onopen = () => setState("open");
      source.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as { sequence?: number };
          if (typeof payload.sequence === "number") sequenceRef.current = Math.max(sequenceRef.current, payload.sequence);
          callbackRef.current(payload);
        } catch { /* malformed event is ignored, backend remains authoritative */ }
      };
      // Named SSE events do not trigger onmessage in every browser, so subscribe to the
      // MedClaimIQ event families the reviewer surface relies on.
      const named = ["review.lock.acquired", "review.lock.renewed", "review.lock.released", "review.started", "review.note.added", "review.evidence.requested", "review.decision.recorded", "sla.timer.warning", "sla.timer.breached", "rag.guardrail.escalated", "agent.workflow.completed", "agent.workflow.interrupted", "appeal.reconsideration.reingestion.queued", "appeal.reconsideration.reingestion.completed", "appeal.reconsideration.fhir.updated", "appeal.reconsideration.snapshot.locked", "appeal.reconsideration.rag.completed", "appeal.reconsideration.agent.completed", "appeal.reconsideration.annotation.added", "appeal.reconsideration.missing_evidence.requested", "appeal.reconsideration.escalated", "appeal.reconsideration.checkpoint.resumed"];
      for (const name of named) source.addEventListener(name, (event) => {
        try {
          const payload = JSON.parse((event as MessageEvent).data) as { sequence?: number };
          if (typeof payload.sequence === "number") sequenceRef.current = Math.max(sequenceRef.current, payload.sequence);
          callbackRef.current(payload);
        } catch { /* ignore malformed event */ }
      });
      source.onerror = () => {
        source?.close();
        if (!cancelled) {
          setState("reconnecting");
          retry = setTimeout(connect, 1500);
        }
      };
    };
    connect();
    return () => { cancelled = true; if (retry) clearTimeout(retry); source?.close(); setState("closed"); };
  }, [url]);

  return { state, lastSequence: sequenceRef.current };
}
