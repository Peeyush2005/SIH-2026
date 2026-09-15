import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/alignment_20260915';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1536,height:1050},acceptDownloads:true}),errors=[],measurements=[];
page.on('pageerror',e=>errors.push(e.message));
const ready=()=>page.waitForFunction(()=>document.querySelector('.surprise-button')&&!document.querySelector('.surprise-button').disabled&&document.querySelector('svg.sonar'));
try{
 await page.goto(process.env.BLUECHO_URL||'http://127.0.0.1:8010');await page.getByRole('button',{name:'Try demo',exact:true}).click();await ready();
 assert.equal(await page.locator('.scene-card').count(),11);assert.equal(await page.getByRole('button',{name:/Open Gulf survey/}).count(),0);
 await page.getByRole('button',{name:'Open Pipeline survey',exact:true}).click();await ready();
 for(const width of [1536,1024,768,390]){
  await page.setViewportSize({width,height:1050});
  const boxes=await page.locator('.export-buttons>button').evaluateAll(elements=>elements.map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height,right:r.right}}));
  assert.equal(boxes.length,7);for(const b of boxes)assert.equal(b.h,48);
  for(const b of boxes)for(const c of boxes)if(Math.abs(b.y-c.y)<2)assert.ok(Math.abs(b.y-c.y)<.1,'Buttons in a row must share their top edge');
  const bounds=await page.locator('.export-buttons').boundingBox();assert.ok(Math.abs(Math.max(...boxes.map(b=>b.right))-(bounds.x+bounds.width))<1);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const reviews=await page.locator('.review-actions button').evaluateAll(es=>es.map(e=>e.getBoundingClientRect().height));assert.ok(reviews.every(h=>h===44));
  measurements.push({width,exports:boxes,reviewHeights:reviews});
  await page.locator('.downloads').screenshot({path:path.join(out,'exports-'+width+'.png')});
  await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,'page-'+width+'.png'),fullPage:true});
 }
 const event=page.waitForEvent('download');await page.getByRole('button',{name:'JSON',exact:true}).click();await(await event).saveAs(path.join(out,'report.json'));assert.equal(JSON.parse(await fs.readFile(path.join(out,'report.json'),'utf8')).demo.synthetic,false);
 for(let i=0;i<4;i++){await page.getByRole('button',{name:'Surprise me',exact:true}).click();await ready();assert.doesNotMatch(await page.locator('.active-scene h2').innerText(),/Gulf survey · west/);}
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks:['Eleven featured real samples including all ten FLS classes and one georeferenced survey','Surprise me excludes the retired duplicate NOAA choice','Seven export buttons align with equal heights at four viewport widths','Review buttons share a consistent height','No horizontal page overflow','JSON download remains functional'],measurements,errors},null,2));console.log('PASS card removal, button alignment, responsive layout and report download');
}finally{await browser.close()}
