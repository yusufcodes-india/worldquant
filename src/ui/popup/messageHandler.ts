// src/ui/popup/messageHandler.ts
/**
 * Placeholder message handler for the popup UI.
 * In full implementation it would handle requests such as connection status,
 * initiating a new research run, etc.
 */
export function handlePopupMessage(message: any, sender: any, sendResponse: (response?: any) => void) {
  // Simple echo for now.
  console.log('Popup message received', message);
  // No async work – reply immediately.
  sendResponse && sendResponse({ handled: true, source: 'popup' });
}
