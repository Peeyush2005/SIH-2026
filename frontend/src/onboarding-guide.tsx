import React, { useState, useEffect } from 'react';
import { Icon } from './design';
import { useTranslation } from 'react-i18next';

export const ONBOARDING_KEY = 'bluecho-onboarding-dismissed';

export interface OnboardingStep {
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  highlight: string;
  detail: string;
}

/** Returns the 4 onboarding steps translated to the active language. */
export function useOnboardingSteps(): OnboardingStep[] {
  const { t } = useTranslation();
  return [
    {
      title: t('onboarding.step1_title'),
      subtitle: t('onboarding.step1_subtitle'),
      description: t('onboarding.step1_desc'),
      icon: 'upload',
      highlight: t('onboarding.step1_highlight'),
      detail: t('onboarding.step1_detail'),
    },
    {
      title: t('onboarding.step2_title'),
      subtitle: t('onboarding.step2_subtitle'),
      description: t('onboarding.step2_desc'),
      icon: 'model',
      highlight: t('onboarding.step2_highlight'),
      detail: t('onboarding.step2_detail'),
    },
    {
      title: t('onboarding.step3_title'),
      subtitle: t('onboarding.step3_subtitle'),
      description: t('onboarding.step3_desc'),
      icon: 'scan',
      highlight: t('onboarding.step3_highlight'),
      detail: t('onboarding.step3_detail'),
    },
    {
      title: t('onboarding.step4_title'),
      subtitle: t('onboarding.step4_subtitle'),
      description: t('onboarding.step4_desc'),
      icon: 'file',
      highlight: t('onboarding.step4_highlight'),
      detail: t('onboarding.step4_detail'),
    },
  ];
}

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
  const { t } = useTranslation();
  const steps = useOnboardingSteps();
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

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;
  const isFirst = currentStep === 0;
  const progress = ((currentStep + 1) / steps.length) * 100;

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
            <span>{t('onboarding.badge')}</span>
          </div>
          <div className="onboarding-header-right">
            <span className="onboarding-step-counter">
              {t('onboarding.step_counter', { current: currentStep + 1, total: steps.length })}
            </span>
            <button className="onboarding-close" onClick={dismiss} aria-label={t('onboarding.close')}>
              <Icon name="close" size={16} />
            </button>
          </div>
        </header>

        {/* ── Progress bar ── */}
        <div className="onboarding-progress-track" role="progressbar" aria-valuenow={currentStep+1} aria-valuemin={1} aria-valuemax={steps.length}>
          <div className="onboarding-progress-fill" style={{width: `${progress}%`}} />
        </div>

        {/* ── "Protect Our Ocean with BluEcho" tagline ── */}
        <div className="ob-tagline" aria-label={t('onboarding.tagline')}>
          <span className="ob-tagline-pulse" aria-hidden="true" />
          <span className="ob-tagline-ocean" aria-hidden="true">🌊</span>
          <p className="ob-tagline-text">
            <strong>Protect Our Ocean</strong>{' '}with BluEcho
          </p>
          <span className="ob-tagline-ocean" aria-hidden="true">🌊</span>
          <span className="ob-tagline-pulse" aria-hidden="true" />
        </div>

        {/* ── Animated ticker ── */}
        <div className="ob-ticker" aria-hidden="true">
          <div className="ob-ticker-track">
            {Array.from({length: 8}).map((_, i) => (
              <span key={i} className="ob-ticker-segment">
                <span className="ob-ticker-wave">🌊</span>
                <span className="ob-ticker-emphasis">PROTECT OUR OCEAN</span>
                <span className="ob-ticker-divider">·</span>
                <span className="ob-ticker-brand">WITH BLUECHO</span>
                <span className="ob-ticker-divider">·</span>
              </span>
            ))}
          </div>
        </div>

        {/* ── Step navigation pills ── */}
        <div className="onboarding-step-indicator" role="tablist" aria-label="Workflow steps">
          {steps.map((s, idx) => (
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
              {t('onboarding.try_demo')}
            </button>
            <button className="onboarding-text-btn skip-btn" onClick={dismiss}>
              {t('onboarding.skip')}
            </button>
          </div>

          <div className="onboarding-nav-actions">
            <button
              className="onboarding-nav-btn"
              onClick={() => goTo(currentStep - 1)}
              disabled={isFirst}
              aria-label="Previous step"
            >
              {t('onboarding.back')}
            </button>
            {!isLast ? (
              <button className="onboarding-nav-btn primary" onClick={() => goTo(currentStep + 1)}>
                {t('onboarding.next')} <Icon name="arrow" size={14} />
              </button>
            ) : (
              <button className="onboarding-nav-btn primary" onClick={handleInspect}>
                {t('onboarding.start')} <Icon name="arrow" size={14} />
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
  const { t } = useTranslation();
  const steps = useOnboardingSteps();
  return (
    <section className="how-it-works-section" aria-label={t('how_it_works.title')}>
      <div className="how-it-works-header">
        <div className="how-it-works-heading">
          <p className="section-kicker">{t('how_it_works.kicker')}</p>
          <h2>{t('how_it_works.title')}</h2>
          <p className="section-subtitle">
            {t('how_it_works.subtitle')}
          </p>
        </div>
        <div className="how-it-works-actions">
          <button className="help-trigger-button" onClick={onOpenGuide}>
            <Icon name="help" size={15} />
            {t('how_it_works.walkthrough_btn')}
          </button>
          <button className="quick-demo-button" onClick={onStartDemo}>
            <Icon name="scan" size={15} />
            {t('how_it_works.demo_btn')}
          </button>
        </div>
      </div>

      {/* Connector line + step cards */}
      <div className="workflow-steps-grid">
        {steps.map((step, idx) => (
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
