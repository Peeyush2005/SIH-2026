/** Fresh ONNX inference on every supplied presentation file; never uses /demo. */
import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const pack=process.env.BLUECHO_PRESENTATION||'E:/Hackathon/BluEcho_Live_Presentation';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/upload_reliability_20260915/live';await fs.mkdir(out,{recursive:true});
const manifest=JSON.parse(await fs.readFile(path.join(pack,'manifest.json'),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'}),page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true}),runs=[],errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function upload(file){await page.getByRole('button',{name:'New inspection',exact:true}).click();await page.getByLabel('Sonar source',{exact:true}).setInputFiles(file);await page.locator('.source-card').waitFor()}
async function exported(file){await page.getByRole('button',{name:'View inspection report',exact:true}).first().click();const pending=page.waitForEvent('download');await page.getByRole('button',{name:'JSON',exact:true}).click();await(await pending).saveAs(file);return JSON.parse(await fs.readFile(file,'utf8'))}
try{
 await page.goto(process.env.BLUECHO_URL||'http://127.0.0.1:8014');await page.locator('.minimal-hero').waitFor();
 for(const entry of manifest.images){
  await upload(path.join(pack,entry.file));assert.equal(await page.getByLabel('Confirm source modality').inputValue(),entry.modality);assert.equal(await page.getByLabel('Model route').inputValue(),entry.model);
  if(runs.length===0){await page.getByLabel('Confirm source modality').selectOption('FLS_ARIS');await page.getByLabel('Model route').selectOption('fls11-debris');assert.ok(await page.getByRole('button',{name:'Start inspection',exact:true}).isDisabled());await page.getByLabel('Confirm source modality').selectOption(entry.modality);await page.getByLabel('Model route').selectOption(entry.model)}
  await page.getByRole('button',{name:'Start inspection',exact:true}).click();await page.locator('.candidates h2').waitFor({timeout:180000});
  const boxes=await page.locator('svg.sonar [data-candidate]').count();assert.ok(boxes>0,'No visible boxes for '+entry.file);
  await page.locator('svg.sonar').screenshot({path:path.join(out,entry.file.replaceAll('/','_')+'.png')});
  const r=await exported(path.join(out,entry.file.replaceAll('/','_')+'.json'));
  assert.equal(r.source_sha256,entry.sha256);assert.equal(r.saved_example,false);assert.ok(!r.demo);assert.match(r.runtime,/onnxruntime-web/);assert.equal(r.modality,entry.modality);
  const predictions=[...r.detections,...r.unvalidated_proposals];assert.equal(predictions.length,boxes);
  for(const d of predictions){assert.equal(d.model_id,entry.model);assert.ok(d.model_score>0);assert.ok(d.box_xyxy_pixels.every(Number.isFinite));const[x,y,z,t]=d.box_xyxy_pixels;assert.ok(x>=0&&y>=0&&z>x&&t>y&&z<=entry.width&&t<=entry.height)}
  runs.push({...entry,boxes,classes:predictions.map(d=>d.class_name),scores:predictions.map(d=>d.model_score),runtime:r.runtime});console.log('PASS',entry.file,JSON.stringify(runs.at(-1).classes));
 }
 // Unknown uploads must clear the old specialist, even when the filename sounds familiar.
 await page.getByRole('button',{name:'New inspection',exact:true}).click();await page.getByLabel('Sonar source',{exact:true}).setInputFiles({name:'propeller.png',mimeType:'image/png',buffer:Buffer.from(await page.evaluate(async()=>{const c=document.createElement('canvas');c.width=310;c.height=320;const b=await new Promise(r=>c.toBlob(r));return Array.from(new Uint8Array(await b.arrayBuffer()))}))});await page.locator('.source-card').waitFor();assert.equal(await page.getByLabel('Model route').inputValue(),'');assert.equal(await page.getByLabel('Confirm source modality').inputValue(),'');assert.ok(await page.getByRole('button',{name:'Start inspection',exact:true}).isDisabled());
 // Real negative control remains empty and offers recovery rather than manufactured boxes.
 await upload('E:/Hackathon/BluEcho_Live_Demo_Images/SSS_Pipeline/pipeline_empty.png');await page.getByRole('button',{name:'Start inspection',exact:true}).click();await page.locator('.candidates h2').waitFor({timeout:180000});assert.equal(await page.locator('svg.sonar [data-candidate]').count(),0);await page.getByRole('button',{name:'Choose model & run again',exact:true}).click();await page.locator('.source-card').waitFor();assert.equal(await page.getByLabel('Model route').inputValue(),'sss-pipeline-v3');
 assert.deepEqual(errors,[]);const receipt={status:'PASS',runtime:'Fresh browser WASM inference, fixed configured thresholds',runs,checks:['Every presentation PNG/JPG has real visible bounded predictions','Exact source hashes and image bounds checked','Matching detector selected for known samples','Wrong detector blocked','Unknown upload clears prior route','Negative control stays empty with recovery actions'],errors};await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2));await fs.writeFile(path.join(pack,'LIVE_RESULTS.json'),JSON.stringify(receipt,null,2));console.log('PASS all presentation images and routing safeguards');
}catch(e){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});await fs.writeFile(path.join(out,'partial.json'),JSON.stringify({runs,error:e.stack},null,2));throw e}finally{await browser.close()}

