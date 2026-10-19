#!/usr/bin/env python3
"""Embed dynamic weekly panels into the NEWEST HTML market report at deploy time.
Does not rewrite source reports or retroactively change older published reports.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CSS=".calIntro,.calMuted,.calFoot{opacity:.76;font-size:.87rem}.calEvent{padding:11px;margin:9px 0;border:1px solid rgba(125,135,155,.36);border-radius:11px;font-size:.9rem}.calEvent>div+div{margin-top:3px}.calTag{display:inline-block;background:rgba(130,145,165,.22);padding:2px 6px;margin:0 5px;border-radius:7px;font-size:.73rem}.calFoot{font-size:.77rem}.calEvent a{text-decoration:underline}"
PANELS='<section><h2>本週財報發布｜目前最新動態</h2><p class="muted">每次開啟顯示目前本週，不代表本報原始發布時已知。</p><div id="weeklyEarnings">讀取中…</div></section><section><h2>重大財經日曆｜目前最新動態</h2><div id="weeklyMacro">讀取中…</div></section>'

def inject(html,relative="../../../"):
    if 'id="weeklyEarnings"' in html and 'id="weeklyMacro"' in html:return html
    if "</body>" not in html:return html
    if re.search(r"</header\s*>",html,re.I):
        html=re.sub(r"</header\s*>",lambda m:m.group(0)+PANELS,html,count=1,flags=re.I)
    else:
        html=html.replace("<main>", "<main>"+PANELS,1)
    if "</style>" in html:html=html.replace("</style>",CSS+"</style>",1)
    return html.replace("</body>",
        f'<script src="{relative}weekly-calendar.js" data-root="{relative}" defer></script></body>',1)

def main(root=ROOT):
    files=sorted((root/"reports").glob("????/??/????-??-??.html"))
    if not files:raise SystemExit("No dated reports found")
    latest=files[-1]
    original=latest.read_text(encoding="utf-8")
    changed=inject(original)
    if changed!=original:latest.write_text(changed,encoding="utf-8")
    print(f"Latest report calendar applied: {latest.relative_to(root)}")

if __name__=="__main__":main()
