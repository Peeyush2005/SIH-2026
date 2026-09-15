import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/team_credits_20260915/review-feedback';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function exportJSON(name){const pending=page.waitForEvent('download');await page.getByRole('button',{name:'JSON',exact:true}).click();const file=path.join(out,name);await(await pending).saveAs(file);return JSON.parse(await fs.readFile(file,'utf8'))}
try{
 await page.goto((process.env.BLUECHO_URL||'http://127.0.0.1:8013')+'/?demo=propeller');
 await page.locator('svg.sonar image').waitFor();
 const before=await exportJSON('before.json');assert.equal(before.detections.length,2);
 const [first,second]=before.detections;
 await page.getByLabel('Advance to next unreviewed contact').uncheck();
 await page.getByLabel('Review note',{exact:true}).fill('Needs additional acoustic context.');
 await page.getByRole('button',{name:'Uncertain',exact:true}).click();
 const uncertain=page.getByRole('dialog',{name:'Marked as uncertain'});await uncertain.waitFor();
 await uncertain.getByText(/decision and note are saved/).waitFor();
 assert.match(await uncertain.innerText(),/does not automatically retrain/);
 assert.ok(await page.evaluate(()=>document.activeElement.closest('dialog')));
 await page.setViewportSize({width:390,height:844});
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:path.join(out,'uncertain-mobile.png')});
 await uncertain.getByRole('button',{name:'Review next candidate',exact:true}).click();
 assert.equal(await page.locator('dialog').count(),0);
 await page.locator(`.selected-box [data-candidate="${second.candidate_id}"]`).waitFor();
 await page.getByRole('button',{name:'False alert',exact:true}).click();
 const rejected=page.getByRole('dialog',{name:'False alert recorded'});await rejected.waitFor();
 assert.match(await rejected.innerText(),/grey dashed outline/);
 await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(out,'false-alert-desktop.png')});
 await rejected.getByRole('button',{name:'Open report downloads',exact:true}).click();
 const after=await exportJSON('after.json');
 assert.equal(after.detections.find(d=>d.candidate_id===first.candidate_id).review_state,'uncertain');
 assert.equal(after.detections.find(d=>d.candidate_id===second.candidate_id).review_state,'false_alert');
 for(const original of before.detections){const current=after.detections.find(d=>d.candidate_id===original.candidate_id);assert.equal(current.model_score,original.model_score);assert.deepEqual(current.box_xyxy_pixels,original.box_xyxy_pixels);assert.ok(current.review_history.length)}
 await page.reload();await page.locator('svg.sonar image').waitFor();
 const restored=await exportJSON('restored.json');assert.equal(restored.review_revision,after.review_revision);
 const falseBox=page.locator(`[data-candidate="${second.candidate_id}"]`);assert.equal(await falseBox.getAttribute('stroke-dasharray'),'7 5');assert.equal(await falseBox.getAttribute('stroke'),'#a4b4bd');
 await page.getByRole('button',{name:'Uncertain',exact:true}).click();await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');assert.equal(await page.locator('dialog').count(),0);
 assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks:['Uncertain and false-alert confirmations explain consequences','Keyboard focus and Escape work','Next candidate and report actions work','Mobile dialog fits','Original scores/boxes remain unchanged','Review states and history survive reload','False-alert boxes have visible status and dashed outline'],errors},null,2));
 console.log('PASS review guidance, modal actions, immutable predictions and reload persistence');
}finally{await browser.close()}
