import React, {useEffect, useState} from 'react';
import {Icon} from './design';
import { useTranslation } from 'react-i18next';

function useOceanMotion() {
 const [paused,setPaused]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches);
 const [hidden,setHidden]=useState(document.hidden);
 useEffect(()=>{const update=()=>setHidden(document.hidden);document.addEventListener('visibilitychange',update);return()=>document.removeEventListener('visibilitychange',update)},[]);
 return {paused,setPaused,stopped:paused||hidden};
}

function OceanBubbles() {
 const bubbles=[[3,12,23,-7],[8,6,18,-13],[14,18,28,-20],[29,7,25,-4],[43,10,30,-17],[58,6,21,-8],[72,15,26,-16],[82,8,20,-3],[89,22,31,-23],[95,11,24,-12],[98,5,19,-5]];
 return <div className="ocean-bubbles" aria-hidden="true">{bubbles.map(([left,size,duration,delay],i)=><span key={i} className="ocean-bubble ocean-moving" style={{left:left+'%',width:size,height:size,animationDuration:duration+'s',animationDelay:delay+'s'}}/>)}</div>;
}

export function InspectionWelcome({inspect,demo,busy,openGuide}:{inspect:()=>void,demo:()=>void,busy:boolean,openGuide?:()=>void}) {
 const {paused,setPaused,stopped}=useOceanMotion();
 const {t} = useTranslation();
 return <section className={'inspection-welcome '+(stopped?'ocean-paused':'')}>
  <OceanBubbles/>
  <div className="welcome-copy"><p className="eyebrow">{t('welcome.eyebrow')}</p><h1>{t('welcome.headline_1')}<br/><em>{t('welcome.headline_em')}</em></h1><p>{t('welcome.body')}</p>
   <div className="welcome-actions"><button className="primary" onClick={inspect}>{t('welcome.cta_new')}<Icon name="arrow" size={18}/></button><button className="welcome-demo" disabled={busy} onClick={demo}><Icon name="scan" size={18}/>{busy?t('welcome.cta_demo_loading'):t('welcome.cta_demo')}</button>{openGuide&&<button className="welcome-guide-btn" onClick={openGuide}><Icon name="help" size={17}/>{t('welcome.cta_how')}</button>}</div>
   <span className="welcome-hint">{t('welcome.hint')}</span>
  </div>
  <SonarSea paused={stopped}/>
  <button className="motion-control" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?t('hero.play_animation'):t('hero.pause_animation')}</button>
 </section>;
}

function SonarSea({paused}:{paused:boolean}) {
 const {t} = useTranslation();
 return <div className={'sonar-sea '+(paused?'ocean-paused':'')} aria-hidden="true">
  <div className="sea-haze"/>
  <svg className="sea-contours" viewBox="0 0 660 480" fill="none">
   {Array.from({length:17},(_,i)=><path key={i} d={`M-80 ${240+i*15} C 70 ${100+i*8}, 170 ${390+i*5}, 310 ${275+i*7} S 500 ${70+i*14}, 750 ${170+i*10}`} />)}
  </svg>
  <div className="sonar-instrument">
   <div className="scope-ring scope-ring-outer"/><div className="scope-ring scope-ring-middle"/>
   <div className="scope-face">
    <div className="scope-grid"/><div className="scope-sweep ocean-moving"/>
    <svg className="scope-terrain" viewBox="0 0 400 400" fill="none">
     {Array.from({length:12},(_,i)=><path key={i} d={`M-20 ${175+i*19} C 90 ${80+i*17}, 200 ${340-i*3}, 420 ${110+i*18}`} />)}
     <path className="scope-pipe" d="M112 270 161 213 219 187 273 135"/>
     <path className="scope-bracket" d="M253 122h30v31m-17 112h30v31M98 255v30h30"/>
    </svg>
    <i className="scope-echo echo-a ocean-moving"/><i className="scope-echo echo-b ocean-moving"/>
    <i className="scope-origin"/>
   </div>
   <span className="scope-axis axis-n"/><span className="scope-axis axis-e"/><span className="scope-axis axis-s"/><span className="scope-axis axis-w"/>
  </div>
  <span className="scope-caption"><i/>{t('hero.caption')}</span>
 </div>;
}

