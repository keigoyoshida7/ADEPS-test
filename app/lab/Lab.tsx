'use client';
import { useCallback, useEffect, useState } from 'react';
import { AudioLines, BookOpen, CircleHelp, Route, Speaker, VolumeX } from 'lucide-react';
import { useLanguage, LocaleProvider, LanguageToggle } from './i18n';
import ADEPSWorkflow from './ADEPSWorkflow';
import ADEPSGlossary from './ADEPSGlossary';
import DiffusionStudio from './DiffusionStudio';
import ResearchInfo from './ResearchInfo';
import SpeakerDecoding from './SpeakerDecoding';

const pages = [
  { id: 'workflow', jp: 'ADEPSの流れ', en: 'ADEPS workflow', icon: Route },
  { id: 'diffusion', jp: '復元・比較', en: 'Reconstruct & compare', icon: AudioLines },
  { id: 'decoding', jp: 'スピーカーで再生', en: 'Speaker playback', icon: Speaker },
  { id: 'paper', jp: '論文と実装の範囲', en: 'Paper & implementation', icon: CircleHelp },
  { id: 'glossary', jp: '用語の解説', en: 'Glossary', icon: BookOpen },
] as const;
type Page = typeof pages[number]['id'];
const supportedPage = (value: string | null): Page => pages.find(page => page.id === value)?.id ?? 'workflow';
const pageFromURL = (): Page => typeof window === 'undefined' ? 'workflow' : supportedPage(new URLSearchParams(window.location.search).get('tab'));

export default function Lab() {
  return <LocaleProvider><LabContent /></LocaleProvider>;
}

function LabContent() {
  const language = useLanguage();
  const l = (jp: string, en: string) => language === 'jp' ? jp : en;
  const [tab, setTab] = useState<Page>(pageFromURL);
  useEffect(() => {
    // Old deep links open the workflow instead of an invisible legacy page.
    const url = new URL(window.location.href);
    if (url.searchParams.has('tab') && url.searchParams.get('tab') !== pageFromURL()) {
      url.searchParams.set('tab', 'workflow');
      url.hash = '';
      window.history.replaceState(null, '', url);
    }
    const restore = () => setTab(pageFromURL());
    window.addEventListener('popstate', restore);
    return () => window.removeEventListener('popstate', restore);
  }, []);
  const navigate = useCallback((requested: string) => {
    const next = supportedPage(requested);
    const url = new URL(window.location.href);
    if (url.searchParams.get('tab') !== next) {
      url.searchParams.set('tab', next);
      url.hash = '';
      window.history.pushState(null, '', url);
    }
    setTab(next);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, []);
  const current = pages.find(page => page.id === tab)!;

  return <div className="shell adeps-shell">
    <header className="adeps-navigation">
      <div className="brand"><span className="brand-symbol"><AudioLines size={25}/></span><div>ADEPS<span>test</span></div></div>
      <nav aria-label={l('ADEPSのページ', 'ADEPS pages')}>
        {pages.map(page => <button type="button" key={page.id} className={tab === page.id ? 'active' : ''}
          aria-current={tab === page.id ? 'page' : undefined} onClick={() => navigate(page.id)}>
          <page.icon size={17}/><span>{l(page.jp, page.en)}</span>
        </button>)}
      </nav>
      <LanguageToggle />
    </header>
    <main>
      <header className="topbar"><div><span className="eyebrow">ARRAY-AGNOSTIC AMBISONICS</span><h1>{l(current.jp, current.en)}</h1></div>
        <span className="badge">{l('独立実装・検証用', 'Independent research prototype')}</span>
      </header>
      <div hidden={tab !== 'workflow'}><ADEPSWorkflow language={language} active={tab === 'workflow'} onNavigate={navigate}/></div>
      <div hidden={tab !== 'diffusion'}><DiffusionStudio active={tab === 'diffusion'}/></div>
      <div hidden={tab !== 'decoding'}><SpeakerDecoding language={language} active={tab === 'decoding'} onNavigate={navigate}/></div>
      <div hidden={tab !== 'glossary'}><ADEPSGlossary language={language}/></div>
      {tab === 'paper' && <ResearchInfo onNavigate={navigate}/>}
      <footer><span className="adeps-footer-name">ADEPS-test · {l('データから復元までを確かめる', 'Trace the path from data to reconstruction')}</span>
        <span className="silent"><VolumeX size={13}/>{l('音は試聴ボタンで再生します', 'Audio starts only when you press play')}</span>
      </footer>
    </main>
  </div>;
}
