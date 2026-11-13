// Alpha Research Pilot - Background Service Worker (MV3)
// Lightweight coordinator only; all durable queueing and engine state reside in local backend.

chrome.runtime.onInstalled.addListener(() => {
  console.log("Alpha Research Pilot Extension installed.");
});

// Listener for messages from popup or dashboard
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "OPEN_DASHBOARD") {
    chrome.tabs.create({ url: chrome.runtime.getURL("dashboard.html") });
    sendResponse({ success: true });
  }
  return true;
});
