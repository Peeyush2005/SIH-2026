import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=process.env.BLUECHO_PRESENTATION||'E:/Hackathon/BluEcho_Live_Presentation';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/fls_route_20260915';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'}),page=await browser.newPage({acceptDownloads:true}),errors=[];page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(process.env.BLUECHO_URL||'http://127.0.0.1:8014');await page.locator('.minimal-hero').waitFor();
 const files=(await fs.readdir(path.join(root,'FLS_Debris'))).filter(f=>/\.(jpg|png)$/.test(f));
 for(const file of files){await page.getByLabel('Sonar source',{exact:true}).setInputFiles(path.join(root,'FLS_Debris',file));await page.locator('.source-card').waitFor();await page.getByLabel('Confirm source modality').selectOption('FLS_ARIS');await page.waitForFunction(()=>document.querySelector('#model-route-status')?.textContent.includes('FLS debris specialist is ready'));assert.equal(await page.getByLabel('Model route').inputValue(),'fls11-debris');assert.ok(await page.getByRole('button',{name:'Start inspection',exact:true}).isEnabled())}
 await page.getByLabel('Confirm source modality').selectOption('SSS_LF');assert.ok(await page.getByRole('button',{name:'Start inspection',exact:true}).isDisabled());await page.getByLabel('Confirm source modality').selectOption('FLS_ARIS');await page.waitForFunction(()=>document.querySelector('#model-route-status')?.textContent.includes('FLS debris specialist is ready'));assert.equal(await page.getByLabel('Model route').inputValue(),'fls11-debris');
 await page.getByLabel('Sonar source',{exact:true}).setInputFiles(path.join(root,'FLS_Debris/propeller.jpg'));await page.locator('.source-card').waitFor();await page.getByRole('button',{name:'Start inspection',exact:true}).click();await page.locator('.candidates h2').waitFor({timeout:180000});assert.equal(await page.locator('svg.sonar [data-candidate]').count(),2);
 await page.getByRole('button',{name:'View inspection report',exact:true}).first().click();const pending=page.waitForEvent('download');await page.getByRole('button',{name:'JSON',exact:true}).click();await(await pending).saveAs(path.join(out,'live.json'));const r=JSON.parse(await fs.readFile(path.join(out,'live.json'),'utf8'));assert.ok(r.detections.some(d=>d.class_name==='propeller'));assert.ok(r.detections.every(d=>d.model_id==='fls11-debris'));assert.ok(!r.demo);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',files,checks:['All FLS PNG/JPG model choices survive reselecting FLS','Switching back to FLS restores its detector','Mismatched sensor remains blocked','Fresh propeller inference produces two boxes'],errors},null,2));console.log('PASS',files.length,'FLS uploads, sensor reselection, and real propeller inference');
}finally{await browser.close()}
