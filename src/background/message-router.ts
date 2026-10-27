// src/background/message-router.ts
/**
 * Simple message router for background service worker.
 * Listens to chrome.runtime.onMessage and forwards to appropriate handlers.
 */

import { handlePopupMessage } from '../ui/popup/messageHandler';
import { handleDashboardMessage } from '../ui/dashboard/messageHandler';
import { handleOptionsMessage } from '../ui/options/messageHandler';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Basic validation – ensure a `type` field exists.
  if (!message || typeof message.type !== 'string') {
    console.warn('Received malformed message', message);
    return false;
  }

  switch (message.type) {
    case 'POPUP':
      handlePopupMessage(message, sender, sendResponse);
      break;
    case 'DASHBOARD':
      handleDashboardMessage(message, sender, sendResponse);
      break;
    case 'OPTIONS':
      handleOptionsMessage(message, sender, sendResponse);
      break;
    default:
      console.warn('Unknown message type', message.type);
  }
  // Return true to indicate async response if any handler calls sendResponse asynchronously.
  return true;
});
