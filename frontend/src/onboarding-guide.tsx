import React, { useState } from 'react';
import { Icon } from './design';

export const ONBOARDING_KEY = 'bluecho-onboarding-dismissed';

export interface OnboardingStep {
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  highlight: string;
}

export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    title: 'Upload Sonar Imagery',
    subtitle: 'Step One',
    description: 'Import side-scan sonar (SSS) or forward-looking sonar (FLS) records and images. Raw formats like XTF and standard images are supported.',
    icon: 'upload',
    highlight: 'Your imagery stays private on your system during local processing.'
  },
  {
    title: 'Select Sensor & Detector',
    subtitle: 'Step Two',
    description: 'Confirm the sonar type and pair your imagery with the matching specialized detector—whether looking for seabed debris, pipelines, or lost gear.',
    icon: 'model',
    highlight: 'Detectors are tuned to specific sonar acoustics for maximum clarity.'
  },
  {
    title: 'Inspect & Review Findings',
    subtitle: 'Step Three',
    description: 'Examine candidate detections directly on the original acoustic pixels. Retain valid findings, flag false alerts, or refine boundaries.',
    icon: 'scan',
    highlight: 'Human judgement remains in control; original predictions stay traceable.'
  },
  {
    title: 'Export Defensible Reports',
    subtitle: 'Step Four',
    description: 'Download field-ready PDF summary briefs, mapped GeoJSON vectors, CSV logs, or full evidence packages for stakeholders.',
    icon: 'file',
    highlight: 'Every report preserves data provenance and full review history.'
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

  if (!isOpen) return null;

  const step = ONBOARDING_STEPS[currentStep];
  const isLast = currentStep === ONBOARDING_STEPS.length - 1;

  function dismiss() {
    try {
      localStorage.setItem(ONBOARDING_KEY, 'true');
    } catch {}
    onClose();
  }

  function handleDemo() {
    dismiss();
    onStartDemo?.();
  }

  function handleInspect() {
    dismiss();
    onStartInspect?.();
  }

  return (
    <div className="onboarding-backdrop" role="dialog" aria-modal="true" aria-labelledby="onboarding-modal-title">
      <div className="onboarding-modal">
        <header className="onboarding-header">
          <div className="onboarding-badge">
            <Icon name="compass" size={16} />
            <span>OPERATOR GUIDE</span>
          </div>
          <button className="onboarding-close" onClick={dismiss} aria-label="Close guide">
            <Icon name="close" size={18} />
          </button>
        </header>

        <div className="onboarding-body">
          <div className="onboarding-step-indicator">
            {ONBOARDING_STEPS.map((s, idx) => (
              <button
                key={s.subtitle}
                className={'step-pill ' + (idx === currentStep ? 'active ' : '') + (idx < currentStep ? 'completed ' : '')}
                onClick={() => setCurrentStep(idx)}
                aria-label={`Go to ${s.subtitle}: ${s.title}`}
              >
                <span className="pill-number">{idx < currentStep ? <Icon name="check" size={12} /> : idx + 1}</span>
                <span className="pill-text">{s.title}</span>
              </button>
            ))}
          </div>

          <div className="onboarding-card">
            <div className="onboarding-icon-wrap">
              <Icon name={step.icon} size={32} />
            </div>
            <div className="onboarding-content">
              <span className="onboarding-step-label">{step.subtitle}</span>
              <h2 id="onboarding-modal-title">{step.title}</h2>
              <p className="onboarding-desc">{step.description}</p>
              <div className="onboarding-highlight">
                <Icon name="shield" size={16} />
                <span>{step.highlight}</span>
              </div>
            </div>
          </div>
        </div>

        <footer className="onboarding-footer">
          <div className="onboarding-footer-left">
            <button className="onboarding-text-btn" onClick={handleDemo}>
              <Icon name="scan" size={16} />
              Try Real Demo
            </button>
            <button className="onboarding-text-btn skip-btn" onClick={dismiss}>
              Skip guide
            </button>
          </div>

          <div className="onboarding-nav-actions">
            {currentStep > 0 && (
              <button className="onboarding-nav-btn" onClick={() => setCurrentStep(c => c - 1)}>
                Previous
              </button>
            )}
            {!isLast ? (
              <button className="primary onboarding-nav-btn" onClick={() => setCurrentStep(c => c + 1)}>
                Next <Icon name="arrow" size={16} />
              </button>
            ) : (
              <button className="primary onboarding-nav-btn" onClick={handleInspect}>
                Start Inspection <Icon name="arrow" size={16} />
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
  onStartInspect
}: {
  onOpenGuide: () => void;
  onStartDemo: () => void;
  onStartInspect: () => void;
}) {
  return (
    <section className="how-it-works-section" aria-label="How BluEco Works">
      <div className="how-it-works-header">
        <div>
          <p className="section-kicker">WORKFLOW OVERVIEW</p>
          <h2>How BluEco Works in the Field</h2>
          <p className="section-subtitle">
            From raw acoustic pings to a validated inspection report in four clear stages.
          </p>
        </div>
        <div className="how-it-works-actions">
          <button className="help-trigger-button" onClick={onOpenGuide}>
            <Icon name="help" size={16} />
            Operator Walkthrough
          </button>
          <button className="quick-demo-button" onClick={onStartDemo}>
            <Icon name="scan" size={16} />
            Try Demo
          </button>
        </div>
      </div>

      <div className="workflow-steps-grid">
        {ONBOARDING_STEPS.map((step, idx) => (
          <article className="workflow-step-card" key={step.subtitle}>
            <div className="step-card-top">
              <span className="step-card-number">{idx + 1}</span>
              <span className="step-card-icon">
                <Icon name={step.icon} size={22} />
              </span>
            </div>
            <h3>{step.title}</h3>
            <p>{step.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
