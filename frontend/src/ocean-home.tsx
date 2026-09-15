import React, {useEffect, useState} from 'react';
import {Icon} from './design';

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

export function InspectionWelcome({inspect,demo,busy}:{inspect:()=>void,demo:()=>void,busy:boolean}) {
 const {paused,setPaused,stopped}=useOceanMotion();
 return <section className={'inspection-welcome '+(stopped?'ocean-paused':'')}>
  <OceanBubbles/>
  <div className="welcome-copy"><p className="eyebrow">YOUR SONAR WORKSPACE</p><h1>A clearer view<br/><em>starts here.</em></h1><p>Bring your sonar imagery into focus. Inspect potential findings, review their context, and keep the evidence together.</p>
   <div className="welcome-actions"><button className="primary" onClick={inspect}>New inspection<Icon name="arrow" size={18}/></button><button className="welcome-demo" disabled={busy} onClick={demo}><Icon name="scan" size={18}/>{busy?'Opening…':'Try demo'}</button></div>
   <span className="welcome-hint">Explore the demo with real sonar imagery.</span>
  </div>
  <SonarSea paused={stopped}/>
  <button className="motion-control" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?'Play animation':'Pause animation'}</button>
 </section>;
}

function SonarSea({paused}:{paused:boolean}) {
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
  <span className="scope-caption"><i/>Illustrative sonar view</span>
 </div>;
}

export function OceanHero({inspect,demo,busy}:{inspect:()=>void,demo:()=>void,busy:boolean}) {
 const {paused,setPaused,stopped}=useOceanMotion();
 return <section className={'minimal-hero ocean-hero '+(stopped?'ocean-paused':'')}>
  <OceanBubbles/>
  <div className="ocean-hero-inner">
   <div className="ocean-copy"><p className="eyebrow"><span/>MARINE ANOMALY INTELLIGENCE</p>
    <h1>Look deeper.<br/><em>See what matters.</em></h1>
    <p>Find potential debris in sonar imagery. Review the evidence, understand its location, and turn a finding into an actionable report.</p>
    <div className="ocean-actions"><button className="primary" onClick={inspect}>Inspect sonar<Icon name="arrow" size={18}/></button><button className="demo-launch" disabled={busy} onClick={demo}><Icon name="scan" size={17}/>{busy?'Opening…':'Try demo'}</button><a href="#bluecho-features">Explore the features <span>↘</span></a></div>
    <p className="ocean-promise">From acoustic imagery to informed decisions.</p>
   </div>
   <SonarSea paused={stopped}/>
  </div>
  <div className="sea-horizon" aria-hidden="true"><svg className="ocean-moving wave-far" viewBox="0 0 1600 100" preserveAspectRatio="none"><path d="M0 40Q200 0 400 40T800 40T1200 40T1600 40V100H0Z"/></svg><svg className="ocean-moving wave-near" viewBox="0 0 1600 100" preserveAspectRatio="none"><path d="M0 45Q200 85 400 45T800 45T1200 45T1600 45V100H0Z"/></svg></div>
  <button className="motion-control" aria-pressed={paused} onClick={()=>setPaused(!paused)}>{paused?'Play animation':'Pause animation'}</button>
 </section>;
}

const features=[
 ['scan','Sonar specialists','Choose a detector suited to side-scan or forward-looking imagery. Inspect predictions in the original image.'],
 ['wave','Acoustic context','Examine quality flags, shadows and the surrounding seabed alongside each potential object.'],
 ['check','Human review','Retain, reject or correct a finding. Your notes and decisions stay linked to the original prediction.'],
 ['pin','Metadata-backed maps','Place findings on a map when matching coordinates are available. Missing locations stay clearly marked.'],
 ['model','Batch inspections','Queue several images and review each result separately, without mixing their sources or evidence.'],
 ['file','Portable reports','Take annotated imagery, review history and findings with you in PDF, JSON, CSV or GeoJSON.'],
];

export function OceanStory({hosted,browser}:{hosted:boolean,browser:boolean}) {
 return <>
  <section className="problem-solution" aria-label="The problem and our solution">
   <article><p className="section-kicker">BENEATH THE NOISE</p><h2>The problem</h2><p>On the seafloor, debris can look like rock. Shadows can look like objects. Reading sonar takes patience, context and careful judgement.</p></article>
   <article><p className="section-kicker">A CLEARER WAY THROUGH</p><h2>Our solution</h2><p>BluEcho brings detection, visual inspection and human review into one workspace—so every finding can become a report with evidence behind it.</p></article>
  </section>
  <section className="ocean-features" id="bluecho-features"><div className="ocean-section-heading"><p className="section-kicker">BUILT FOR THE WHOLE INSPECTION</p><h2>From first look<br/><span>to a shareable report.</span></h2></div>
   <div className="feature-lines">{features.map(([icon,title,copy])=><article key={title}><span className="feature-symbol"><Icon name={icon} size={23}/></span><div><h3>{title}</h3><p>{copy}</p></div></article>)}</div>
  </section>
  <section className="bluecho-difference"><div><p className="section-kicker">THE BLUECHO DIFFERENCE</p><h2>Your sonar.<br/>Your judgement.<br/><em>Your evidence.</em></h2><p>Our focus is the connection between a detection and a defensible decision. The source, model and review history travel with every finding.</p></div>
   <ul><li><Icon name="shield"/><div><h3>{hosted?'A choice of where to work':'Private by design'}</h3><p>{hosted?'Use this hosted workspace or run BluEcho locally when your imagery needs to stay on your device.':browser?'Your images are analyzed in your browser. The local application supports offline workflows after setup.':'Process imagery locally, with offline workflows available after dependencies and models are prepared.'}</p></div></li>
   <li><Icon name="check"/><div><h3>You stay in control</h3><p>Model suggestions start the inspection. Human review shapes the report, and original predictions remain traceable.</p></div></li>
   <li><Icon name="pin"/><div><h3>Evidence before certainty</h3><p>Clear model limitations, uncalibrated scores and source-backed locations. Experimental findings stay labelled.</p></div></li></ul>
  </section>
 </>;
}
