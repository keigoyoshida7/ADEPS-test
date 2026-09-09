'use client';
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import english from './en.json';
import backendEnglish from './backend-en.json';
export type Language = 'jp' | 'en';
type Message = string | { key: string; values?: unknown[] };
type Translator = (
  message: Message | null | undefined,
  values?: unknown[],
) => string;
const dictionary: Record<string, string> = english;
const normalize = (value: string) => value.replace(/\s+/g, ' ').trim();
const escapePattern = (value: string) =>
  value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// Only known server messages use pattern matching. Imported names and result data remain intact.
const serverPatterns = Object.entries(backendEnglish)
  .filter(([key]) => key.includes('${'))
  .map(([key, translation]) => ({
    pattern: new RegExp(
      '^' +
        key
          .split(/\$\{[^}]*\}/)
          .map(escapePattern)
          .join('([\\s\\S]*?)') +
        '$',
    ),
    names: [...key.matchAll(/\$\{([^}]*)\}/g)].map((match) => match[1]),
    translation,
  }));
function translateSource(source: string, depth = 0): string {
  const known = dictionary[normalize(source)];
  if (known !== undefined) return known;
  if (depth > 3) return source;
  for (const { pattern, names, translation } of serverPatterns) {
    const match = pattern.exec(source);
    if (match)
      return translation.replace(/\$\{([^}]*)\}/g, (_, name: string) =>
        translateSource(match[names.indexOf(name) + 1] || '', depth + 1),
      );
  }
  return source;
}
const LanguageContext = createContext<{
  language: Language;
  setLanguage: (language: Language) => void;
  t: Translator;
} | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('jp');
  useEffect(() => {
    try {
      if (localStorage.getItem('adeps-test-language') === 'en')
        setLanguage('en');
    } catch {
      /* Storage may be unavailable. */
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = language === 'jp' ? 'ja' : 'en';
    document.title =
      language === 'jp'
        ? 'ADEPS-test · 実験と検証'
        : 'ADEPS-test · Experiments & Evidence';
  }, [language]);
  const chooseLanguage = useCallback((next: Language) => {
    setLanguage(next);
    try {
      localStorage.setItem('adeps-test-language', next);
    } catch {
      /* The current session still switches. */
    }
  }, []);
  const t = useCallback<Translator>(
    (message, values) => {
      const source =
        typeof message === 'object' && message ? message.key : message || '';
      const params =
        typeof message === 'object' && message ? message.values : values;
      const translated = language === 'en' ? translateSource(source) : source;
      let index = 0;
      return params
        ? translated.replace(/\$\{[^}]*\}/g, () =>
            String(params[index++] ?? ''),
          )
        : translated;
    },
    [language],
  );
  return (
    <LanguageContext.Provider
      value={{ language, setLanguage: chooseLanguage, t }}
    >
      {children}
    </LanguageContext.Provider>
  );
}
export function useT() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('Translation requires LocaleProvider');
  return context.t;
}
export function LanguageToggle() {
  const context = useContext(LanguageContext)!;
  return (
    <div
      className="language-toggle"
      role="group"
      aria-label={context.language === 'jp' ? '表示言語' : 'Display language'}
    >
      <button
        type="button"
        lang="ja"
        aria-label="日本語"
        aria-pressed={context.language === 'jp'}
        onClick={() => context.setLanguage('jp')}
      >
        JP
      </button>
      <span aria-hidden="true">/</span>
      <button
        type="button"
        lang="en"
        aria-label="English"
        aria-pressed={context.language === 'en'}
        onClick={() => context.setLanguage('en')}
      >
        EN
      </button>
    </div>
  );
}
