import {evidenceURL} from './browser-engine';
type Obj=Record<string,any>;
export async function inspectionPDF(result:Obj,job:Obj,items:Obj[],base:string,scope:string){
 const {jsPDF}=await import('jspdf');const doc=new jsPDF({compress:true});
 const clean=(v:any)=>String(v??'Unavailable').replace(/[\x00-\x08\x0b-\x1f]/g,'').replace(/[^\x20-\xff\n]/g,'?');
 let y=24;const page=()=>{doc.addPage();y=24};
 function text(value:any,size=10,bold=false){doc.setFont('helvetica',bold?'bold':'normal');doc.setFontSize(size);doc.setTextColor(24,53,72);const lines=doc.splitTextToSize(clean(value),174);for(const line of lines){if(y>268)page();doc.text(line,18,y);y+=size*.47}y+=3}
 function rule(){doc.setDrawColor(219,229,235);doc.line(18,y,192,y);y+=8}
 doc.setProperties({title:'BluEcho inspection brief',author:'BluEcho | SIH 2026',subject:'Operator review and sonar evidence'});
 text('BluEcho',27,true);text('SONAR INSPECTION BRIEF / SIH 2026',10,true);rule();
 text(job.filename,16,true);text(`Inspection ${job.id} | Window ${base.split('/').pop()} | Review revision ${result.review_revision}`);
 text(`Generated ${new Date().toISOString()} | Scope: ${scope==='all'?'All contacts':'Displayed contacts only'}`);
 text(`${items.length} included contacts | ${items.filter(d=>d.review_state!=='unreviewed').length} reviewed | ${items.filter(d=>d.coordinates).length} with metadata locations`);
 text(`Image: ${result.image_dimensions.width} x ${result.image_dimensions.height} pixels | ${result.quality.regions.length} quality regions flagged`);
 const response=await fetch(evidenceURL(base,'original.png'));if(!response.ok)throw Error('Could not load original report image');const bitmap=await createImageBitmap(await response.blob());
 const c=document.createElement('canvas');const scale=Math.min(1,1800/bitmap.width,1800/bitmap.height);c.width=Math.max(1,Math.round(bitmap.width*scale));c.height=Math.max(1,Math.round(bitmap.height*scale));const ctx=c.getContext('2d')!;ctx.drawImage(bitmap,0,0,c.width,c.height);bitmap.close();ctx.strokeStyle='#24ded8';ctx.lineWidth=2;ctx.font='bold 14px sans-serif';
 items.forEach((d,i)=>{const [x1,y1,x2,y2]=d.box_xyxy_pixels.map((n:number)=>n*scale);ctx.strokeRect(x1,y1,x2-x1,y2-y1);ctx.fillStyle='#092b39';ctx.fillRect(x1,Math.max(0,y1-19),28,19);ctx.fillStyle='#fff';ctx.fillText(String(i+1),x1+4,Math.max(14,y1-4))});
 const ih=Math.min(100,174*c.height/c.width),iw=ih*c.width/c.height;if(y+ih>265)page();doc.addImage(c.toDataURL('image/jpeg',.9),'JPEG',18,y,iw,ih);y+=ih+7;
 text('Original image with current reviewed boxes. Display brightness/contrast adjustments are excluded.',9);rule();
 text('Interpretation',12,true);text('Model scores are uncalibrated confidence, not probability of hazard. Metadata positions are estimates. Review decisions are not field verification. No navigation clearance or independent-site accuracy is established.',10);
 text(result.evidence_scope||'Consult the model card for evaluation scope.',9);
 if(!items.length)text('No contacts in this export scope. This does not establish that the source contains no hazards.');
 for(const [i,d] of items.entries()){
  if(y>195)page();rule();text(`${i+1}. ${d.class_name} | ${d.model_score.toFixed(1)}%`,14,true);
  text(`Evidence: ${d.candidate_type||'model_detection'} | ${d.evidence_status||result.evidence_scope||'See model card'}`,9);
  text(`Review: ${d.review_state} | Candidate: ${d.candidate_id}`);text(`Box xyxy (pixels): ${d.box_xyxy_pixels.map((n:number)=>n.toFixed(2)).join(', ')}`);
  text(d.coordinates?`Latitude ${d.coordinates[1].toFixed(6)}, longitude ${d.coordinates[0].toFixed(6)} | ${d.position_method||'Metadata estimate'}`:'Geographic location unavailable');
  text(`Model: ${d.model_id} | ${d.model_version||'See evidence JSON'}`);text(`Weight SHA-256: ${d.model_sha256}`,8);
  const history=d.review_history||[];if(history.length){text('Operator audit trail',10,true);for(const e of history)text(`${e.timestamp||e.created||''} | ${e.reviewer||'Unnamed reviewer'} | ${e.action}: ${e.note||'(no note)'}`,9)}else text('No operator review recorded.',9);
 }
 rule();text('Source provenance',12,true);text(`SHA-256: ${result.source_sha256}`,9);text('Keep the JSON and evidence ZIP alongside this brief for complete machine-readable provenance, review history and original Unicode text. The PDF standard font replaces unsupported characters with ?.',9);
 text('Prepared by BluEcho for Smart India Hackathon 2026. Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, Aditya Banerjee.',9);
 const pages=doc.getNumberOfPages();for(let p=1;p<=pages;p++){doc.setPage(p);doc.setFontSize(8);doc.setTextColor(104,124,135);doc.text('BluEcho / Operator decision support',18,284);doc.text(`${p} / ${pages}`,192,284,{align:'right'})}
 return doc.output('blob');
}
