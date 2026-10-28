import React, { useState } from 'react';
import { z } from 'zod';
import { addRecord, DBRecord } from '../../storage/database';

// Simple example schema for Alpha JSON import – adjust as needed.
// Assume the JSON is an array of objects with "symbol" and "value" fields.
const AlphaItemSchema = z.object({
  symbol: z.string(),
  value: z.number(),
});
const AlphaFileSchema = z.array(AlphaItemSchema);

type AlphaItem = z.infer<typeof AlphaItemSchema>;

type AlphaFile = z.infer<typeof AlphaFileSchema>;

export const Dashboard: React.FC = () => {
  const [fileContent, setFileContent] = useState<string>('');
  const [preview, setPreview] = useState<AlphaItem[]>([]);
  const [error, setError] = useState<string>('');
  const [status, setStatus] = useState<string>('');

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setStatus('');
    try {
      const text = await file.text();
      setFileContent(text);
      const parsed = AlphaFileSchema.parse(JSON.parse(text));
      // Show first 5 entries as preview
      setPreview(parsed.slice(0, 5));
    } catch (err) {
      console.error(err);
      setError('Invalid JSON or does not match expected schema.');
      setPreview([]);
    }
  };

  const handleSave = async () => {
    if (!fileContent) {
      setError('No file loaded.');
      return;
    }
    try {
      const data = AlphaFileSchema.parse(JSON.parse(fileContent));
      const record: DBRecord<AlphaFile> = {
        id: `alpha-${Date.now()}`,
        data,
      };
      await addRecord('alphaImports', record);
      setStatus('File saved to IndexedDB successfully.');
    } catch (err) {
      console.error(err);
      setError('Failed to save: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  return (
    <div style={{ padding: '1rem', fontFamily: 'Arial, sans-serif' }}>
      <h2>BRAIN Alpha Import Wizard</h2>
      <input type="file" accept=".json,application/json" onChange={handleFileChange} />
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {preview.length > 0 && (
        <div>
          <h3>Preview (first {preview.length} items)</h3>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                <th style={{ border: '1px solid #ddd', padding: '4px' }}>Symbol</th>
                <th style={{ border: '1px solid #ddd', padding: '4px' }}>Value</th>
              </tr>
            </thead>
            <tbody>
              {preview.map((item, idx) => (
                <tr key={idx}>
                  <td style={{ border: '1px solid #ddd', padding: '4px' }}>{item.symbol}</td>
                  <td style={{ border: '1px solid #ddd', padding: '4px' }}>{item.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button onClick={handleSave} style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}>
        Save to IndexedDB
      </button>
      {status && <p style={{ color: 'green' }}>{status}</p>}
    </div>
  );
};
