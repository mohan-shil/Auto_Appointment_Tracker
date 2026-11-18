import { IVAC_ORIGIN } from './session.js';

const WORDS=new Set('ivac appointment application applicant applicants visa webfile passport login sign signup register account profile dashboard home public landing page otp email mobile phone password submit continue next back cancel close open upload file files choose select centre center location date calendar payment pay invoice confirm confirmation help faq notice important welcome required optional primary secondary name number reference details information document documents status search verify verification available unavailable total fee transaction receipt logout menu navigation contact support terms privacy english online booking official system'.split(' '));
function safeText(s){if(typeof s!=='string'||/\d|@|\+/.test(s))return '[omitted]';const words=s.toLowerCase().match(/[a-z]+/g)||[];return words.length&&words.every(w=>WORDS.has(w))?s.trim().slice(0,100):'[omitted]';}
const safeSegment=p=>!p?'':(WORDS.has(p.toLowerCase())&&!/\d|@/.test(p)?p:'[redacted]');
export async function inspectCurrentPage(page){
  const parsed=new URL(page.url());if(parsed.origin!==IVAC_ORIGIN)throw new Error('Real inspection is limited to the official IVAC host.');
  const raw=await page.evaluate(()=>{
    const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;};
    const label=e=>{const l=e.labels?.[0]||e.closest('label');return l?.innerText||e.getAttribute('aria-label')||'';};
    const text=e=>(e.innerText||e.getAttribute('aria-label')||'').trim();
    return {title:document.title,headings:Array.from(document.querySelectorAll('h1,h2,h3,[role="heading"]')).filter(visible).map(text),buttons:Array.from(document.querySelectorAll('button,[role="button"]')).filter(visible).map(text),links:Array.from(document.querySelectorAll('a[href]')).filter(visible).map(a=>({label:text(a),href:a.href})),controls:Array.from(document.querySelectorAll('input,select,textarea')).filter(visible).map(e=>({label:label(e),type:e.type||e.tagName.toLowerCase(),required:!!e.required,disabled:!!e.disabled,options:e.tagName==='SELECT'?Array.from(e.options).filter(o=>!o.disabled).map(o=>o.textContent.trim()):[],accept:e.type==='file'?e.getAttribute('accept')||'':''}))};
  });
  const parts=parsed.pathname.split('/').filter(Boolean);const pathname='/'+parts.map(safeSegment).join('/');
  return {capturedAt:new Date().toISOString(),hostname:parsed.hostname,pathname,title:safeText(raw.title),headings:raw.headings.map(safeText),buttons:raw.buttons.map(safeText),links:raw.links.map(x=>({label:safeText(x.label),destination:(()=>{try{const u=new URL(x.href);return u.origin===IVAC_ORIGIN?'/'+u.pathname.split('/').filter(Boolean).map(safeSegment).join('/'): '[external destination omitted]';}catch{return '[destination omitted]';}})()})),controls:raw.controls.filter(c=>!['password','hidden'].includes(c.type)).map(c=>({label:safeText(c.label),type:c.type,required:c.required,disabled:c.disabled,options:c.options.map(safeText),acceptedFileTypes:c.accept}))};
}
export const realAutomationCapabilities=Object.freeze({visibleManualBrowser:true,automatedWorkflow:false,continuousMonitoring:false,reason:'IVAC terms, selectors, and permission for automation have not been verified.'});
