import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

function Options() {
  const [apiKey, setApiKey] = useState('');
  const [modelId, setModelId] = useState('');

  const saveSettings = async () => {
    // Store in chrome.storage.session (ephemeral)
    await chrome.storage.session.set({ apiKey, modelId });
    alert('Settings saved (session only).');
  };

  const testConnection = async () => {
    const result = await chrome.runtime.sendMessage({ type: 'OPTIONS', action: 'TEST_CONNECTION' });
    alert(result?.message ?? 'No response');
  };

  return (
    <div style={{ padding: '8px', fontFamily: 'sans-serif' }}>
      <h2>BRAIN Alpha Settings</h2>
      <label>
        Gemini API Key:<br />
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter your Gemini API key"
        />
      </label>
      <br />
      <label>
        Model ID:<br />
        <input
          type="text"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          placeholder="e.g. gemini-1.5-pro"
        />
      </label>
      <br />
      <button onClick={saveSettings}>Save (session)</button>
      <button onClick={testConnection} style={{ marginLeft: '8px' }}>
        Test Connection
      </button>
    </div>
  );
}

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<Options />);
}
