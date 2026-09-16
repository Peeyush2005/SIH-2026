import React, { useState, useEffect } from 'react';
import { Icon } from './design';

export const ONBOARDING_KEY = 'bluecho-onboarding-dismissed';

export interface OnboardingStep {
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  highlight: string;
  detail: string;
}

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    title: 'Upload Sonar Imagery',
    subtitle: 'Step 1 of 4',
    description: 'Import side-scan sonar (SSS) or forward-looking sonar (FLS) records. Raw XTF recordings and standard image formats (PNG, JPG, BMP, PBM) are all supported.',
    icon: 'upload',
    highlight: 'Your imagery stays private — processed locally on your device.',
    detail: 'Supports XTF, PNG, JPG, BMP, PBM · TIFF / GeoTIFF'
  },
  {
    title: 'Select Sensor & Detector',
    subtitle: 'Step 2 of 4',
    description: 'Confirm the sonar type and pair your imagery with a specialized detector. Each model is calibrated to a specific acoustic profile — side-scan pipelines, FLS debris, or ghost-pot detection.',
    icon: 'model',
    highlight: 'Detectors are tuned to specific sonar acoustics for maximum precision.',
    detail: 'SSS · SSS_LF · FLS_ARIS · FLS_UATD sensor routes'
  },
  {
    title: 'Inspect & Review Findings',
    subtitle: 'Step 3 of 4',
    description: 'Examine candidate detections directly on the original acoustic pixels. Retain valid findings, flag false alerts, adjust bounding boxes, and attach field notes — all decisions are traceable.',
    icon: 'scan',
    highlight: 'Human judgement stays in control; original model predictions remain immutable.',
    detail: 'Retain · False alert · Uncertain · Correct label or box'
  },
  {
    title: 'Export Defensible Reports',
    subtitle: 'Step 4 of 4',
    description: 'Download field-ready PDF summary briefs, mapped GeoJSON vectors, CSV anomaly logs, portable HTML evidence bundles, or complete ZIP packages for stakeholders and auditors.',
    icon: 'file',
    highlight: 'Every export preserves data provenance and your full review history.',
    detail: 'PDF · GeoJSON · CSV · HTML · ZIP · JSON formats'
  }
];

