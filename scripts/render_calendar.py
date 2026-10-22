#!/usr/bin/env python3
"""Render a useful server-side weekly calendar in published HTML.

The browser refreshes it when JavaScript is available, but never depends on
JavaScript or an external provider to display the verified data already saved.
"""
from datetime import datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ET = ZoneInfo("America/New_York")
ADELAIDE = ZoneInfo("Australia/Adelaide")


def h(value):
    return escape(str(value if value is not None else ""), quote=True)


def week_bounds(now):
    date = now.astimezone(ET).date()
    start = date - timedelta(days=date.weekday())
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


def source(url, label="來源"):
    if not isinstance(url, str) or not url.startswith("https://"):
        return ""
    return ' <a href="' + h(url) + '" target="_blank" rel="noopener noreferrer">' + h(label) + ' ↗</a>'


def adelaide_time(value):
    if not value:
        return "南澳公布時刻待確認"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return "南澳時間待確認"
        return parsed.astimezone(ADELAIDE).strftime("%m/%d %H:%M") + "（南澳）"
    except (ValueError, TypeError):
        return "南澳時間待確認"


def calendar_panels(doc, status=None, now=None):
    now = now or datetime.now(timezone.utc)
    start, end = week_bounds(now)
    heading = '<p class="calIntro">美東事件日 ' + h(start) + " 至 " + h(end) + '；時間已轉南澳。</p>'
    earnings = sorted((x for x in doc.get("earnings", [])
                       if start <= x.get("date", "") <= end),
                      key=lambda x: (x["date"], -x.get("priority", 0)))
    economic = sorted((x for x in doc.get("economic", [])
                       if start <= x.get("date", "") <= end),
                      key=lambda x: (x["date"], str(x.get("datetime_et") or "")))
    def earning_card(x):
        label = "官方已確認" if x.get("status") == "official" else "來源日曆／待核IR"
        local = adelaide_time(x.get("datetime_et"))
        if x.get("event_type") == "call" and x.get("datetime_et"):
            local += "（電話會議，非發布時間）"
        return ('<article class="calEvent"><div><strong>' +
                h(x.get("date", "")[5:]) + " · " + h(x.get("symbol", "")) +
                "</strong> " + h(x.get("name", "")) + '<span class="calTag">' +
                label + '</span></div><div>' + h(x.get("time_label", "公布時段待核實")) +
                '</div><div class="calMuted">' + h(local) +
                '</div><div class="calMuted">重點：' + h(x.get("focus", "")) +
                source(x.get("source_url")) + '</div></article>')
    def economic_card(x):
        return ('<article class="calEvent"><div><strong>' +
                h(x.get("date", "")[5:]) + " · " + h(x.get("title", "")) +
                '</strong><span class="calTag">' +
                ("重要" if x.get("impact") == "高" else "關注") +
                '</span></div><div>' + h(adelaide_time(x.get("datetime_et"))) +
                '</div><div class="calMuted">觀察：' + h(x.get("focus", "")) +
                source(x.get("source_url"), "官方日曆") + '</div></article>')
    e = (heading + '<div class="calRows">' +
         "".join(earning_card(x) for x in earnings) + '</div>' if earnings else
         heading + '<p class="calMuted">本週尚無已收錄的財報；請核實公司 IR。</p>')
    m = (heading + '<div class="calRows">' +
         "".join(economic_card(x) for x in economic) + '</div>' if economic else
         heading + '<p class="calMuted">本週尚無已收錄的重大事件。</p>')
    e += '<p class="calFoot">資料基準：' + h(doc.get("as_of", "未註明")) + '。' + source("https://www.nasdaq.com/market-activity/earnings", "更多財報") + '</p>'
    scan = (status or {}).get("last_scan_at")
    if scan:
        e += '<p class="calFoot">來源最近掃描：' + h(scan) + '；未經公司 IR 確認的日期仍屬預告。</p>'
    else:
        e += '<p class="calFoot">自動來源尚未完成掃描；目前為已儲存的來源清單。</p>'
    m += '<p class="calFoot">' + source("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "Fed") + ' · ' + source("https://www.bls.gov/schedule/", "BLS") + ' · ' + source("https://www.bea.gov/news/schedule/", "BEA") + '</p>'
    return {"weeklyEarnings": e, "weeklyMacro": m}


def render_html(html, doc, status=None, now=None):
    for element_id, content in calendar_panels(doc, status, now).items():
        placeholder = 'id="' + element_id + '">讀取中…</div>'
        if placeholder not in html:
            raise ValueError("Missing calendar placeholder: " + element_id)
        html = html.replace(placeholder,
                            'id="' + element_id + '">' + content + '</div>', 1)
    return html


def main(root=ROOT, now=None):
    doc = json.loads((root / "weekly-calendar.json").read_text(encoding="utf-8"))
    status = json.loads((root / "weekly-calendar-status.json").read_text(encoding="utf-8"))
    pages = [root / "index.html"]
    reports = sorted((root / "reports").glob("????/??/????-??-??.html"))
    if reports:
        pages.append(reports[-1])
    for page in pages:
        html = page.read_text(encoding="utf-8")
        page.write_text(render_html(html, doc, status, now), encoding="utf-8")
        print("Pre-rendered weekly calendars:", page.relative_to(root))


if __name__ == "__main__":
    main()
