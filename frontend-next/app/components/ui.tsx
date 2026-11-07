'use client';
/* ============================================================================
   iNET RH - UI primitives
   A small, dependency-free component set built on the design tokens in
   globals.css. Import these instead of writing inline styles, so pages stay
   consistent and the whole app can be re-themed (or white-labelled per client)
   by changing tokens in one place.

   Usage:
     import { Card, StatCard, Badge, Button, PageHeader, EmptyState, Skeleton } from '@/app/components/ui';
   ========================================================================== */
import React from 'react';

type Tone = 'green' | 'yellow' | 'red' | 'purple' | 'blue' | 'gray' | 'cyan';

export const TONE_COLOR: Record<Tone, string> = {
  green:  'var(--success)',
  yellow: 'var(--warning)',
  red:    'var(--danger)',
  purple: 'var(--purple)',
  blue:   'var(--brand-400)',
  cyan:   'var(--cyan)',
  gray:   'var(--gray-500)',
};

/* ── Card ─────────────────────────────────────────────── */
export function Card({
  children, hover = false, className = '', style, ...rest
}: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return (
    <div
      className={`card${hover ? ' card-hover' : ''}${className ? ' ' + className : ''}`}
      style={style}
      {...rest}
    >
      {children}
    </div>
  );
}

/* Section title + optional subtitle and right-side action. */
export function CardHeader({
  title, subtitle, action,
}: { title: React.ReactNode; subtitle?: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="card-head">
      <div style={{ minWidth: 0 }}>
        <div className="t-section" style={{ color: 'var(--gray-900)' }}>{title}</div>
        {subtitle && <div className="t-meta" style={{ marginTop: 2 }}>{subtitle}</div>}
      </div>
      {action}
    </div>
  );
}

/* ── Button ───────────────────────────────────────────── */
export function Button({
  variant = 'primary', children, className = '', ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
}) {
  return (
    <button className={`btn-${variant}${className ? ' ' + className : ''}`} {...rest}>
      {children}
    </button>
  );
}

/* ── Badge ────────────────────────────────────────────── */
export function Badge({
  tone = 'gray', dot = false, children,
}: { tone?: Tone; dot?: boolean; children: React.ReactNode }) {
  return (
    <span className={`badge badge-${tone}`}>
      {dot && <span className="dot" style={{ background: TONE_COLOR[tone] }} />}
      {children}
    </span>
  );
}

/* ── Skeleton ─────────────────────────────────────────── */
export function Skeleton({
  height = 16, width = '100%', radius = 6, style,
}: { height?: number | string; width?: number | string; radius?: number; style?: React.CSSProperties }) {
  return <div className="skeleton" style={{ width, height, borderRadius: radius, ...style }} />;
}

/* ── Page header ──────────────────────────────────────── */
export function PageHeader({
  title, subtitle, eyebrow, actions,
}: {
  title: React.ReactNode; subtitle?: React.ReactNode;
  eyebrow?: React.ReactNode; actions?: React.ReactNode;
}) {
  return (
    <header style={{
      display: 'flex', justifyContent: 'space-between',
      alignItems: 'flex-start', gap: 20, marginBottom: 26,
    }}>
      <div style={{ minWidth: 0 }}>
        {eyebrow && <div className="t-meta" style={{ marginBottom: 5 }}>{eyebrow}</div>}
        <h1 className="t-title" style={{ color: 'var(--gray-900)' }}>{title}</h1>
        {subtitle && <p className="t-meta" style={{ marginTop: 4 }}>{subtitle}</p>}
      </div>
      {actions && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {actions}
        </div>
      )}
    </header>
  );
}

/* ── Stat card ────────────────────────────────────────── */
/* Restrained by design: the number carries the emphasis, colour is a quiet
   accent on the icon only. `value === null` renders a skeleton so the layout
   never jumps while data loads. */
export function StatCard({
  label, value, sub, tone = 'blue', icon: Icon, href,
}: {
  label: string;
  value: React.ReactNode | null;
  sub?: string;
  tone?: Tone;
  icon?: React.ElementType;
  href?: string;
}) {
  const color = TONE_COLOR[tone];
  const body = (
    <div className="card card-hover" style={{ padding: 18, height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <span className="t-label">{label}</span>
        {Icon && (
          <span style={{
            width: 28, height: 28, borderRadius: 'var(--radius-sm)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(12,36,54,0.04)', color, flexShrink: 0,
          }}>
            <Icon size={15} />
          </span>
        )}
      </div>
      <div className="t-num" style={{
        fontSize: '1.9rem', fontWeight: 680, color: 'var(--gray-900)',
        lineHeight: 1.1, marginTop: 10, letterSpacing: '-0.03em', minHeight: '2rem',
      }}>
        {value === null ? <Skeleton width={54} height={24} /> : value}
      </div>
      {sub && <div className="t-meta" style={{ marginTop: 3 }}>{sub}</div>}
    </div>
  );
  return href ? <a href={href} style={{ display: 'block' }}>{body}</a> : body;
}

/* ── Empty state ──────────────────────────────────────── */
export function EmptyState({
  icon: Icon, title, hint, action,
}: { icon?: React.ElementType; title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="empty-state">
      {Icon && <div className="empty-state-icon"><Icon size={18} /></div>}
      <div style={{ color: 'var(--gray-700)', fontWeight: 550, fontSize: '0.84rem' }}>{title}</div>
      {hint && <div className="t-meta" style={{ marginTop: 3, maxWidth: 320 }}>{hint}</div>}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  );
}

/* ── Progress ─────────────────────────────────────────── */
export function Progress({ value, tone = 'blue' }: { value: number; tone?: Tone }) {
  return (
    <div className="progress-track">
      <div
        className="progress-fill"
        style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: TONE_COLOR[tone] }}
      />
    </div>
  );
}

/* ── Avatar ───────────────────────────────────────────── */
export function Avatar({ name, size = 30 }: { name?: string; size?: number }) {
  const initials = (name || '')
    .split(' ').filter(Boolean).slice(0, 2)
    .map(w => w[0]?.toUpperCase()).join('') || '-';
  return (
    <div style={{
      width: size, height: size, borderRadius: 'var(--radius-full)',
      background: 'rgba(15,163,224,0.14)', color: 'var(--brand-400)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.36, fontWeight: 600, flexShrink: 0,
      border: '1px solid rgba(15,163,224,0.2)',
    }}>
      {initials}
    </div>
  );
}