export function OnboardingModal({
  isOpen,
  onClose,
  onStartDemo,
  onStartInspect
}: {
  isOpen: boolean;
  onClose: () => void;
  onStartDemo?: () => void;
  onStartInspect?: () => void;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [animDir, setAnimDir] = useState<'next'|'prev'|null>(null);

  // Reset step when re-opened
  useEffect(() => {
    if (isOpen) setCurrentStep(0);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') dismiss(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen]);

  if (!isOpen) return null;

  const step = ONBOARDING_STEPS[currentStep];
  const isLast = currentStep === ONBOARDING_STEPS.length - 1;
  const isFirst = currentStep === 0;
  const progress = ((currentStep + 1) / ONBOARDING_STEPS.length) * 100;

  function goTo(idx: number) {
    setAnimDir(idx > currentStep ? 'next' : 'prev');
    setCurrentStep(idx);
  }

  function dismiss() {
    try { localStorage.setItem(ONBOARDING_KEY, 'true'); } catch {}
    onClose();
  }

  function handleDemo() { dismiss(); onStartDemo?.(); }
  function handleInspect() { dismiss(); onStartInspect?.(); }

  return (
    <div
      className="onboarding-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-modal-title"
      onClick={(e) => { if (e.target === e.currentTarget) dismiss(); }}
    >
      <div className="onboarding-modal">

        {/* ── Header ── */}
        <header className="onboarding-header">
          <div className="onboarding-badge">
            <Icon name="compass" size={15} />
            <span>Operator Guide</span>
          </div>
          <div className="onboarding-header-right">
            <span className="onboarding-step-counter">{currentStep + 1} / {ONBOARDING_STEPS.length}</span>
            <button className="onboarding-close" onClick={dismiss} aria-label="Close guide">
              <Icon name="close" size={16} />
            </button>
          </div>
        </header>

        {/* ── Progress bar ── */}
        <div className="onboarding-progress-track" role="progressbar" aria-valuenow={currentStep+1} aria-valuemin={1} aria-valuemax={ONBOARDING_STEPS.length}>
          <div className="onboarding-progress-fill" style={{width: `${progress}%`}} />
        </div>

        {/* ── Step navigation pills ── */}
        <div className="onboarding-step-indicator" role="tablist" aria-label="Workflow steps">
          {ONBOARDING_STEPS.map((s, idx) => (
            <button
              key={s.subtitle}
              role="tab"
              aria-selected={idx === currentStep}
              className={
                'step-pill' +
                (idx === currentStep ? ' active' : '') +
                (idx < currentStep ? ' completed' : '')
              }
              onClick={() => goTo(idx)}
              aria-label={`${s.subtitle}: ${s.title}`}
            >
              <span className="pill-number" aria-hidden="true">
                {idx < currentStep ? <Icon name="check" size={11} /> : idx + 1}
              </span>
              <span className="pill-text">{s.title}</span>
            </button>
          ))}
        </div>

        {/* ── Step card ── */}
        <div className="onboarding-body">
          <div className={`onboarding-card onboarding-card--${animDir || 'idle'}`}
            key={currentStep}
          >
            {/* Icon + step label row */}
            <div className="onboarding-card-top">
              <div className="onboarding-icon-wrap" aria-hidden="true">
                <Icon name={step.icon} size={28} />
              </div>
              <div className="onboarding-card-meta">
                <span className="onboarding-step-label">{step.subtitle}</span>
                <span className="onboarding-detail-tag">{step.detail}</span>
              </div>
            </div>

            {/* Title + description */}
            <h2 id="onboarding-modal-title" className="onboarding-card-title">{step.title}</h2>
            <p className="onboarding-desc">{step.description}</p>

            {/* Highlight callout */}
            <div className="onboarding-highlight">
              <span className="onboarding-highlight-icon" aria-hidden="true">
                <Icon name="shield" size={14} />
              </span>
              <span>{step.highlight}</span>
            </div>
          </div>
        </div>

        {/* ── Footer ── */}
        <footer className="onboarding-footer">
          <div className="onboarding-footer-left">
            <button className="onboarding-text-btn" onClick={handleDemo}>
              <Icon name="scan" size={14} />
              Try demo
            </button>
            <button className="onboarding-text-btn skip-btn" onClick={dismiss}>
              Skip
            </button>
          </div>

          <div className="onboarding-nav-actions">
            <button
              className="onboarding-nav-btn"
              onClick={() => goTo(currentStep - 1)}
              disabled={isFirst}
              aria-label="Previous step"
            >
              ← Back
            </button>
            {!isLast ? (
              <button className="onboarding-nav-btn primary" onClick={() => goTo(currentStep + 1)}>
                Next <Icon name="arrow" size={14} />
              </button>
            ) : (
              <button className="onboarding-nav-btn primary" onClick={handleInspect}>
                Start Inspection <Icon name="arrow" size={14} />
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
  );
}

export function HowItWorksSection({
  onOpenGuide,
  onStartDemo,
}: {
  onOpenGuide: () => void;
  onStartDemo: () => void;
  onStartInspect: () => void;
}) {
  return (
    <section className="how-it-works-section" aria-label="How BluEco Works">
      <div className="how-it-works-header">
        <div className="how-it-works-heading">
          <p className="section-kicker">WORKFLOW OVERVIEW</p>
          <h2>How BluEco Works in the Field</h2>
          <p className="section-subtitle">
            From raw acoustic pings to a validated inspection report — four clear stages.
          </p>
        </div>
        <div className="how-it-works-actions">
          <button className="help-trigger-button" onClick={onOpenGuide}>
            <Icon name="help" size={15} />
            Operator Walkthrough
          </button>
          <button className="quick-demo-button" onClick={onStartDemo}>
            <Icon name="scan" size={15} />
            Try Demo
          </button>
        </div>
      </div>

      {/* Connector line + step cards */}
      <div className="workflow-steps-grid">
        {ONBOARDING_STEPS.map((step, idx) => (
          <article className="workflow-step-card" key={step.subtitle} onClick={onOpenGuide} tabIndex={0} role="button" aria-label={`Learn about ${step.title}`}>
            <div className="step-card-top">
              <span className="step-card-number" aria-label={`Step ${idx + 1}`}>{idx + 1}</span>
              <span className="step-card-icon" aria-hidden="true">
                <Icon name={step.icon} size={20} />
              </span>
            </div>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
            <span className="step-card-detail">{step.detail}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
