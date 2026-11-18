import { describe,it,expect } from 'vitest';
import { inspectCurrentPage, realAutomationCapabilities } from '../../src/browser/real-ivac-adapter.js';

describe('real IVAC adapter boundaries',()=>{
  it('inspects sanitized visible structure without reading values, CAPTCHA metadata, or dynamic paths',async()=>{
    const page={url:()=> 'https://appointment.ivacbd.com/account/ABCD123456?token=secret#fragment',evaluate:async fn=>{
      const source=String(fn);
      expect(source).not.toMatch(/\.value|cookie|localStorage|sessionStorage|innerHTML|outerHTML|fetch\(|captcha|recaptcha|hcaptcha/i);
      return {title:'IVAC Appointment',headings:['Book an Appointment','Applicant Name'],buttons:['Continue'],links:[{label:'Appointment',href:'https://appointment.ivacbd.com/appointment?email=private@example.test'}],controls:[{label:'Email',type:'email',required:true,disabled:false,options:[],accept:''},{label:'Password',type:'password',required:true,disabled:false,options:[],accept:''}]};
    }};
    const report=await inspectCurrentPage(page);
    expect(report.hostname).toBe('appointment.ivacbd.com');
    expect(report.pathname).toBe('/account/[redacted]');
    expect(report.links[0].destination).toBe('/appointment');
    expect(report.controls).toHaveLength(1);
    expect('captchaWidgetPresent' in report).toBe(false);
    expect(JSON.stringify(report)).not.toContain('private@example.test');
  });
  it('does not claim unverified real automation capability',()=>{expect(realAutomationCapabilities.automatedWorkflow).toBe(false);expect(realAutomationCapabilities.continuousMonitoring).toBe(false);});
  it('rejects any nonofficial browser origin before inspecting',async()=>{await expect(inspectCurrentPage({url:()=> 'https://example.test/',evaluate:()=>{throw new Error('should not inspect');}})).rejects.toThrow('official IVAC');});
});
