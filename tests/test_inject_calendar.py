import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/"scripts"/"inject_calendar.py"
spec=importlib.util.spec_from_file_location("inject_calendar",p)
i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)

class TestCalendarInjection(unittest.TestCase):
 def test_new_report(self):
  html="<html><head><style>section{margin:1px}</style></head><body><main><header><h1>Today</h1></header><section>report</section></main></body></html>"
  new=i.inject(html)
  self.assertIn('id="weeklyEarnings"',new)
  self.assertIn('id="weeklyMacro"',new)
  self.assertIn("../../../weekly-calendar.js",new)
  self.assertEqual(i.inject(new),new)
 def test_existing_report_unchanged(self):
  html='<div id="weeklyEarnings"></div><div id="weeklyMacro"></div>'
  self.assertEqual(i.inject(html),html)
if __name__=="__main__":unittest.main()
