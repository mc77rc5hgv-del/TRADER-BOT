from __future__ import annotations

from app.ai.scenarios import split_scenarios
from app.ai.schemas import AnalysisContext
from app.probability.schemas import ProbabilityResult
from app.risk.schemas import RiskLevels
from app.ta.schemas import TechnicalSnapshot


def build_context(
    symbol: str,
    tf: str,
    snapshot: TechnicalSnapshot,
    probability: ProbabilityResult,
    risk: RiskLevels | None,
) -> AnalysisContext:
    return AnalysisContext(
        symbol=symbol,
        tf=tf,
        price=snapshot.price,
        structure_bias=snapshot.structure_bias,
        rsi=snapshot.rsi,
        volume_trend=snapshot.volume_trend,
        nearest_support=snapshot.nearest_support,
        nearest_resistance=snapshot.nearest_resistance,
        scenarios=split_scenarios(probability),
        entry_low=risk.entry_low if risk else None,
        entry_high=risk.entry_high if risk else None,
        invalidation=risk.invalidation if risk else None,
        targets=risk.targets if risk else None,
        risk_reward=risk.risk_reward if risk else None,
        factors=probability.factors,
    )
