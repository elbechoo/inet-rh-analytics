'use client';
/* Interaction primitives — the things that make a UI feel alive:
   numbers that count up, sections that reveal as you scroll, buttons that
   ripple under the cursor, and values that flash when they change. */
import { useEffect, useRef, useState } from 'react';

/* ── Count-up number ─────────────────────────────────────
   Animates from the previous value to the new one, so KPIs roll rather than
   snap. Re-runs whenever the value changes, not just on mount. */
export function AnimatedNumber({
  value, duration = 900, decimals = 0, suffix = '', prefix = '',
}: { value: number; duration?: number; decimals?: number; suffix?: string; prefix?: string }) {
  const [display, setDisplay] = useState(0);
  const from = useRef(0);
  const raf  = useRef<number | undefined>(undefined);

  useEffect(() => {
    const start = performance.now();
    const a = from.current;
    const b = Number.isFinite(value) ? value : 0;
    if (a === b) { setDisplay(b); return; }

    const tick = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);           // ease-out cubic
      setDisplay(a + (b - a) * eased);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else from.current = b;
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [value, duration]);

  return (
    <span className="t-num">
      {prefix}{display.toFixed(decimals)}{suffix}
    </span>
  );
}

/* ── Reveal on scroll ────────────────────────────────────
   Sections animate in as they enter the viewport instead of all firing at
   once on load — the page stays alive while you scroll it. */
export function Reveal({
  children, delay = 0, y = 16, className = '', style,
}: {
  children: React.ReactNode; delay?: number; y?: number;
  className?: string; style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') { setShown(true); return; }
    const io = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setShown(true); io.disconnect(); } },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? 'none' : `translateY(${y}px)`,
        transition: `opacity 520ms cubic-bezier(.16,1,.3,1) ${delay}ms, transform 520ms cubic-bezier(.16,1,.3,1) ${delay}ms`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/* ── Ripple ──────────────────────────────────────────────
   Drop inside any position:relative element to get a material-style ripple
   from the exact click point. */
export function useRipple() {
  return (e: React.MouseEvent<HTMLElement>) => {
    const host = e.currentTarget;
    const rect = host.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const span = document.createElement('span');
    span.className = 'ripple';
    span.style.width = span.style.height = `${size}px`;
    span.style.left = `${e.clientX - rect.left - size / 2}px`;
    span.style.top  = `${e.clientY - rect.top  - size / 2}px`;
    host.appendChild(span);
    window.setTimeout(() => span.remove(), 620);
  };
}

/* ── Flash on change ─────────────────────────────────────
   Briefly highlights a value when it updates — useful for live counters. */
export function useFlashOnChange<T>(value: T) {
  const [flash, setFlash] = useState(false);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    setFlash(true);
    const t = window.setTimeout(() => setFlash(false), 700);
    return () => window.clearTimeout(t);
  }, [value]);
  return flash;
}
