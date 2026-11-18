import { describe,it,expect } from 'vitest';
import { detectPageState } from '../../src/browser/session.js';
import { attachMockDocuments } from '../../src/browser/mock-upload.js';

describe('Playwright browser support',()=>{
  it('detects mock page states without inspecting login values',()=>{expect(detectPageState({url:()=> 'http://127.0.0.1/mock/login'})).toBe('WAITING_FOR_LOGIN');expect(detectPageState({url:()=> 'http://127.0.0.1/mock/dashboard'})).toBe('AUTHENTICATED');expect(detectPageState({url:()=> 'http://127.0.0.1/mock/payment'})).toBe('PAYMENT_REACHED');expect(detectPageState({url:()=> 'https://appointment.ivacbd.com/unknown'})).toBe('UNKNOWN');});
  it('attaches selected mock files only on the mock upload page',async()=>{const selected=[];const page={url:()=> 'http://127.0.0.1/mock/book',locator:()=>({nth:slot=>({setInputFiles:async file=>selected.push({slot,file})})})};expect(await attachMockDocuments(page,[{slot:0,path:'/private/primary.pdf'},null,{slot:2,path:'/private/secondary.pdf'}])).toBe(2);expect(selected).toEqual([{slot:0,file:'/private/primary.pdf'},{slot:2,file:'/private/secondary.pdf'}]);await expect(attachMockDocuments({...page,url:()=> 'https://appointment.ivacbd.com/upload'},[])).rejects.toThrow('mock upload step');});
});
