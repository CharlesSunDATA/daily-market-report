import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("watchlist",Path(__file__).resolve().parents[1]/"scripts"/"update_watchlist.py")
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
NOW=dt.datetime(2026,10,20,tzinfo=dt.timezone.utc)
XML=b'''<rss><channel><item><title>Nvidia raises guidance - Reuters</title>
<source url="https://www.reuters.com">Reuters</source>
<link>https://news.google.com/rss/articles/1</link>
<pubDate>Mon, 19 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Nvidia raises guidance - Untrusted</title>
<source url="https://evil.example">Untrusted</source>
<link>https://news.google.com/rss/articles/2</link>
<pubDate>Mon, 19 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Nvidia shares rise - Reuters</title>
<source url="https://www.reuters.com">Reuters</source>
<link>https://news.google.com/rss/articles/3</link>
<pubDate>Mon, 19 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'''

class Tests(unittest.TestCase):
    def test_domain_allowlist(self):
        self.assertEqual(u.publisher_from("https://www.reuters.com"),"Reuters")
        self.assertIsNone(u.publisher_from("https://reuters.com.evil.example"))
    def test_ambiguous_symbols(self):
        self.assertEqual(u.tickers_in("You must BE ready",["BE"]),[])
        self.assertEqual(u.tickers_in("Bloom Energy signs a deal",["BE"]),["BE"])
    def test_material_news(self):
        rows=u.parse_news(XML,{"title":"AI","tickers":["NVDA"]},NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["light"],"🟡")
        self.assertIn("待核實",rows[0]["title"])
    def test_11_groups_and_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            r.joinpath("watchlist.html").write_text(
                '<div class="group"><h3>AI</h3><div><span class="tick">NVDA</span></div></div>'*11,encoding="utf8")
            r.joinpath("watchlist-signals.json").write_text('{"signals":[]}',encoding="utf8")
            fetch=lambda _:XML;sec=lambda g,n:([],1,1,[])
            self.assertEqual(u.update(NOW,r,fetch,sec),1)
            self.assertEqual(u.update(NOW,r,fetch,sec),0)
            self.assertEqual(len(json.loads(r.joinpath("watchlist-signals.json").read_text())["signals"]),1)
            self.assertEqual(json.loads(r.joinpath("watchlist-status.json").read_text())["status"],"success")

if __name__=="__main__":unittest.main()
