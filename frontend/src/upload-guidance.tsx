import React from 'react';
import samples from '../public/upload-samples.json';
import {modelName,modalityName} from './design';
import {REAL_DEMO_SAMPLES} from './demo-scene';
export function knownUpload(hash?:string){return samples.find(s=>s.sha256===hash)}
export async function recognizeUpload(file:File){if(file.size>32*1024**2||!/\.(png|jpe?g|bmp|pbm)$/i.test(file.name))return undefined;const bytes=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());return knownUpload(Array.from(new Uint8Array(bytes),v=>v.toString(16).padStart(2,'0')).join(''))}
export function UploadGuidance({source,model}:{source:Record<string,any>;model:string}){
 const hint=source.upload_hint||knownUpload(source.sha||source.info?.sha256),small=Math.min(source.info?.width||999,source.info?.height||999)<256;
 const original=hint&&REAL_DEMO_SAMPLES.find(s=>s.name===hint.name);
 return <div className="upload-guidance"><p><strong>{source.info.width&&`${source.info.width} × ${source.info.height} pixels`}</strong>{hint&&<> · Recognized presentation sample</>}</p>{hint?<p>{modalityName(hint.modality)} · <strong>{modelName(hint.model)}</strong>. Selected from this file’s exact content match. Starting inspection runs fresh inference.</p>:<p>Select the sensor and detector for this image. A new upload never inherits the previous image’s model.</p>}{hint&&model&&model!==hint.model&&<p role="alert" className="warning">This sample requires {modelName(hint.model)}. Select its matching model before starting.</p>}{small&&<p className="warning">Small image: fine details may be lost. Use the full-resolution source for your presentation. {original&&<a href={'/real-demo/'+original.id+'/original.png'} download={original.id+'.png'}>Download original PNG</a>}</p>}</div>;
}
export function EmptyDetectionHelp({model,width,height,reconfigure,demo,busy}:{model:string;width:number;height:number;reconfigure:()=>void;demo:()=>void;busy:boolean}){
 return <section className="empty-detection-help panel"><div><p className="eyebrow">ANALYSIS FINISHED · NO BOXES RETURNED</p><h2>Check the image and detector pairing</h2><p>This {width} × {height} image was processed with <strong>{modelName(model)}</strong>. The detector did not return a candidate above its configured threshold.</p><p>For fan-shaped water-tank images, choose Forward-looking · ARIS and FLS debris specialist. The pipeline detector only detects pipelines.</p></div><div className="empty-detection-actions"><button className="primary" disabled={busy} onClick={reconfigure}>Choose model & run again</button><button disabled={busy} onClick={demo}>Open a real demo example</button></div></section>;
}
