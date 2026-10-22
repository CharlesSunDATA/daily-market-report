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

    def test_published_earnings_consensus_and_guidance(self):
        now=dt.datetime(2026,10,22,5,0,tzinfo=dt.timezone.utc)
        earnings=[
            {"date":"2026-10-21","symbol":"META","name":"Meta","result_status":"published",
             "results":[{"indicator":"營收（USD）","actual":"$64.60B","forecast":"$64.57B",
                         "previous":"$51.24B","surprise":"+0.05%"},
                        {"indicator":"EPS（GAAP）","actual":"$3.83","forecast":None}],
             "guidance":"Q4 指引 73–76B","result_note":"GAAP 與調整 EPS 不可混用",
             "result_source_url":"https://example.com/ir",
             "consensus_source_url":"https://example.com/consensus"},
            {"date":"2026-10-20","symbol":"XYZ","name":"Unverified Report",
             "time_label":"date estimated","status":"provider_unverified"},
            {"date":"2026-10-23","symbol":"WDC","name":"Upcoming Report",
             "status":"official","time_label":"盤後"}
        ]
        html=r.calendar_panels({"earnings":earnings,"economic":[]},{},now)["weeklyEarnings"]
        self.assertIn("已公布・數據核實",html)
        self.assertIn("預期 $64.57B",html)
        self.assertIn("差異 <b>+0.05%</b>",html)
        self.assertIn("未取得同口徑預期",html)
        self.assertIn("Q4 指引",html)
        self.assertIn("正式財報",html)
        self.assertIn("預期來源",html)
        self.assertIn("日期已過・結果待核實",html)
        self.assertIn("公司確認日期・待公布",html)
        self.assertNotIn("讀取中",html)

    def test_real_earnings_rows_have_source_and_actual(self):
        doc=json.loads((ROOT/"weekly-calendar.json").read_text(encoding="utf-8"))
        published=[x for x in doc["earnings"] if x.get("result_status")=="published"]
        self.assertGreaterEqual(len(published),8)
        self.assertTrue(all(x["result_source_url"].startswith("https://") for x in published))
        self.assertTrue(all(x["results"] and all(v.get("actual") for v in x["results"]) for x in published))
        self.assertTrue(all("indicator" in v for x in published for v in x["results"]))
        self.assertTrue(all(v.get("surprise") is None or v.get("forecast") for x in published for v in x["results"]))

    def test_missing_panels_raise(self):
        with self.assertRaisesRegex(ValueError,"Missing calendar placeholder"):
            r.render_html("<div></div>",{},{})

if __name__=="__main__":
    unittest.main()
