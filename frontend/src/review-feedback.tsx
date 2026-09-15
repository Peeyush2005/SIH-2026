import React,{useEffect,useRef} from 'react';
import {Icon} from './design';

export type ReviewFeedbackValue={action:string;label:string;candidateId:string;nextId?:string;hasNote:boolean;status:'saving'|'saved'|'error';error?:string};

export function ReviewFeedback({value,close,view,next,reports}:{value:ReviewFeedbackValue;close:()=>void;view:()=>void;next:()=>void;reports:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);
 const uncertain=value.action==='uncertain';
 const saving=value.status==='saving',failed=value.status==='error';
 const titles:Record<string,string>={retain:'Candidate retained',uncertain:'Marked as uncertain',false_alert:'False alert recorded',note:'Note saved',corrected:'Correction saved'};
 const explanations:Record<string,string>={retain:'The finding stays retained for follow-up in the report. Retaining it does not confirm its identity in the field.',uncertain:'The finding stays marked Uncertain in this inspection and its reports. Review more context or ask a qualified reviewer before treating it as confirmed.',false_alert:'The viewer marks this box with a grey dashed outline and a False alert label. The finding stays in the evidence record and exports with your decision.',note:'Your note is added to the review history. The current decision stays unchanged; an unreviewed finding still needs a decision.',corrected:'The report includes your corrected label or box, with the original prediction and previous edits preserved in the history.'};
 useEffect(()=>{const element=dialog.current!;const previous=document.activeElement;element.showModal();return()=>{element.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus()}},[]);
 return <dialog ref={dialog} className="review-feedback" aria-busy={saving} aria-labelledby="review-feedback-title" aria-describedby="review-feedback-description" onCancel={event=>{event.preventDefault();if(!saving)close()}}>
  <button className="review-feedback-close" disabled={saving} onClick={close} aria-label="Close review confirmation">×</button>
  <span className={'review-feedback-symbol '+(uncertain?'is-uncertain':'')}><Icon name={uncertain?'scan':'check'} size={25}/></span>
  <p className="eyebrow">{saving?'SAVING REVIEW':failed?'REVIEW NEEDS ATTENTION':'REVIEW SAVED'}</p>
  <h2 id="review-feedback-title">{saving?'Saving your review…':failed?'Could not finish saving':titles[value.action]}</h2>
  <p id="review-feedback-description" role="status"><strong>{value.label}</strong>{saving?' — please wait. Other controls are locked.':failed?' — '+value.error:value.action==='note'?' — your note is saved.':value.hasNote?' — your decision and note are saved.':' — your decision is saved.'}</p>
  {!saving&&!failed&&<>
  <div className="review-feedback-explanation">
   <h3>What happens now</h3>
   <p>{explanations[value.action]}</p>
   <p>The review buttons are locked for this finding. Choose Edit saved review if you need to make another change.</p>
   <p>Your original detection and model score are preserved. This review does not automatically retrain the model, send an alert or request another scan.</p>
  </div>
  <div className="review-feedback-actions">
   <button className="primary" autoFocus onClick={value.nextId?next:view}>{value.nextId?'Review next candidate':'View saved decision'}<Icon name="arrow" size={17}/></button>
   <button onClick={reports}>View inspection report</button>
  </div>
  {value.nextId&&<button className="review-feedback-return" onClick={view}>Return to this finding</button>}</>}
  {failed&&<button className="primary" onClick={close}>Return to review</button>}
 </dialog>;
}
