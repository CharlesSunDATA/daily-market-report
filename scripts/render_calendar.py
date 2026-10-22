#!/usr/bin/env python3
"""Render a useful server-side weekly calendar in published HTML.

The browser refreshes it when JavaScript is available, but never depends on
JavaScript or an external provider to display the verified data already saved.
"""
from datetime import datetime, timedelta, timezone
from html import escape
import json
import re
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
        values = x.get("results") or []
        verified = (x.get("result_status") == "published" and
                    any(v.get("actual") is not None for v in values))
        timestamp = x.get("datetime_et")
        past = x.get("date", "") < now.astimezone(ET).date().isoformat()
        if timestamp:
            try:
                event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if event_time.tzinfo is not None and event_time <= now:
                    past = True
            except (ValueError, TypeError):
                pass
        label = ("已公布・數據核實" if verified else
                 "日期已過・結果待核實" if past else
                 "公司確認日期・待公布" if x.get("status") == "official" else
                 "預告・待核IR")
        intro = ('<article class="calEvent"><div><strong>' +
                 h(x.get("date", "")[5:]) + " · " + h(x.get("symbol", "")) +
                 "</strong> " + h(x.get("name", "")) +
                 '<span class="calTag">' + label + '</span></div>')
        if verified:
            rows = []
            for v in values:
                last = v.get("previous")
                prefix = "前季" if last and "前季" in str(last) else "去年同期"
                rows.append(
                    '<div class="calResult"><strong>' + h(v.get("indicator", "")) +
                    '</strong><div>實際 <b>' + h(v.get("actual")) +
                    '</b> · 預期 ' + h(v.get("forecast") or "未取得同口徑預期") +
                    (" · " + prefix + " " + h(last) if last else "") +
                    (" · 差異 <b>" + h(v["surprise"]) + "</b>" if v.get("surprise") else "") +
                    "</div></div>")
            body = '<div class="calResults">' + "".join(rows) + "</div>"
            if x.get("guidance"):
                body += '<div class="calMuted"><strong>財測／關鍵：</strong>' + h(x["guidance"]) + "</div>"
            if x.get("result_note"):
                body += '<div class="calMuted">' + h(x["result_note"]) + "</div>"
            body += ('<div class="calMuted">' +
                     source(x.get("result_source_url") or x.get("source_url"), "正式財報") +
                     source(x.get("consensus_source_url"), "預期來源") + "</div>")
        else:
            local = adelaide_time(timestamp)
            if x.get("event_type") == "call" and timestamp:
                local += "（電話會議，非財報發布時刻）"
            body = ('<div>' + h(x.get("time_label", "公布日期預告")) + '</div>' +
                    '<div class="calMuted">' + h(local) + "</div>")
            if past:
                body += ('<div class="calMuted">該日期已過，但尚未取得可核實的數字；'
                         '不代表公司未發布。</div>')
            body += ('<div class="calMuted">重點：' + h(x.get("focus", "")) +
                     source(x.get("source_url")) + "</div>")
        return intro + body + "</article>"
    def economic_card(x):
        actual_rows = x.get("results", [])
        verified = x.get("result_status") == "published" and any(
            r.get("actual") is not None for r in actual_rows)
        timestamp = x.get("datetime_et")
        past = False
        if timestamp:
            try:
                published_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                past = published_time.tzinfo is not None and published_time <= now
            except (ValueError, TypeError):
                pass
        tag = ("已公布" if verified else "已到公布時間・待核實"
               if past else "重要・待公布" if x.get("impact") == "高"
               else "關注・待公布")
        intro = ('<article class="calEvent"><div><strong>' +
                 h(x.get("date", "")[5:]) + " · " + h(x.get("title", "")) +
                 '</strong><span class="calTag">' + tag + '</span></div>')
        if verified:
            results = '<div class="calResults">' + "".join(
                '<div class="calResult"><strong>' + h(v.get("indicator", x.get("title", ""))) +
                '</strong><div>實際 <b>' + h(v.get("actual")) +
                '</b> · 預期 ' + h(v.get("forecast") or "未取得") +
                ' · 前值 ' + h(v.get("previous") or "未取得") +
                '</div></div>' for v in actual_rows) + '</div>'
            results += ('<div class="calMuted">數據發布：' + h(adelaide_time(timestamp)) +
                        source(x.get("result_source_url") or x.get("source_url"), "官方實際數據") +
                        source(x.get("forecast_source_url"), "預期值來源") + '</div>')
        else:
            results = '<div class="calMuted">' + h(adelaide_time(timestamp)) + '</div>'
            if past:
                results += ('<div class="calMuted">預定發布時刻已過，尚未取得可核實的'
                            '實際數據；不可視為未公布。</div>')
        return (intro + results +
                '<div class="calMuted">觀察：' + h(x.get("focus", "")) +
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
        # Existing reports use different Chinese loading messages. Replace the
        # initial text in the exact calendar container without touching HTML nearby.
        pattern = r'(id="' + re.escape(element_id) + r'">)[^<]*(</div>)'
        html, count = re.subn(pattern, lambda m: m.group(1) + content + m.group(2),
                              html, count=1)
        if count != 1:
            raise ValueError("Missing calendar placeholder: " + element_id)
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
