// src/background/scheduler.ts
/**
 * Scheduler placeholder using chrome.alarms.
 * Real implementation will register alarms for job retries, rate‑limiting, and recovery.
 */

export function scheduleAlarm(name: string, delayMinutes: number) {
  chrome.alarms.create(name, { delayInMinutes: delayMinutes });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  console.log('Alarm triggered:', alarm.name);
  // In a full implementation we would dispatch to the appropriate job handler.
});
