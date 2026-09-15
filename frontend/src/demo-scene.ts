/** Procedural UI fixtures, never model predictions or real survey observations. */
export const DEMO_SCENARIOS=[
 {id:'pipeline',name:'Pipeline corridor',description:'Follow an elongated return and review nearby contacts.'},
 {id:'objects',name:'Scattered returns',description:'Inspect object-like returns and their acoustic shadows.'},
 {id:'coverage',name:'Interrupted coverage',description:'Explore dark coverage bands and request another scan.'},
];
export function demoScene(seed:number,scenario:string){
 let state=seed>>>0;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296};
 const spec=DEMO_SCENARIOS.find(x=>x.id===scenario)||DEMO_SCENARIOS[seed%DEMO_SCENARIOS.length];
 const width=1400,height=680,c=document.createElement('canvas');c.width=width;c.height=height;const ctx=c.getContext('2d')!;
 const pixels=ctx.createImageData(width,height);
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const range=Math.abs(x-width/2)/(width/2),water=range<.045;
  const ridges=Math.sin(y*.025+Math.sin(x*.009)*2)*9+Math.sin(x*.019+y*.016)*5;
  const noise=(random()+random()+random()-1.5)*53;
  const value=Math.max(0,Math.min(255,water?7+random()*7:51+range*38+ridges+noise));
  const i=(y*width+x)*4;pixels.data.set([value*.91,value,value*1.02,255],i);
 }
 ctx.putImageData(pixels,0,0);
 const contacts:{box:number[],label:string,score:number}[]=[];
 const add=(box:number[],label:string)=>contacts.push({box,label,score:.57+random()*.36});
 if(spec.id==='pipeline'){
  const x=250+Math.floor(random()*90);ctx.fillStyle='#071820';ctx.fillRect(x+21,64,37,530);
  ctx.strokeStyle='#ccd5c6';ctx.lineWidth=9;ctx.beginPath();ctx.moveTo(x,62);ctx.lineTo(x+36,596);ctx.stroke();
  ctx.strokeStyle='#eef3cf';ctx.lineWidth=2;ctx.stroke();add([x-14,59,x+57,601],'Pipe-like return');
 }
 for(let i=0;i<(spec.id==='objects'?5:3);i++){
  const x=(i%2?850:110)+Math.floor(random()*300),y=95+i*100+Math.floor(random()*48),w=24+random()*43,h=17+random()*24;
  ctx.save();ctx.translate(x,y);ctx.fillStyle='#061923';ctx.beginPath();ctx.ellipse(w*.85,h*.7,w*1.5,h*.65,.15,0,Math.PI*2);ctx.fill();
  const grad=ctx.createLinearGradient(-w,-h,w,h);grad.addColorStop(0,'#dae6cf');grad.addColorStop(.45,'#9bafac');grad.addColorStop(1,'#344c59');ctx.fillStyle=grad;
  ctx.beginPath();ctx.ellipse(0,0,w*.6,h*.6,-.2,0,Math.PI*2);ctx.fill();ctx.restore();
  add([x-w*.7,y-h*.75,x+w*.8,y+h*.8],i%2?'Compact return':'Object-like return');
 }
 const regions:any[]=[];
 if(spec.id==='coverage'){const y=290+Math.floor(random()*60);ctx.fillStyle='#04101b';ctx.fillRect(0,y,width,25);regions.push({flag:'simulated_dark_band',assessment:'Demo: inspect coverage and try a scan request',evidence:'This band was generated for the interface demonstration; its physical cause is not known.',box_xyxy_pixels:[0,y,width,y+25]})}
 ctx.fillStyle='#031a25dc';ctx.fillRect(16,15,350,32);ctx.fillStyle='#a5d9db';ctx.font='12px monospace';ctx.fillText('SIMULATED SONAR / INTERACTIVE DEMO',28,36);
 return {canvas:c,width,height,contacts,regions,spec,seed};
}
