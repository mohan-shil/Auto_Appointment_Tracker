import { describe,it,expect,beforeAll,afterAll } from 'vitest';
import { expect as pwExpect } from 'playwright/test';
import { launchBrowser } from '../../src/browser/session.js';
import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import net from 'node:net';

let proc,browser,base,dataDir,port;
const getPort=()=>new Promise((resolve,reject)=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});s.on('error',reject);});
beforeAll(async()=>{port=await getPort();base=`http://127.0.0.1:${port}`;dataDir=await fs.mkdtemp(path.join(os.tmpdir(),'ivac-v3-server-'));proc=spawn(process.execPath,['src/server/index.js'],{env:{...process.env,PORT:String(port),V3_DATA_DIR:dataDir},stdio:'ignore'});for(let i=0;i<80;i++){try{if((await fetch(base)).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}browser=await launchBrowser({mode:'mock',headless:true,baseURL:base});},30000);
afterAll(async()=>{await browser?.close();proc?.kill();if(dataDir)await fs.rm(dataDir,{recursive:true,force:true});});
describe('local mock IVAC pages',()=>{
  it('navigates mock login, dashboard, upload, calendar and payment without live-site requests',async()=>{
    const page=await browser.context.newPage();const external=[];page.on('request',req=>{if(!req.url().startsWith(base))external.push(req.url());});
    await page.goto(`${base}/mock/login?scenario=second`);await pwExpect(page.getByRole('heading',{name:'Mock IVAC Login'})).toBeVisible();
    await page.getByRole('button',{name:'Simulate manual login'}).click();await page.getByRole('button',{name:'Book an Appointment'}).click();
    await pwExpect(page.getByRole('heading',{name:'Mock Webfile Upload'})).toBeVisible();expect(await page.locator('input[type=file]').count()).toBe(4);
    await page.getByRole('button',{name:'Continue'}).click();await pwExpect(page.getByRole('heading',{name:'Mock Calendar'})).toBeVisible();
    const dates=page.locator('#dates button');expect(await dates.count()).toBe(2);await dates.nth(0).click();await pwExpect(page.locator('#result')).toContainText('unavailable');await dates.nth(1).click();await pwExpect(page.locator('#result')).toContainText('accepted');await page.locator('#slots button:not([disabled])').first().click();await pwExpect(page.locator('#result')).toContainText('09:00');
    await page.getByRole('button',{name:/Continue after/}).click();await pwExpect(page.getByRole('heading',{name:'PAYMENT STAGE REACHED'})).toBeVisible();expect(external).toEqual([]);await page.close();
  },30000);
  it('serves the local dashboard and drives a complete mock state-machine run to payment stop',async()=>{
    const page=await browser.context.newPage();await page.goto(base);await pwExpect(page.getByRole('heading',{name:'IVAC Appointment Assistant V3'})).toBeVisible();
    await page.evaluate(()=>fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:'mock',scenario:'second',intervalMs:1000})}));
    await page.locator('input[data-slot="0"]').setInputFiles({name:'fictional-primary.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.7 synthetic test PDF')});
    let documentState;for(let i=0;i<30;i++){documentState=await page.evaluate(()=>fetch('/api/state').then(r=>r.json()));if(documentState.documents.some(d=>d.slot===0))break;await page.waitForTimeout(50);}expect(documentState.documents.some(d=>d.slot===0)).toBe(true);
    await page.locator('#interval').fill('1');await page.getByRole('button',{name:'Start mock workflow'}).click();let waiting;for(let i=0;i<20;i++){waiting=await page.evaluate(()=>fetch('/api/state').then(r=>r.json()));if(waiting.state==='WAITING_FOR_LOGIN')break;await page.waitForTimeout(50);}expect(waiting.state).toBe('WAITING_FOR_LOGIN');
    await page.getByRole('button',{name:'Pause'}).click();await pwExpect.poll(async()=>page.evaluate(()=>fetch('/api/state').then(r=>r.json()).then(s=>s.state))).toBe('PAUSED');await page.getByRole('button',{name:'Resume'}).click();
    const loginPage=await browser.context.newPage();await loginPage.goto(`${base}/mock/login`);await loginPage.getByRole('button',{name:'Simulate manual login'}).click();await loginPage.close();
    let result;for(let i=0;i<60;i++){result=await page.evaluate(()=>fetch('/api/state').then(r=>r.json()));if(result.state==='PAYMENT_REACHED')break;await page.waitForTimeout(100);}
    expect(result.state).toBe('PAYMENT_REACHED');expect(result.attempts).toHaveLength(2);expect(result.attempts[0].result).toBe('unavailable');expect(result.attempts[1].result).toBe('available');expect(result.attempts[0].cycle).toBe(1);
    const restart=await page.evaluate(()=>fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}).then(r=>r.status));expect(restart).toBe(409);
    await page.getByRole('button',{name:'Stop',exact:true}).click();await pwExpect.poll(async()=>page.evaluate(()=>fetch('/api/state').then(r=>r.json()).then(s=>s.state))).toBe('STOPPED');await page.getByRole('button',{name:'Delete all local documents'}).click();await page.close();
  },30000);
  it('updates the visible mock calendar and rejects cross-origin state-changing requests',async()=>{const page=await browser.context.newPage();await page.goto(`${base}/mock/calendar?scenario=changing`);await page.locator('#dates button').first().click();await pwExpect(page.locator('#dates button')).toHaveCount(3);await page.locator('#dates button').nth(2).click();await pwExpect(page.locator('#result')).toContainText('accepted');await page.locator('#slots button:not([disabled])').first().click();const rejected=await fetch(`${base}/api/stop`,{method:'POST',headers:{Origin:'https://attacker.example'}});expect(rejected.status).toBe(403);await page.close();});
  it('closes its owned Playwright browser cleanly',async()=>{expect(browser.isOpen).toBe(true);await browser.close();expect(browser.isOpen).toBe(false);});
});
