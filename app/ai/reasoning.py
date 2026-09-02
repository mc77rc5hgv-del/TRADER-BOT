"""AI Reasoning Layer (TZ section 7, step 4 of the build sequence in section
13). Orchestrates the deterministic engines' output into a compressed
context, asks the LLM only for the WHY narrative, and assembles the final
AnalysisResult — the LLM never contributes a number to this object."""

from __future__ import annotations

from app.ai.context import build_context
from app.ai.prompt import SYSTEM_PROMPT, build_user_prompt
from app.ai.provider import LLMProvider, LLMUsage
from app.ai.schemas import AnalysisNarrative, AnalysisResult
from app.probability.schemas import ProbabilityResult
from app.risk.schemas import RiskLevels
from app.ta.schemas import TechnicalSnapshot

DISCLAIMER = "⚠️ Это вероятностный анализ, а не финансовая рекомендация. Проверяйте риски самостоятельно."


async def analyze(
    provider: LLMProvider,
    symbol: str,
    tf: str,
    snapshot: TechnicalSnapshot,
    probability: ProbabilityResult,
    risk: RiskLevels | None,
) -> tuple[AnalysisResult, LLMUsage]:
    context = build_context(symbol, tf, snapshot, probability, risk)
    narrative, usage = await provider.generate_structured(
        SYSTEM_PROMPT, build_user_prompt(context), AnalysisNarrative
    )

    result = AnalysisResult(
        symbol=symbol,
        tf=tf,
        structure_bias=snapshot.structure_bias,
        scenarios=context.scenarios,
        entry_low=context.entry_low,
        entry_high=context.entry_high,
        invalidation=context.invalidation,
        targets=context.targets,
        risk_reward=context.risk_reward,
        why=narrative.why,
        disclaimer=DISCLAIMER,
    )
    return result, usage
