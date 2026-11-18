const asDate = (value) => {
  if (value instanceof Date && !Number.isNaN(value.valueOf())) return new Date(value.getFullYear(), value.getMonth(), value.getDate());
  if (typeof value !== 'string') return null;
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const d = new Date(+match[1], +match[2] - 1, +match[3]);
  return d.getFullYear() === +match[1] && d.getMonth() === +match[2] - 1 && d.getDate() === +match[3] ? d : null;
};

export function sortEligibleDates(values, today = new Date()) {
  const floor = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const format = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  return [...new Set(values.map(asDate).filter(d => d && d >= floor).map(format))].sort();
}

export function selectFirstValidTimeSlot(slots) {
  if (!Array.isArray(slots)) return null;
  const slot=slots.find(item=>typeof item==='string' ? item.trim() : item && item.available===true && item.disabled!==true);
  return typeof slot==='string' ? slot.trim() : slot?.value ?? slot?.label ?? null;
}

export class CalendarEngine {
  constructor({ intervalMs = 20000, maxAttempts = 12 } = {}) {
    this.intervalMs = Math.max(1000, Number(intervalMs) || 20000);
    this.maxAttempts = maxAttempts;
    this.attempted = new Map();
  }
  next(dates, today = new Date()) {
    if (this.attempted.size >= this.maxAttempts) return null;
    return sortEligibleDates(dates, today).find(d => !this.attempted.has(d)) || null;
  }
  record(date, result) {
    if (this.attempted.has(date)) return false;
    this.attempted.set(date, result);
    return true;
  }
  refresh(dates, today = new Date()) { return sortEligibleDates(dates, today); }
}
