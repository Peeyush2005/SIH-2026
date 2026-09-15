import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/team_credits_20260915/review-report-flow';
await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function report(){await page.getByRole('button',{name:'View inspection report',exact:true}).first().click();await page.getByRole('article',{name:'Inspection report'}).waitFor();assert.equal(await page.locator('.workspace').count(),0)}
async function exportJSON(name){const pending=page.waitForEvent('download');await page.getByRole('button',{name:'JSON',exact:true}).click();const file=path.join(out,name);await(await pending).saveAs(file);return JSON.parse(await fs.readFile(file,'utf8'))}
async function inspect(){await page.getByRole('button',{name:'Return to inspection',exact:true}).click();await page.locator('svg.sonar image').waitFor()}
async function unlock(){await page.getByRole('button',{name:'Edit saved review',exact:true}).click()}
async function saved(title){const dialog=page.getByRole('dialog',{name:title});await dialog.waitFor();assert.ok(await page.evaluate(()=>document.querySelector('dialog').matches(':modal')));assert.equal(await page.locator('.review-actions button:disabled').count(),4);await dialog.getByRole('button',{name:'Close review confirmation'}).click();assert.equal(await page.locator('.review-actions button:disabled').count(),4)}
try{
 await page.goto((process.env.BLUECHO_URL||'http://127.0.0.1:8013')+'/?demo=propeller');await page.locator('svg.sonar image').waitFor();
 await report();const before=await exportJSON('before.json');await inspect();await page.getByLabel('Advance to next unreviewed contact').uncheck();
 // Two synchronous click events must cause only one save. Record the immediate saving modal.
 await page.evaluate(()=>{window.__savingSeen=false;new MutationObserver(()=>{if(document.querySelector('dialog[aria-busy="true"]'))window.__savingSeen=true}).observe(document.body,{childList:true,subtree:true});const b=[...document.querySelectorAll('.review-actions button')].find(e=>e.textContent==='Retain candidate');b.click();b.click()});
 await saved('Candidate retained');assert.ok(await page.evaluate(()=>window.__savingSeen));
 await report();let current=await exportJSON('retained.json');assert.equal(current.review_revision,before.review_revision+1);await page.getByRole('heading',{name:'Findings & next steps'}).waitFor();await inspect();
 await unlock();await page.getByLabel('Review note',{exact:true}).fill('Shadow requires a second review.');await page.getByRole('button',{name:'Uncertain',exact:true}).click();await saved('Marked as uncertain');
 await unlock();await page.getByRole('button',{name:'False alert',exact:true}).click();await saved('False alert recorded');
 await unlock();await page.getByLabel('Review note',{exact:true}).fill('Rejected after checking the source context.');await page.getByRole('button',{name:'Save note',exact:true}).click();await saved('Note saved');
 await report();current=await exportJSON('noted.json');const target=current.detections[0];assert.equal(target.review_state,'false_alert');assert.equal(target.review_history.length,4);assert.equal(target.model_score,before.detections[0].model_score);assert.deepEqual(target.box_xyxy_pixels,before.detections[0].box_xyxy_pixels);await page.getByText('Rejected after checking the source context.',{exact:true}).waitFor();
 await page.screenshot({path:path.join(out,'report-desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'report-mobile.png'),fullPage:true});await inspect();
 await unlock();await page.getByText('Correct label or box',{exact:true}).click();await page.getByLabel('Original pixels: x1, y1, x2, y2').fill('-1, 0, 0, 0');await page.getByRole('button',{name:'Save correction',exact:true}).click();await page.getByRole('dialog',{name:'Could not finish saving'}).waitFor();await page.getByRole('button',{name:'Return to review',exact:true}).click();
 await page.getByLabel('Original pixels: x1, y1, x2, y2').fill(before.detections[0].box_xyxy_pixels.join(', '));await page.getByRole('button',{name:'Save correction',exact:true}).click();await saved('Correction saved');
 await page.reload();await page.locator('svg.sonar image').waitFor();assert.equal(await page.locator('.review-actions button:disabled').count(),4);
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Reports',exact:true}).click();await page.locator('.inspection-row').first().click();await page.getByRole('article',{name:'Inspection report'}).waitFor();assert.equal(await page.locator('.review-actions').count(),0);assert.equal(await page.locator('.scene-gallery').count(),0);
 current=await exportJSON('final.json');assert.equal(current.review_revision,before.review_revision+5);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks:['Immediate modal and duplicate-click prevention','All five review actions have confirmation','Saved review lock with explicit edit','Invalid correction recovers without a new revision','Separate report from library and popup','Notes, decisions and coordinates faithfully reported','Reload preserves review lock','Desktop and mobile report layout'],errors},null,2));console.log('PASS review locks, all action modals, error recovery and distinct reports');
}catch(e){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e}finally{await browser.close()}
