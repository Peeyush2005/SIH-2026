/** Publicly attributable real sonar samples; no procedural image generator. */
import catalog from '../public/real-demo/catalog.json';
// Local presentation bundles can add approved-access samples without publishing them.
const localSamples=['127.0.0.1','localhost','[::1]'].includes(location.hostname)
 ? ((window as Window & {BLUECHO_LOCAL_DEMOS?:typeof catalog}).BLUECHO_LOCAL_DEMOS||[]) : [];
export const REAL_DEMO_SAMPLES=[...catalog,...localSamples];
export const DEMO_SCENARIOS=REAL_DEMO_SAMPLES.filter(s=>!['noaa0','seabed'].includes(s.id));
export function nextDemoScenario(current?:string,seed=crypto.getRandomValues(new Uint32Array(1))[0]){
 const choices=DEMO_SCENARIOS.filter(s=>s.id!==current);return choices[seed%choices.length].id;
}
