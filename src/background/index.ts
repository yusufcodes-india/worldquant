// src/background/index.ts
/**
 * Background service worker entry point. It imports the message router which registers
 * chrome.runtime.onMessage listeners. Additionally it sets up a periodic
 * improvement loop using chrome.alarms.
 */
import './message-router';

// ------------------------------------------------------------
// Scheduler: fire an alarm every hour to run a placeholder improvement loop.
// ------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  // Create an alarm that repeats every 60 minutes (1 hour).
  chrome.alarms.create('improvementLoop', { periodInMinutes: 60 });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'improvementLoop') {
    console.log('🕒 Improvement loop alarm triggered');
    // Placeholder: In a full implementation you would invoke an AI provider
    // method here to run a scheduled improvement or batch processing task.
    // Example (not executed now):
    // const provider = new GeminiAIProvider();
    // provider.proposeCandidates({ hypothesis: 'example' });
  }
});

// You can add other background tasks here.
