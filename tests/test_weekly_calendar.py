import datetime as dt
import importlib.util
import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo
path=Path(__file__).resolve().parents[1]/"scripts"/"update_weekly_calendar.py"
spec=importlib.util.spec_from_file_location("weekly",path)
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class CalendarTests(unittest.TestCase):
 def test_nasdaq_format(self):
  body=json.dumps({"data":{"rows":[{"symbol":"NVDA","name":"NVIDIA","time":"time-after-hours"},{"symbol":"XYZ","name":"Other","time":"unknown"}]}}).encode()
  rows=u.nasdaq_results(body,dt.date(2026,10,21))
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["session"],"AMC")
  self.assertEqual(rows[0]["status"],"provider_unverified")
 def test_invalid_payload_not_empty(self):
  with self.assertRaises(ValueError):u.nasdaq_results(b'{"data":null}',dt.date(2026,10,21))
 def test_bls_ics_timezone(self):
  ics=b'''BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20261106T083000
SUMMARY:Employment Situation for October 2026
END:VEVENT
END:VCALENDAR'''
  rows=u.bls_events(ics,dt.datetime(2026,10,20,tzinfo=dt.timezone.utc))
  self.assertEqual(rows[0]["datetime_et"],"2026-11-06T08:30:00-05:00")
 def test_calendar_dates(self):
  now=dt.datetime(2026,10,20,tzinfo=dt.timezone.utc)
  self.assertEqual(u.market_dates(now)[0],dt.date(2026,10,19))
 def test_seed_sources(self):
  d=json.loads((path.parents[1]/"weekly-calendar.json").read_text())
  self.assertTrue(all(v["source_url"].startswith("https://") for v in d["earnings"]+d["economic"]))
  self.assertTrue(any(v["symbol"]=="META" for v in d["earnings"]))
if __name__=="__main__":unittest.main()