export function OceanHero({inspect,demo,busy,openGuide}:{inspect:()=>void,demo:()=>void,busy:boolean,openGuide?:()=>void}) {
 const {paused,setPaused,stopped}=useOceanMotion();
 const {t} = useTranslation();
 return <section className={'minimal-hero ocean-hero '+(stopped?'ocean-paused':'')}>
  <OceanBubbles/>
  <div className="ocean-hero-inner">
   <div className="ocean-copy"><p className="eyebrow"><span/>{t('hero.eyebrow')}</p>
    <h1>{t('hero.headline_1')}<br/><em>{t('hero.headline_em')}</em></h1>
    <p>{t('hero.body')}</p>
    <div className="ocean-actions">
      <button className="primary" onClick={inspect}>{t('hero.cta_inspect')}<Icon name="arrow" size={18}/></button>
      <button className="demo-launch" disabled={busy} onClick={demo}><Icon name="scan" size={17}/>{busy?t('hero.cta_demo_loading'):t('hero.cta_demo')}</button>
      {openGuide&&<button className="hero-guide-btn" onClick={openGuide}><Icon name="help" size={16}/>{t('hero.cta_how')}</button>}
      <a href="#bluecho-features">{t('hero.explore')} <span>↘</span></a>
    </div>
    <p className="ocean-promise">{t('hero.promise')}</p>
   </div>
   <SonarSea paused={stopped}/>
  </div>
  <div className="sea-horizon" aria-hidden="true"><svg className="ocean-moving wave-far" viewBox="0 0 1600 100" preserveAspectRatio="none"><path d="M0 40Q200 0 400 40T800 40T1200 40T1600 40V100H0Z"/></svg><svg className="ocean-moving wave-near" viewBox="0 0 1600 100" preserveAspectRatio="none"><path d="M0 45Q200 85 400 45T800 45T1200 45T1600 45V100H0Z"/></svg></div>
  <button className="motion-control" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?t('hero.play_animation'):t('hero.pause_animation')}</button>
 </section>;
}

export function OceanStory({hosted,browser}:{hosted:boolean,browser:boolean}) {
 const {t} = useTranslation();
 const features:[string,string,string][]=[
  ['scan', t('features.specialists_title'), t('features.specialists_body')],
  ['wave', t('features.acoustic_title'),    t('features.acoustic_body')],
  ['check',t('features.review_title'),      t('features.review_body')],
  ['pin',  t('features.maps_title'),        t('features.maps_body')],
  ['model',t('features.batch_title'),       t('features.batch_body')],
  ['file', t('features.reports_title'),     t('features.reports_body')],
 ];
 return <>
  <section className="problem-solution" aria-label={t('story.problem_title')}>
   <article><p className="section-kicker">{t('story.problem_kicker')}</p><h2>{t('story.problem_title')}</h2><p>{t('story.problem_body')}</p></article>
   <article><p className="section-kicker">{t('story.solution_kicker')}</p><h2>{t('story.solution_title')}</h2><p>{t('story.solution_body')}</p></article>
  </section>
  <section className="ocean-features" id="bluecho-features"><div className="ocean-section-heading"><p className="section-kicker">{t('story.features_kicker')}</p><h2>{t('story.features_headline_1')}<br/><span>{t('story.features_headline_em')}</span></h2></div>
   <div className="feature-lines">{features.map(([icon,title,copy])=><article key={title}><span className="feature-symbol"><Icon name={icon} size={23}/></span><div><h3>{title}</h3><p>{copy}</p></div></article>)}</div>
  </section>
  <section className="bluecho-difference"><div><p className="section-kicker">{t('story.diff_kicker')}</p><h2>{t('story.diff_headline_1')}<br/>{t('story.diff_headline_2')}<br/><em>{t('story.diff_headline_em')}</em></h2><p>{t('story.diff_body')}</p></div>
   <ul><li><Icon name="shield"/><div><h3>{hosted?t('story.diff_private_title_hosted'):t('story.diff_private_title_local')}</h3><p>{hosted?t('story.diff_private_body_hosted'):browser?t('story.diff_private_body_browser'):t('story.diff_private_body_local')}</p></div></li>
   <li><Icon name="check"/><div><h3>{t('story.diff_control_title')}</h3><p>{t('story.diff_control_body')}</p></div></li>
   <li><Icon name="pin"/><div><h3>{t('story.diff_evidence_title')}</h3><p>{t('story.diff_evidence_body')}</p></div></li></ul>
  </section>
 </>;
}
