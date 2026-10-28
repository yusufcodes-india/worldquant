// src/ai/provider.ts
/**
 * Abstract interface that all AI providers must implement.
 * The UI and background scheduler will interact only via this contract.
 */

import { CandidateInput, CandidateProposal, ConnectionResult, RevisionInput, RevisionProposal } from '../shared/types';

export interface AIProvider {
  /**
   * Test the connection using the stored credentials.
   * Should return a ConnectionResult indicating success or the error.
   */
  testConnection(): Promise<ConnectionResult>;

  /**
   * Given a hypothesis, current expression, settings, and example alphas,
   * propose a bounded list of candidate expressions.
   */
  proposeCandidates(input: CandidateInput): Promise<CandidateProposal[]>;

  /**
   * Given diagnostics from a previous run, propose a revision (or STOP).
   */
  diagnoseAndRevise(input: RevisionInput): Promise<RevisionProposal>;
}

export default AIProvider;
