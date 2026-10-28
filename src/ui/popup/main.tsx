import React from 'react';
import { createRoot } from 'react-dom/client';

function Popup() {
  const openDashboard = () => {
    // Open the dashboard page in a new tab.
    chrome.tabs.create({ url: chrome.runtime.getURL('dashboard.html') });
  };

  const testConnection = async () => {
    const result = await chrome.runtime.sendMessage({ type: 'OPTIONS', action: 'TEST_CONNECTION' });
    alert(result?.message ?? 'No response');
  };

  return (
    <div style={{ padding: '8px', fontFamily: 'sans-serif' }}>
      <h2>BRAIN Alpha</h2>
      <button onClick={testConnection}>Test AI Connection</button>
      <button onClick={openDashboard} style={{ marginLeft: '8px' }}>
        Open Dashboard
      </button>
    </div>
  );
}

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Popup />);
}
