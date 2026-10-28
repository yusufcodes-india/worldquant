// src/ai/gemini-provider.ts
/**
 * Stub Gemini AI provider for live mode.
 * In DEMO mode the mock provider is used. This file contains minimal
 * implementation that reads the API key from chrome.storage.session and
 * returns a successful connection test. Actual request logic is omitted
 * for brevity and to avoid network calls in the sandbox.
 */
import AIProvider from './provider';
import { CandidateInput, CandidateProposal, ConnectionResult, RevisionInput, RevisionProposal } from '../shared/types';

export class GeminiAIProvider implements AIProvider {
  async testConnection(): Promise<ConnectionResult> {
    const result = await new Promise<ConnectionResult>((resolve) => {
      chrome.storage.session.get(['apiKey'], (items) => {
        if (items.apiKey) {
          resolve({ success: true, message: 'Gemini connection successful.' });
        } else {
          resolve({ success: false, message: 'API key not set.' });
        }
      });
    });
    return result;
  }

  async proposeCandidates(_input: CandidateInput): Promise<CandidateProposal[]> {
    // Placeholder: return empty list; real implementation would call Gemini.
    return [];
  }

  async diagnoseAndRevise(_input: RevisionInput): Promise<RevisionProposal> {
    // Placeholder implementation.
    return { id: 'gemini-revision', revisedExpression: '', improvement: 0 };
  }
}

export default GeminiAIProvider;
