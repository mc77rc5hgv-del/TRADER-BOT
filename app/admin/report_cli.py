"""Internal admin report (TZ section 11). Run with `python -m app.admin.report_cli`.

Prints cost/DAU/conversion figures to stdout - deliberately just a script,
not a web endpoint, since no admin auth exists yet and this is meant to be
run by someone with direct access to the deployment, not exposed publicly."""

from __future__ import annotations

import asyncio

from app.admin.analytics import (
    ActivityReport,
    ConversionReport,
    CostReport,
    compute_activity_report,
    compute_conversion_report,
    compute_cost_report,
)
from app.db.session import async_session_factory


def _print_cost_report(report: CostReport) -> None:
    print(f"\n=== AI cost (last {report.window_days} days) ===")
    print(f"Total: ${report.total_cost_usd:.2f} across {report.total_requests} requests")
    if report.latency_p50_ms is not None:
        print(f"Latency p50/p95: {report.latency_p50_ms:.0f}ms / {report.latency_p95_ms:.0f}ms")
    if report.by_day:
        print("\nBy day:")
        for row in report.by_day:
            print(f"  {row.day}: ${row.cost_usd:.2f} ({row.requests} requests)")
    if report.top_users:
        print("\nTop users by cost:")
        for row in report.top_users:
            print(f"  user {row.user_id}: ${row.cost_usd:.2f} ({row.requests} requests)")


def _print_activity_report(report: ActivityReport) -> None:
    print("\n=== Activity ===")
    print(f"DAU: {report.dau}")
    print(f"WAU: {report.wau}")


def _print_conversion_report(report: ConversionReport) -> None:
    print("\n=== Free -> Pro conversion ===")
    print(f"Total users: {report.total_users}")
    print(f"Active PRO users: {report.active_pro_users}")
    if report.conversion_rate is not None:
        print(f"Conversion rate: {report.conversion_rate:.1f}%")
    print(f"Churned in last {report.churn_window_days} days: {report.churned_in_window}")


async def main() -> None:
    async with async_session_factory() as session:
        cost_report = await compute_cost_report(session)
        activity_report = await compute_activity_report(session)
        conversion_report = await compute_conversion_report(session)

    _print_cost_report(cost_report)
    _print_activity_report(activity_report)
    _print_conversion_report(conversion_report)
    print()


if __name__ == "__main__":
    asyncio.run(main())
