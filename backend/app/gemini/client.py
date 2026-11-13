import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.models.schemas import GeminiCandidatePayload, GeminiBatchResponse
from app.engine.fast_expression import CONFIRMED_FIELDS, CONFIRMED_FUNCTIONS, CONFIRMED_GROUPINGS

logger = logging.getLogger("alpha_pilot.gemini")

class GeminiResearchClient:
    def __init__(self):
        self.api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = settings.gemini_model
        self.calls_count = 0
        self.tokens_used = 0
        self.is_paused = False
        self.backoff_until: Optional[float] = None

    def set_api_key(self, key: str):
        self.api_key = key
        # Reset backoff if new key provided
        self.backoff_until = None
        self.is_paused = False

    def generate_candidates(
        self,
        profile_rules: Dict[str, Any],
        parent_seed: Optional[Dict[str, Any]] = None,
        reference_alphas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 5
    ) -> List[GeminiCandidatePayload]:
        """
        Generates candidate alphas using Gemini structured outputs.
        If no API key is provided, returns high-quality deterministic seed variations
        so mock research works autonomously out-of-the-box.
        """
        if self.backoff_until and time.time() < self.backoff_until:
            logger.warning("Gemini API in backoff period due to quota/rate limit. Deferring call.")
            return []

        if not self.api_key:
            logger.info("No Gemini API key configured. Utilizing local deterministic generator.")
            return self._generate_mock_candidates(profile_rules, parent_seed, reference_alphas, batch_size)

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            
            prompt = self._build_prompt(profile_rules, parent_seed, reference_alphas, batch_size)
            prompt += "\nOutput ONLY valid JSON adhering to the schema: {\"candidates\": [{\"expression\": \"...\", \"economic_hypothesis\": \"...\", \"signal_family\": \"...\", \"exact_changed_design_choice\": \"...\", \"expected_risks\": \"...\"}]}"

            interaction = client.interactions.create(
                model=self.model,
                input=prompt,
            )
            
            self.calls_count += 1
            raw_text = interaction.output_text.strip()
            
            # Clean Markdown wrapping if returned
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
            if raw_text.endswith("```"):
                raw_text = raw_text.rsplit("```", 1)[0]
            
            parsed = json.loads(raw_text.strip())
            candidates_raw = parsed.get("candidates", [])
            return [GeminiCandidatePayload(**c) for c in candidates_raw]

        except Exception as e:
            err_str = str(e)
            logger.error(f"Gemini API call failed: {err_str}")
            if "429" in err_str or "quota" in err_str.lower():
                self.backoff_until = time.time() + 60.0 # 60s backoff
                self.is_paused = True
            # Fallback to local candidates so campaign execution doesn't halt completely
            return self._generate_mock_candidates(profile_rules, parent_seed, reference_alphas, batch_size)

    def _build_prompt(
        self,
        profile_rules: Dict[str, Any],
        parent_seed: Optional[Dict[str, Any]],
        reference_alphas: Optional[List[Dict[str, Any]]],
        batch_size: int
    ) -> str:
        max_ops = profile_rules.get("max_operators", 8)
        max_fields = profile_rules.get("max_fields", 4)
        
        ref_context = ""
        if reference_alphas:
            ref_context = "\n".join([
                f"- Alpha {a.get('id')}: {a.get('signal_family', 'unknown')} | {a.get('description', '')}"
                for a in reference_alphas[:7]
            ])

        exemplar_context = """PROVEN HIGH-SHARPE WORLDQUANT BRAIN EXEMPLARS (TRAINING EXAMPLES):
- Exemplar 1 (Sharpe 2.55, Fitness 1.87, Ops 5):
  group_neutralize(rank(liabilities / assets) - rank(returns), subindustry);
- Exemplar 2 (Sharpe 1.85, Fitness 1.00, Ops 6):
  group_neutralize(rank(-ts_zscore(returns, 126) / ts_std_dev(returns, 2)), subindustry);
- Exemplar 3 (Sharpe 1.44, Fitness 1.01, Ops 7):
  rev = -ts_decay_linear(ts_zscore(returns, 7), 300);
  vol_filter = volume > ts_mean(volume, 10);
  trade_when(vol_filter, group_rank(rev, subindustry), -1);
- Exemplar 4 (Sharpe 1.30, Fitness 1.17, Ops 7):
  group_neutralize(rank(ts_zscore(operating_income / cap, 126)) - rank(ts_delta(close, 5)), sector);
"""

        prompt = f"""You are the quantitative research engine of Alpha Research Pilot.
Your task is to generate {batch_size} distinct WorldQuant BRAIN Fast Expression alpha candidates.

CRITICAL HARD CONSTRAINTS:
1. MAX OPERATORS: {max_ops} operators per alpha expression. Count every arithmetic operator (+, -, *, /), comparison (<, >, ==), and function call as 1 operator!
2. MAX FIELDS: At most {max_fields} unique data fields per alpha.
3. ALLOWED FIELDS ONLY: {list(CONFIRMED_FIELDS.keys())}
4. FORBIDDEN FIELDS: scl15_sentiment, fam_est_eps_rank (NEVER USE)
5. ALLOWED FUNCTIONS: {list(CONFIRMED_FUNCTIONS)}
6. FORBIDDEN OPERATORS: regression_neut, ts_max (NEVER USE)
7. GROUPING IDENTIFIERS: subindustry, industry, sector
8. VECTOR REDUCTION: nws12_afterhsz_sl MUST be reduced, e.g. vec_avg(nws12_afterhsz_sl)
9. UNIT INTEGRITY: NEVER add a constant directly to price, volume, or dollar fundamentals (e.g. volume * close + 1 is INVALID). Use valid price-range denominators: (high - low + 0.001 * close) or dimensionless ratios.

{exemplar_context}

SELF-CORRELATION DIVERSIFICATION:
Existing submitted alphas exhibit high correlation. Avoid repeating standard short-term reversal or candle cores.
Known submitted alpha families:
{ref_context}

Explore distinct economic mechanisms:
- Volatility skew / term-structure signals
- Earnings / cashflow quality relative to assets or enterprise value
- Volume-weighted liquidity shocks
- Sentimentbuzz interactions

Parent experiment context:
{json.dumps(parent_seed or {}, indent=2)}

Generate valid JSON adhering to the specified schema. Each candidate must have a complete executable Fast Expression ending with a semicolon.
"""
        return prompt

    def _generate_mock_candidates(
        self,
        profile_rules: Dict[str, Any],
        parent_seed: Optional[Dict[str, Any]],
        reference_alphas: Optional[List[Dict[str, Any]]],
        batch_size: int
    ) -> List[GeminiCandidatePayload]:
        """Deterministic, syntactically and rule-valid candidates designed to fit Low-Corr Sprint (<= 8 ops, <= 4 fields)."""
        pool = [
            GeminiCandidatePayload(
                expression="iv_diff = implied_volatility_put_120 - implied_volatility_call_120; -group_zscore(iv_diff, subindustry);",
                economic_hypothesis="Implied volatility skew between put and call options reflects directional hedging pressure; mean-reversion over subindustry captures mispricing.",
                signal_family="Option Skew",
                exact_changed_design_choice="Subindustry z-score of raw IV spread",
                expected_risks="Option liquidity bias and slow pricing updates in smaller caps.",
                estimated_fields=2,
                estimated_operators=3
            ),
            GeminiCandidatePayload(
                expression="ret_dev = ts_std_dev(returns, 10); -rank(ret_dev);",
                economic_hypothesis="Low-volatility anomaly: stocks with lower return dispersion achieve superior risk-adjusted forward returns.",
                signal_family="Low Volatility",
                exact_changed_design_choice="10-day return standard deviation ranked inversely",
                expected_risks="Underperformance during high-beta market rallies.",
                estimated_fields=1,
                estimated_operators=3
            ),
            GeminiCandidatePayload(
                expression="val = cashflow_op / assets; group_rank(val, industry);",
                economic_hypothesis="Cashflow return on assets represents high-quality operational profitability that is rewarded cross-sectionally.",
                signal_family="Fundamental Quality",
                exact_changed_design_choice="Cashflow to assets ratio evaluated by industry rank",
                expected_risks="Quarterly reporting latency and restatements.",
                estimated_fields=2,
                estimated_operators=2
            ),
            GeminiCandidatePayload(
                expression="buzz_signal = vec_avg(nws12_afterhsz_sl) * scl12_buzz; -rank(buzz_signal);",
                economic_hypothesis="High retail buzz accompanied by aftermarket sentiment spikes reflects transient attention overload that mean-reverts.",
                signal_family="Alternative Sentiment",
                exact_changed_design_choice="Product of reduced aftermarket news score and buzz",
                expected_risks="Sporadic coverage for illiquid tickers.",
                estimated_fields=2,
                estimated_operators=4
            ),
            GeminiCandidatePayload(
                expression="p_diff = high - low + 0.001 * close; rank(close / p_diff);",
                economic_hypothesis="Normalizing price by true daily trading range reveals compressed volatility setups prior to directional expansion.",
                signal_family="Range Expansion",
                exact_changed_design_choice="Conservative price range denominator with small regularizer",
                expected_risks="Whipsaws during regime shifts.",
                estimated_fields=3,
                estimated_operators=5
            ),
            GeminiCandidatePayload(
                expression="vol_shock = volume / adv20; -ts_rank(vol_shock, 5);",
                economic_hypothesis="Abnormal trading volume surges indicate institutional turnover that temporarily exhausts short-term liquidity.",
                signal_family="Volume Liquidity",
                exact_changed_design_choice="5-day time series rank of 20-day volume shock",
                expected_risks="Crowding during index rebalancing.",
                estimated_fields=2,
                estimated_operators=3
            ),
        ]
        return pool[:batch_size]

gemini_client = GeminiResearchClient()
