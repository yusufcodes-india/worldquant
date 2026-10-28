// src/ai/mock-provider.ts
/**
 * Deterministic mock AI provider used in DEMO mode.
 * Returns a fixed set of candidate proposals so the UI can be exercised
 * without any external network calls or API keys.
 */
import AIProvider from './provider';
import { CandidateInput, CandidateProposal, ConnectionResult, RevisionInput, RevisionProposal } from '../shared/types';

export class MockAIProvider implements AIProvider {
  async testConnection(): Promise<ConnectionResult> {
    return { success: true, message: 'Mock connection successful (no real API key required).' };
  }

  async proposeCandidates(input: CandidateInput): Promise<CandidateProposal[]> {
    // Produce up to 3 deterministic candidates based on the hypothesis string length.
    const base = (input.hypothesis ?? '').replace(/\s+/g, ' ').trim();
    const candidates: CandidateProposal[] = [];
    for (let i = 1; i <= 3; i++) {
      candidates.push({
        id: `mock-${i}`,
        expression: `${base} /* candidate ${i} */`,
        score: i,
      });
    }
    return candidates;
  }

  async diagnoseAndRevise(input: RevisionInput): Promise<RevisionProposal> {
    // Simple deterministic revision: prepend "rev_" to the expression.
    const revised = `rev_${input.expression}`;
    return {
      id: 'mock-revision',
      revisedExpression: revised,
      improvement: 0,
    };
  }
}

export default MockAIProvider;
