import {defineConfig} from 'vite';
import {copyFileSync,mkdirSync,readdirSync,unlinkSync} from 'node:fs';
import {resolve} from 'node:path';
export default defineConfig({build:{outDir:'../src/bluecho/dashboard/static',emptyOutDir:true},plugins:[{name:'browser-wasm-assets',closeBundle(){
 const root=resolve(__dirname,'../src/bluecho/dashboard/static');
 if(process.env.VITE_BROWSER_ENGINE==='1'){
  const out=resolve(root,'ort');mkdirSync(out,{recursive:true});
  for(const name of ['ort-wasm-simd-threaded.wasm','ort-wasm-simd-threaded.mjs'])copyFileSync(resolve(__dirname,'node_modules/onnxruntime-web/dist',name),resolve(out,name));
  copyFileSync(resolve(__dirname,'licenses/ONNX-RUNTIME-LICENSE.txt'),resolve(out,'LICENSE.txt'));
 }
 // Browser mode uses the explicit /ort/ path; local API mode never loads WASM.
 // Remove only the redundant generated WASM asset, not application files.
 const assets=resolve(root,'assets');for(const name of readdirSync(assets))if(/^ort-wasm-simd-threaded-[\w-]+\.wasm$/.test(name)){try{unlinkSync(resolve(assets,name))}catch{}}
}}]});
