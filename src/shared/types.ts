// Shared type definitions for AI providers and BRAIN interactions

export interface CandidateInput {
  expression: string;
  settings?: Record<string, unknown>;
  hypothesis?: string;
  examples?: { id: string }[]; // Simplified example alphas
}

export interface CandidateProposal {
  id: string;
  expression: string;
  score?: number;
}

export interface RevisionInput {
  parentTrialId?: string;
  expression: string;
  diagnostics?: string;
}

export interface RevisionProposal {
  id: string;
  revisedExpression: string;
  improvement?: number;
}

export interface ConnectionResult {
  success: boolean;
  message?: string;
}
