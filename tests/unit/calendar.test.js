import { describe,it,expect } from 'vitest';
import { sortEligibleDates, CalendarEngine, selectFirstValidTimeSlot } from '../../src/calendar/engine.js';

describe('calendar engine',()=>{
  it('normalizes, deduplicates and sorts valid future dates',()=>{
    expect(sortEligibleDates(['2026-12-03','2026-12-01','2026-12-01','2026-02-31','bad'],new Date(2026,10,18))).toEqual(['2026-12-01','2026-12-03']);
  });
  it('selects each currently displayed date chronologically once and refreshes changed calendars',()=>{
    const engine=new CalendarEngine({maxAttempts:5});const now=new Date(2026,10,18);
    expect(engine.next(['2026-12-03','2026-12-01'],now)).toBe('2026-12-01');engine.record('2026-12-01','unavailable');
    expect(engine.next(['2026-12-03','2026-12-01'],now)).toBe('2026-12-03');
    expect(engine.refresh(['2026-12-04','2026-12-03'],now)).toEqual(['2026-12-03','2026-12-04']);
    expect(engine.record('2026-12-01','duplicate')).toBe(false);
  });
  it('chooses the first valid available time slot only',()=>{
    expect(selectFirstValidTimeSlot([{label:'08:00',available:false},{label:'09:00',available:true},{label:'10:00',available:true}])).toBe('09:00');
    expect(selectFirstValidTimeSlot([])).toBeNull();
  });
});
