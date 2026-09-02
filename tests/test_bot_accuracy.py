from app.ai.schemas import AccuracyBreakdownRow, AccuracyReport
from app.bot.handlers.accuracy import NO_DATA_TEXT, _render_report


def test_render_report_no_data() -> None:
    report = AccuracyReport(
        window_days=30,
        total_predictions=0,
        resolved_predictions=0,
        win_rate=None,
        avg_realized_r=None,
        by_symbol=[],
        by_tf=[],
    )

    assert _render_report(report) == NO_DATA_TEXT


def test_render_report_includes_win_rate_and_breakdowns() -> None:
    report = AccuracyReport(
        window_days=30,
        total_predictions=10,
        resolved_predictions=8,
        win_rate=62.5,
        avg_realized_r=0.8,
        by_symbol=[AccuracyBreakdownRow(key="BTCUSDT@binance", total_predictions=5, win_rate=60.0)],
        by_tf=[AccuracyBreakdownRow(key="1h", total_predictions=10, win_rate=None)],
    )

    text = _render_report(report)

    assert "10" in text
    assert "62%" in text or "63%" in text  # rounding of 62.5
    assert "BTCUSDT@binance" in text
    assert "1h" in text
    assert "нет оценённых" in text
