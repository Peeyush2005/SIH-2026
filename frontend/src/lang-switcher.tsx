import React from 'react';
import { useTranslation } from 'react-i18next';
import i18n from './i18n';

const LANGS = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  // Phase 2: { code: 'mr', label: 'मराठी' },
] as const;

export function LangSwitcher() {
  const { t, i18n: i18nInst } = useTranslation();
  const current = i18nInst.resolvedLanguage ?? 'en';

  function switchLang(code: string) {
    i18n.changeLanguage(code);
    // Update <html lang=""> for assistive tech + CSS :lang() selector
    document.documentElement.lang = code;
  }

  return (
    <div className="lang-switcher" role="group" aria-label={t('lang.switcher_label')}>
      {LANGS.map(({ code, label }) => (
        <button
          key={code}
          className={'lang-btn' + (current === code ? ' lang-btn--active' : '')}
          onClick={() => switchLang(code)}
          aria-pressed={current === code}
          lang={code}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
