import { chromium } from 'playwright';
import { URL } from 'node:url';

export const IVAC_ORIGIN = 'https://appointment.ivacbd.com';
export class BrowserSession {
  constructor(browser, context, page, mode) { this.browser=browser; this.context=context; this.page=page; this.mode=mode; this.closed=false; }
  get isOpen() { return !this.closed && !this.page.isClosed(); }
  async close() { if(this.closed)return; this.closed=true; await this.browser.close(); }
}
export async function launchBrowser({mode='mock',headless=false,baseURL='http://127.0.0.1:4173'}={}) {
  if (!['mock','real'].includes(mode)) throw new Error('Unknown browser mode.');
  let mockBase;
  try { mockBase=new URL(baseURL); } catch { throw new Error('Invalid local mock address.'); }
  if(mode==='mock'&&(mockBase.protocol!=='http:'||!['127.0.0.1','localhost','::1'].includes(mockBase.hostname)))throw new Error('Mock mode is restricted to a local loopback address.');
  const browser=await chromium.launch({headless});
  const context=await browser.newContext(); const page=await context.newPage();
  try { await page.goto(mode==='mock'?`${mockBase.origin}/mock/login`:IVAC_ORIGIN,{waitUntil:'domcontentloaded',timeout:30000}); }
  catch(error) { await browser.close(); throw new Error('Website unavailable or browser navigation failed.'); }
  return new BrowserSession(browser,context,page,mode);
}
export function detectPageState(page) {
  let url;try{url=new URL(page.url());}catch{return 'UNKNOWN';}
  if(url.protocol!=='http:'||!['127.0.0.1','localhost','::1'].includes(url.hostname))return 'UNKNOWN';
  if(url.pathname==='/mock/login') return 'WAITING_FOR_LOGIN';
  if(url.pathname==='/mock/payment') return 'PAYMENT_REACHED';
  if(url.pathname==='/mock/book') return 'DOCUMENT_STEP';
  if(url.pathname==='/mock/calendar') return 'CALENDAR_STEP';
  if(url.pathname==='/mock/dashboard') return 'AUTHENTICATED';
  return 'UNKNOWN';
}
