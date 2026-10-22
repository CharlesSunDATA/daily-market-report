import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("render_calendar", ROOT/"scripts"/"render_calendar.py")
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class StaticCalendarTests(unittest.TestCase):
    def test_week_and_fallback_data(self):
        doc=json.loads((ROOT/"weekly-calendar.json").read_text(encoding="utf-8"))
        now=dt.datetime(2026,10,22,0,0,tzinfo=dt.timezone.utc)
        panels=r.calendar_panels(doc,{},now)
        self.assertIn("META",panels["weeklyEarnings"])
        self.assertIn("初領失業救濟金",panels["weeklyMacro"])
        self.assertNotIn("讀取中",panels["weeklyEarnings"])
        self.assertNotIn("讀取中",panels["weeklyMacro"])
    def test_replaces_both_panels_and_escapes_html(self):
        doc={"as_of":"test","earnings":[{"date":"2026-10-22","symbol":"T","name":"<unsafe>","status":"official"}],"economic":[]}
        now=dt.datetime(2026,10,22,tzinfo=dt.timezone.utc)
        html='<div id="weeklyEarnings">讀取中…</div><div id="weeklyMacro">讀取中…</div>'
        result=r.render_html(html,doc,{},now)
        self.assertIn("&lt;unsafe&gt;",result)
        self.assertNotIn("讀取中",result)
    def test_missing_panels_raise(self):
        with self.assertRaisesRegex(ValueError,"Missing calendar placeholder"):
            r.render_html("<div></div>",{},{})

if __name__=="__main__":
    unittest.main()
