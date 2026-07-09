from __future__ import annotations

from pathlib import Path


DEFAULT_WORKFLOW_PATH = Path(".github") / "workflows" / "radar-scan.yml"


def write_github_action(
    output_path: Path = DEFAULT_WORKFLOW_PATH,
    cron: str = "0 */12 * * *",
    include_linkedin: bool = False,
    include_facebook: bool = False,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(github_action_yaml(cron, include_linkedin, include_facebook), encoding="utf-8")
    return output_path


def github_action_yaml(cron: str, include_linkedin: bool = False, include_facebook: bool = False) -> str:
    scan_command = scheduled_scan_command(include_linkedin, include_facebook)
    return f"""name: Internship Radar Scan

on:
  schedule:
    - cron: "{cron}"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run career scan
        env:
          RADAR_SMTP_USERNAME: ${{{{ secrets.RADAR_SMTP_USERNAME }}}}
          RADAR_SMTP_PASSWORD: ${{{{ secrets.RADAR_SMTP_PASSWORD }}}}
          RADAR_EMAIL_FROM: ${{{{ secrets.RADAR_EMAIL_FROM }}}}
          RADAR_EMAIL_TO: ${{{{ secrets.RADAR_EMAIL_TO }}}}
          SERPAPI_API_KEY: ${{{{ secrets.SERPAPI_API_KEY }}}}
          META_GRAPH_ACCESS_TOKEN: ${{{{ secrets.META_GRAPH_ACCESS_TOKEN }}}}
        run: |
          {scan_command}
"""


def scheduled_scan_command(include_linkedin: bool = False, include_facebook: bool = False) -> str:
    args = ["python", "-m", "radar", "scan", "--notify"]
    if include_linkedin:
        args.append("--include-linkedin")
    if include_facebook:
        args.append("--include-facebook")
    return " ".join(args)


def local_schedule_hint(
    every_hours: int = 12,
    include_linkedin: bool = False,
    include_facebook: bool = False,
) -> str:
    powershell_command = scheduled_scan_command(include_linkedin, include_facebook)
    return f"""Windows Task Scheduler:
schtasks /Create /SC HOURLY /MO {every_hours} /TN InternshipRadar /TR "{powershell_command}"

cron:
0 */{every_hours} * * * cd /path/to/mailsmth && {powershell_command}
"""
