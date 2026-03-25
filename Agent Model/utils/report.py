from analyzers.base import DiagnosticReport, Finding

SEVERITY_ICONS = {
    "high": "\U0001f534",    # Red circle
    "medium": "\U0001f7e0",  # Orange circle
    "low": "\U0001f7e1",     # Yellow circle
}


def format_report(report: DiagnosticReport) -> str:
    """Format a DiagnosticReport as markdown for Streamlit display."""
    lines = [f"### {report.summary}", ""]

    if not report.findings:
        return "\n".join(lines)

    # Group findings by category
    categories: dict[str, list[Finding]] = {}
    for f in report.findings:
        categories.setdefault(f.category, []).append(f)

    for category, findings in categories.items():
        lines.append(f"**{category}**")
        for f in findings:
            icon = SEVERITY_ICONS.get(f.severity, "")
            loc = f" _{f.location}_" if f.location else ""
            lines.append(f"- {icon} {f.description}{loc}")
        lines.append("")

    return "\n".join(lines)
