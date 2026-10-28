import { z } from 'zod';
import { DBRecord, addRecord, getAllRecords, updateRecord, deleteRecord } from '../../storage/database';
import React, { useEffect, useState } from 'react';

type ResearchRun = {
  id: string;
  name: string;
  createdAt: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
};

export const ResearchRuns: React.FC = () => {
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState('');

  const loadRuns = async () => {
    try {
      const records = await getAllRecords<ResearchRun>('researchRuns');
      setRuns(records.map(r => r.data));
    } catch (e) {
      setError('Failed to load runs');
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const addRun = async () => {
    if (!newName) return;
    const run: ResearchRun = {
      id: `run-${Date.now()}`,
      name: newName,
      createdAt: new Date().toISOString(),
      status: 'pending',
    };
    await addRecord('researchRuns', { id: run.id, data: run } as DBRecord<ResearchRun>);
    setNewName('');
    await loadRuns();
  };

  const deleteRun = async (id: string) => {
    await deleteRecord('researchRuns', id);
    await loadRuns();
  };

  return (
    <div style={{ marginTop: '1rem' }}>
      <h3>Research Runs</h3>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ul>
        {runs.map(run => (
          <li key={run.id} style={{ marginBottom: '0.5rem' }}>
            <strong>{run.name}</strong> – {run.status} (created {new Date(run.createdAt).toLocaleString()})
            <button onClick={() => deleteRun(run.id)} style={{ marginLeft: '0.5rem' }}>Delete</button>
          </li>
        ))}
      </ul>
      <div style={{ marginTop: '1rem' }}>
        <input
          type="text"
          placeholder="New run name"
          value={newName}
          onChange={e => setNewName(e.target.value)}
        />
        <button onClick={addRun} style={{ marginLeft: '0.5rem' }}>Add Run</button>
      </div>
    </div>
  );
};
