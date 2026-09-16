import React from 'react';

export function Icon({name, size=20}:{name:string,size?:number}) {
  const paths:Record<string,React.ReactNode> = {
    grid:<><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    scan:<><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 12h18"/><rect x="8" y="7" width="8" height="10" rx="2"/></>,
    file:<><path d="M14 3H5v18h14V8zM14 3v6h5M8 13h8m-8 4h5"/></>,
    model:<><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/></>,
    upload:<><path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/></>,
    arrow:<path d="M4 12h16m-6-6 6 6-6 6"/>,
    pin:<><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
    shield:<><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/></>,
    wave:<><path d="M2 8c4-6 6 6 10 0s6 6 10 0M2 16c4-6 6 6 10 0s6 6 10 0"/></>,
    clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    download:<><path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/></>,
    check:<path d="m5 12 4 4L19 6"/>,
    plus:<path d="M12 5v14M5 12h14"/>,
    help:<><circle cx="12" cy="12" r="9"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3m.08 4h.01"/></>,
    close:<path d="M18 6 6 18M6 6l12 12"/>,
    info:<><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/></>,
    compass:<><circle cx="12" cy="12" r="9"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></>,
    sparkle:<path d="m12 3 1.9 4.8L18.7 9.7l-4.8 1.9L12 16.4l-1.9-4.8L5.3 9.7l4.8-1.9L12 3z"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.scan}</svg>;
}

export function SonarMark(){return <svg className="sonar-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M7 28a18 18 0 0 1 26 0M12 23a11 11 0 0 1 16 0M17 18a4 4 0 0 1 6 0" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round"/><circle cx="20" cy="30" r="2.5" fill="currentColor"/></svg>}

export function SurveyGraphic(){return <svg className="survey-graphic" viewBox="0 0 480 260" fill="none" aria-hidden="true"><defs><pattern id="survey-grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0v30" stroke="#b5d8dc" strokeWidth=".5"/></pattern></defs><rect width="480" height="260" fill="url(#survey-grid)"/>{Array.from({length:12},(_,i)=><path key={i} d={`M${-80+i*11} 260C${-40+i*10} 80 ${150+i*9} ${330-i*15} ${220+i*12} ${140-i*9}S${440+i*10} ${160-i*15} 500 ${40-i*15}`} stroke="#4798a1" strokeOpacity={.15+i*.035} strokeWidth="1.3"/>)}<circle cx="276" cy="122" r="74" stroke="#156a79" strokeOpacity=".18"/><circle cx="276" cy="122" r="49" stroke="#156a79" strokeOpacity=".25"/><path d="M276 36v172M190 122h172" stroke="#156a79" strokeOpacity=".24"/><circle cx="276" cy="122" r="5" fill="#137e8c"/><path d="m280 117 46-39" stroke="#137e8c" strokeWidth="1.2"/><rect x="326" y="56" width="113" height="30" rx="5" fill="#fff"/><text x="338" y="75" fill="#276572" fontSize="10" fontFamily="monospace">SONAR WORKSPACE</text></svg>}

export const modelName=(id:string)=>({'ghost-pot':'GhostVision crab pots','sonarvision-sss':'SonarVision wrecks & debris','fls11-debris':'FLS debris specialist','sss-pipeline-v3':'Pipeline detector','sss-wreck-experimental':'Experimental SSS detector','uatd-fls':'UATD object detector','fls-debris-development':'FLS debris detector'}[id]||id);
export const modalityName=(id:string)=>({'SSS':'Side-scan sonar','SSS_LF':'Side-scan · low frequency','FLS_UATD':'Forward-looking · UATD','FLS_ARIS':'Forward-looking · ARIS'}[id]||id);
export const stateName=(s:string)=>({'completed_with_warnings':'Ready for review','processing':'Analyzing','validating':'Preparing','exporting':'Preparing results','queued':'Queued','failed':'Failed','cancelled':'Cancelled'}[s]||s);
export const coordinate=(value:number,axis:'lat'|'lon')=>`${Math.abs(value).toFixed(6)}° ${axis==='lat'?(value<0?'S':'N'):(value<0?'W':'E')}`;

export function Coverage({browser=false}:{browser?:boolean}){return <div className="coverage-strip" aria-label="Side-scan model coverage"><span className="coverage-title">SSS coverage</span><span><i className="dot"/>Pipelines <small>Development</small></span><span><i className="dot amber"/>Shipwrecks <small>Experimental</small></span><span><i className="dot amber"/>Crab pots <small>Low recall</small></span><span><i className="dot gray"/>Cylinders <small>Unvalidated</small></span><span><i className="dot gray"/>Entangled nets <small>Unavailable</small></span></div>}

export function Steps({current}:{current:number}){return <ol className="flow-steps">{['Upload sonar','Configure analysis','Inspect & locate','Export report'].map((s,i)=><li className={i===current?'current':i<current?'done':''} key={s}><span>{i<current?<Icon name="check" size={13}/>:i+1}</span>{s}</li>)}</ol>}
