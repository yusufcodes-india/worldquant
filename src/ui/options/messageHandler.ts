// src/ui/options/messageHandler.ts
/**
 * Placeholder message handler for the options UI.
 */
export function handleOptionsMessage(message: any, sender: any, sendResponse: (response?: any) => void) {
  console.log('Options message received', message);
  // Handle test connection request.
  if (message.action === 'TEST_CONNECTION') {
    // Forward to background to test AI connection via provider.
    // For now, echo success.
    sendResponse?.({ success: true, message: 'Test connection placeholder' });
    return;
  }
  sendResponse?.({ handled: true, source: 'options' });
}
