import React,{useEffect,useRef} from 'react';
import {Icon} from './design';

export type ReviewFeedbackValue={action:'uncertain'|'false_alert';label:string;candidateId:string;nextId?:string;hasNote:boolean};

export function ReviewFeedback({value,close,view,next,reports}:{value:ReviewFeedbackValue;close:()=>void;view:()=>void;next:()=>void;reports:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);
 const uncertain=value.action==='uncertain';
 useEffect(()=>{const element=dialog.current!;const previous=document.activeElement;element.showModal();return()=>{element.close();if(previous instanceof HTMLElement&&previous.isConnected)previous.focus()}},[]);
 return <dialog ref={dialog} className="review-feedback" aria-labelledby="review-feedback-title" aria-describedby="review-feedback-description" onCancel={event=>{event.preventDefault();close()}}>
  <button className="review-feedback-close" onClick={close} aria-label="Close review confirmation">×</button>
  <span className={'review-feedback-symbol '+(uncertain?'is-uncertain':'')}><Icon name={uncertain?'scan':'check'} size={25}/></span>
  <p className="eyebrow">REVIEW SAVED</p>
  <h2 id="review-feedback-title">{uncertain?'Marked as uncertain':'False alert recorded'}</h2>
  <p id="review-feedback-description"><strong>{value.label}</strong>{value.hasNote?' — your decision and note are saved.':' — your decision is saved.'}</p>
  <div className="review-feedback-explanation">
   <h3>What happens now</h3>
   <p>{uncertain?'The finding stays marked Uncertain in this inspection and its reports. Review more context or ask a qualified reviewer before treating it as confirmed.':'The viewer marks this box with a grey dashed outline and a False alert label. The finding stays in the evidence record and exports with your decision.'}</p>
   <p>Your original detection and model score are preserved. This review does not automatically retrain the model, send an alert or request another scan.</p>
  </div>
  <div className="review-feedback-actions">
   <button className="primary" autoFocus onClick={value.nextId?next:view}>{value.nextId?'Review next candidate':'View saved decision'}<Icon name="arrow" size={17}/></button>
   <button onClick={reports}>Open report downloads</button>
  </div>
  {value.nextId&&<button className="review-feedback-return" onClick={view}>Return to this finding</button>}
 </dialog>;
}
