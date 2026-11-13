"""
Correlation Breaker Engine for Alpha Research Pilot.
Calibrated against WorldQuant BRAIN platform rules and recipes verified in alpha-harness.

When an alpha encounters PROD_CORRELATION_CHECK failure (Pearson >= 0.70 with a production alpha),
this engine re-shapes the alpha's expression while preserving locked simulation settings (USA TOP3000,
delay 1, decay 0, subindustry neutralization).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Grouping fields that do NOT count toward unique data field limits (verified by BRAIN measurement)
GROUPING_FIELDS = {
    "market",
    "sector",
    "industry",
    "subindustry",
    "country",
    "exchange",
    "currency",
    "split",
    "adjfactor",
}

ALPHA_BINDING = "alpha"

@dataclass(frozen=True)
class BreakerRecipe:
    id: str
    name: str
    rationale: str
    setup: Tuple[str, ...]
    tail: str
    operators: Tuple[str, ...]
    fields: Tuple[str, ...]
    caution: str = ""

# The 10 calibrated platform recipes from alpha-harness
RECIPES: Tuple[BreakerRecipe, ...] = (
    BreakerRecipe(
        id="resid_returns",
        name="Residualize against daily returns",
        rationale="Regresses the signal on daily returns over 63 trading days (1 quarter) and keeps only the residual.",
        setup=(),
        tail=f"ts_regression({ALPHA_BINDING}, returns, 63, rettype = 0)",
        operators=("ts_regression",),
        fields=("returns",),
        caution="Residuals have higher turnover day-to-day; monitor turnover bounds.",
    ),
    BreakerRecipe(
        id="resid_size",
        name="Residualize against market capitalization",
        rationale="Regresses the signal on log(cap) over 252 days (1 year) to remove size bias across time.",
        setup=(),
        tail=f"ts_regression({ALPHA_BINDING}, log(cap), 252, rettype = 0)",
        operators=("ts_regression", "log"),
        fields=("cap",),
    ),
    BreakerRecipe(
        id="neut_momentum",
        name="Orthogonalize against short-term momentum",
        rationale="Projects out 5-day price momentum using vector_neut.",
        setup=(),
        tail=f"vector_neut({ALPHA_BINDING}, ts_delta(close, 5))",
        operators=("vector_neut", "ts_delta"),
        fields=("close",),
    ),
    BreakerRecipe(
        id="neut_size",
        name="Orthogonalize against market capitalization",
        rationale="Projects out log market cap to remove the most common crowded exposure.",
        setup=(),
        tail=f"vector_neut({ALPHA_BINDING}, log(cap))",
        operators=("vector_neut", "log"),
        fields=("cap",),
    ),
    BreakerRecipe(
        id="neut_both",
        name="Orthogonalize against size and momentum, then smooth",
        rationale="Removes both size and momentum vectors, then smooths with ts_decay_linear to control turnover.",
        setup=(
            f"no_size = vector_neut({ALPHA_BINDING}, log(cap))",
            "orthogonal = vector_neut(no_size, ts_delta(close, 5))",
        ),
        tail="ts_decay_linear(orthogonal, 3)",
        operators=("vector_neut", "log", "ts_delta", "ts_decay_linear"),
        fields=("cap", "close"),
        caution="Orthogonalizing lifts turnover; decay keeps it within acceptable platform bounds.",
    ),
    BreakerRecipe(
        id="fast_innovation",
        name="Trade the innovation instead of level",
        rationale="Subtracts 20-day time-series average using ts_av_diff to trade new signal arrival.",
        setup=(),
        tail=f"ts_av_diff({ALPHA_BINDING}, 20)",
        operators=("ts_av_diff",),
        fields=(),
    ),
    BreakerRecipe(
        id="event_gate",
        name="Trade only on volume catalysts",
        rationale="Holds portfolio weights between abnormal volume days (volume > 1.25 * adv20).",
        setup=("catalyst = volume > 1.25 * adv20",),
        tail=f"trade_when(catalyst, {ALPHA_BINDING}, -1)",
        operators=("trade_when",),
        fields=("volume", "adv20"),
        caution="Gating reduces turnover; ensure turnover stays above the 1% platform floor.",
    ),
    BreakerRecipe(
        id="cluster_country",
        name="Neutralize inside country and industry clusters",
        rationale="Double neutralization across country and industry groups.",
        setup=("cluster = densify(group_cartesian_product(industry, country))",),
        tail=f"group_neutralize({ALPHA_BINDING}, cluster)",
        operators=("densify", "group_cartesian_product", "group_neutralize"),
        fields=("industry", "country"),
    ),
    BreakerRecipe(
        id="cluster_zscore",
        name="Group z-score inside sector and size clusters",
        rationale="Evaluates instruments against peers in the same sector and market cap tercile.",
        setup=(
            'cap_bucket = bucket(rank(cap), buckets = "0.33, 0.66")',
            "cluster = densify(group_cartesian_product(sector, cap_bucket))",
        ),
        tail=f"group_zscore({ALPHA_BINDING}, cluster)",
        operators=("bucket", "rank", "densify", "group_cartesian_product", "group_zscore"),
        fields=("cap", "sector"),
    ),
    BreakerRecipe(
        id="cluster_volatility",
        name="Neutralize inside sector and volatility clusters",
        rationale="Neutralizes within groups formed by sector and 63-day realized volatility buckets.",
        setup=(
            'vol_bucket = bucket(rank(ts_std_dev(returns, 63)), buckets = "0.33, 0.66")',
            "cluster = densify(group_cartesian_product(sector, vol_bucket))",
        ),
        tail=f"group_neutralize({ALPHA_BINDING}, cluster)",
        operators=(
            "bucket",
            "rank",
            "ts_std_dev",
            "densify",
            "group_cartesian_product",
            "group_neutralize",
        ),
        fields=("returns", "sector"),
    ),
)


class CorrelationBreaker:
    """Transforms an expression using calibrated correlation-breaking recipes."""

    @staticmethod
    def wrap_expression(base_expression: str, recipe: BreakerRecipe) -> str:
        """
        Wraps a base alpha expression in a recipe.
        Format:
          alpha = <base_expression>;
          [setup line 1];
          [setup line 2];
          <tail_expression>
        """
        clean_expr = base_expression.strip().rstrip(";")
        lines = [f"{ALPHA_BINDING} = {clean_expr}"]
        for step in recipe.setup:
            lines.append(step)
        lines.append(recipe.tail)
        return ";\n".join(lines)

    @classmethod
    def generate_candidate_variants(cls, base_expression: str) -> List[Dict[str, Any]]:
        """
        Generates all 10 recipe variants for an expression.
        Returns recipe metadata, generated code, and expected operators/fields.
        """
        variants = []
        for recipe in RECIPES:
            transformed = cls.wrap_expression(base_expression, recipe)
            variants.append({
                "recipe_id": recipe.id,
                "recipe_name": recipe.name,
                "rationale": recipe.rationale,
                "caution": recipe.caution,
                "expression": transformed,
                "added_operators": list(recipe.operators),
                "added_fields": list(recipe.fields),
            })
        return variants
