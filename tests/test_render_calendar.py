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
    def test_published_actuals_and_pending_status(self):
        now=dt.datetime(2026,10,22,3,30,tzinfo=dt.timezone.utc)
        events=[
            {"date":"2026-10-20","datetime_et":"2026-10-20T08:30:00-04:00",
             "title":"已發布住房資料","result_status":"published",
             "results":[{"indicator":"新屋開工","actual":"122.1 萬戶","forecast":"130.0 萬戶","previous":"128.8 萬戶"}],
             "result_source_url":"https://www.census.gov/construction/nrc/current/"},
            {"date":"2026-10-20","datetime_et":"2026-10-20T10:00:00-04:00",
             "title":"逾期未核對","impact":"中"},
            {"date":"2026-10-22","datetime_et":"2026-10-22T08:30:00-04:00",
             "title":"未來公布","impact":"高"}
        ]
        panel=r.calendar_panels({"economic":events,"earnings":[]},{},now)["weeklyMacro"]
        self.assertIn("122.1 萬戶",panel)
        self.assertIn("130.0 萬戶",panel)
        self.assertIn("128.8 萬戶",panel)
        self.assertIn("官方實際數據",panel)
        self.assertIn("已到公布時間・待核實",panel)
        self.assertIn("重要・待公布",panel)
        self.assertEqual(panel.count("已公布"),1)
        self.assertNotIn("讀取中",panel)

    def test_missing_panels_raise(self):
        with self.assertRaisesRegex(ValueError,"Missing calendar placeholder"):
            r.render_html("<div></div>",{},{})

if __name__=="__main__":
    unittest.main()
