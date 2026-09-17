import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en/common.json';
import hi from './locales/hi/common.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { common: en },
      hi: { common: hi },
    },
    defaultNS: 'common',
    fallbackLng: 'en',
    supportedLngs: ['en', 'hi'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      // Check localStorage first, then browser navigator.language
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'bluecho-lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
