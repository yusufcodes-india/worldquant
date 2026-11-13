from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SimulationSettings(BaseModel):
    region: str = "USA"
    universe: str = "TOP3000"
    delay: int = 1
    decay: int = 0
    neutralization: str = "Subindustry"
    truncation: float = 0.08
    nan_handling: str = "On"
    pasteurization: str = "On"
    test_period: str = "1 year"
    language: str = "Fast Expression"

class RuleProfile(BaseModel):
    name: str = "Low-Corr Sprint"
    max_operators: int = 8
    max_fields: int = 4
    min_qualifying_alphas: int = 10
    min_initial_ranking: int = 2
    competition_start_date: str = "2026-11-07"
    ranking_objective: str = "lowest average production correlation"
    tie_breaker: str = "more simulations"
    # Performance baseline thresholds
    min_sharpe: float = 1.25
    min_fitness: float = 1.0
    min_turnover: float = 0.01  # 1%
    max_turnover: float = 0.70  # 70%
    max_self_correlation_target: float = 0.60 # research preference
    official_self_correlation_threshold: float = 0.70
    require_weight_distribution_pass: bool = True
    require_subuniverse_pass: bool = True
    simulation_settings: SimulationSettings = Field(default_factory=SimulationSettings)

class CampaignCreate(BaseModel):
    name: str
    profile: RuleProfile = Field(default_factory=RuleProfile)
    budget_simulations: int = 1500
    budget_gemini_calls: int = 150
    budget_tokens: int = 500000
    simulation_concurrency: int = 1
    stop_on_first_qualifying: bool = False

class CampaignResponse(BaseModel):
    id: str
    name: str
    profile_name: str
    profile_snapshot: Dict[str, Any]
    budget_simulations: int
    submitted_simulations_count: int
    budget_gemini_calls: int
    gemini_calls_count: int
    budget_tokens: int
    tokens_used_count: int
    simulation_concurrency: int
    stop_on_first_qualifying: bool
    status: str
    created_at: str
    updated_at: str

class CandidateCreate(BaseModel):
    expression: str
    hypothesis: Optional[str] = None
    signal_family: Optional[str] = None
    parent_candidate_id: Optional[str] = None
    design_change: Optional[str] = None
    expected_risks: Optional[str] = None

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    unique_fields: List[str] = []
    grouping_identifiers: List[str] = []
    named_functions: List[str] = []
    arithmetic_operators: List[str] = []
    estimated_operators: int = 0
    estimated_fields: int = 0
    unit_status: str = "VERIFIED_PASS" # or REQUIRES_PLATFORM_VERIFICATION or REJECTED
    normalized_expression: str = ""
    normalized_hash: str = ""

class SimulationResultResponse(BaseModel):
    id: str
    candidate_id: str
    campaign_id: str
    is_mock: bool
    platform_status: str
    main_sharpe: Optional[float] = None
    fitness: Optional[float] = None
    turnover: Optional[float] = None
    subuniverse_sharpe: Optional[float] = None
    subuniverse_cutoff: Optional[float] = None
    subuniverse_pass_margin: Optional[float] = None
    weight_distribution_pass: Optional[bool] = None
    platform_reported_field_count: Optional[int] = None
    platform_reported_op_count: Optional[int] = None
    counts_verified: bool = False
    pnl_series: Optional[List[Dict[str, Any]]] = None
    created_at: str

class CorrelationRecordResponse(BaseModel):
    id: str
    candidate_id: str
    check_type: str
    status: str
    measured_value: Optional[float] = None
    target_value: Optional[float] = None
    official_threshold: Optional[float] = None
    official_pass: Optional[bool] = None
    comparison_alphas: Optional[List[str]] = None
    is_local_estimate: bool = False
    provenance_source: str
    notes: Optional[str] = None
    checked_at: str

class CandidateDetailResponse(BaseModel):
    id: str
    campaign_id: str
    expression: str
    normalized_hash: str
    hypothesis: Optional[str] = None
    signal_family: Optional[str] = None
    parent_candidate_id: Optional[str] = None
    design_change: Optional[str] = None
    expected_risks: Optional[str] = None
    estimated_fields: int
    estimated_operators: int
    validation_status: str
    validation_errors: List[str] = []
    queue_status: str
    submission_id: Optional[str] = None
    retry_count: int
    created_at: str
    updated_at: str
    simulation_result: Optional[SimulationResultResponse] = None
    correlations: List[CorrelationRecordResponse] = []
    is_sprint_eligible: bool = False
    readiness_summary: str = "NOT READY"

class ReferenceAlphaCreate(BaseModel):
    id: str
    expression: str
    signal_family: Optional[str] = None
    description: Optional[str] = None
    status: str = "USER_REPORTED"
    submitted_date: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    pnl_series: Optional[List[Dict[str, Any]]] = None

class ReferenceAlphaResponse(BaseModel):
    id: str
    expression: str
    signal_family: Optional[str] = None
    description: Optional[str] = None
    status: str
    submitted_date: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    pnl_series: Optional[List[Dict[str, Any]]] = None
    created_at: str

class LocalCorrelationRequest(BaseModel):
    candidate_id: str
    reference_alpha_id: str

class LocalCorrelationResponse(BaseModel):
    candidate_id: str
    reference_alpha_id: str
    signed_correlation: float
    absolute_correlation: float
    overlap_period: str
    observation_count: int
    disclaimer: str = "LOCAL ESTIMATE — NOT THE PLATFORM SELF-CORRELATION CHECK."
    warnings: List[str] = []

class GeminiCandidatePayload(BaseModel):
    expression: str
    economic_hypothesis: str
    signal_family: str
    parent_experiment_id: Optional[str] = None
    exact_changed_design_choice: str
    expected_risks: str
    estimated_fields: int
    estimated_operators: int

class GeminiBatchResponse(BaseModel):
    candidates: List[GeminiCandidatePayload]
