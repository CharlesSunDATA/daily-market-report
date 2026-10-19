#!/usr/bin/env python3
"""Daily discovery. Trusted headlines are UNVERIFIED leads; SEC filings verify metadata only."""
import argparse
import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
UTC=dt.timezone.utc
PUBLISHERS={"reuters.com":"Reuters","apnews.com":"Associated Press","bloomberg.com":"Bloomberg",
            "ft.com":"Financial Times","wsj.com":"Wall Street Journal","cnbc.com":"CNBC",
            "prnewswire.com":"PR Newswire","businesswire.com":"Business Wire",
            "globenewswire.com":"GlobeNewswire"}
# Never use ambiguous short tickers as free-text matches.
ALIASES={
"NVDA":["Nvidia"],"AMD":["Advanced Micro Devices"],"AVGO":["Broadcom"],"MRVL":["Marvell"],
"SMCI":["Super Micro Computer"],"TSM":["TSMC","Taiwan Semiconductor"],"MU":["Micron"],
"SKHY":["SK Hynix"],"WDC":["Western Digital"],"STX":["Seagate"],
"ANET":["Arista Networks"],"LITE":["Lumentum"],"COHR":["Coherent Corp"],"CIEN":["Ciena"],
"AOSL":["Alpha and Omega Semiconductor"],"NVTS":["Navitas Semiconductor"],"VICR":["Vicor"],
"ON":["onsemi","ON Semiconductor"],"POWI":["Power Integrations"],"MPWR":["Monolithic Power Systems"],
"VSH":["Vishay"],"DIOD":["Diodes Incorporated"],"STM":["STMicroelectronics"],"WOLF":["Wolfspeed"],
"VRT":["Vertiv"],"ETN":["Eaton Corporation"],"GEV":["GE Vernova"],"BE":["Bloom Energy"],
"VST":["Vistra"],"PWR":["Quanta Services"],"FLNC":["Fluence Energy"],"EOSE":["Eos Energy"],
"MSFT":["Microsoft"],"ORCL":["Oracle"],"GOOGL":["Alphabet","Google"],"AMZN":["Amazon"],
"META":["Meta Platforms"],"NET":["Cloudflare"],"DDOG":["Datadog"],"CFLT":["Confluent"],
"NOW":["ServiceNow"],"APP":["AppLovin"],"RKLB":["Rocket Lab"],"SPCX":["SpaceX","Starship","Starlink"],
"LNG":["Cheniere Energy"],"WMB":["Williams Companies"],"SMH":["VanEck Semiconductor ETF"],
"SOXX":["iShares Semiconductor ETF"],"SOXQ":["Invesco PHLX Semiconductor ETF"],
"QQQ":["Invesco QQQ"],"SPY":["SPDR S&P 500"],"XLK":["Technology Select Sector SPDR"],
"IGV":["iShares Expanded Tech-Software"],"XLE":["Energy Select Sector SPDR"]}
MATERIAL=re.compile(
r"\b(earnings|quarterly results|annual results|revenue|guidance|forecast|outlook|"
r"contract|deal|agreement|orders?|backlog|merger|acquisition|acquire|production|"
r"manufacturing|factory|capacity|expansion|shipment|financing|debt|credit|default|"
r"bankruptcy|bond|capex|capital expenditure|export controls?|restrictions?|tariffs?|"
r"regulation|investigation|approval|buyback|repurchase|dividend|layoffs?|"
r"restructuring|data center power|hyperscaler|launch contract|supply agreement|"
r"funding|joint venture|investment)\b",re.I)
SEC_ITEMS={"1.01":"重大合約","1.02":"重大合約終止","2.01":"收購或資產處分",
           "2.02":"財報／業績","2.05":"重組費用","2.06":"資產減損"}

def get(url):
    agent="DailyMarketWatchlist/1.0 (https://github.com/CharlesSunDATA/daily-market-report)"
    with urlopen(Request(url,headers={"User-Agent":agent,"Accept":"application/json, application/rss+xml, */*"}),timeout=22) as r:
        return r.read(10000000)

class ParseGroups(HTMLParser):
    def __init__(self):
        super().__init__();self.groups=[];self.depth=0;self.heading=False;self.ticker=False
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if tag=="div" and not self.depth and "group" in a.get("class","").split():
            self.depth=1;self.groups.append({"title":"","tickers":[]})
        elif self.depth:
            if tag=="div":self.depth+=1
            if tag=="h3":self.heading=True
            if tag=="span" and "tick" in a.get("class","").split():self.ticker=True
    def handle_endtag(self,tag):
        if self.depth:
            if tag=="h3":self.heading=False
            if tag=="span":self.ticker=False
            if tag=="div":self.depth-=1
    def handle_data(self,data):
        if self.depth and self.heading:self.groups[-1]["title"]+=data
        if self.depth and self.ticker:self.groups[-1]["tickers"].append(data.strip())

def read_groups(root):
    p=ParseGroups();p.feed((root/"watchlist.html").read_text(encoding="utf8"))
    groups=[g for g in p.groups if g["tickers"]]
    if len(groups)!=11:raise ValueError(f"Expected 11 groups, got {len(groups)}")
    return groups

def publisher_from(url):
    h=(urlparse(url).hostname or "").lower().rstrip(".")
    return next((name for domain,name in PUBLISHERS.items() if h==domain or h.endswith("."+domain)),None)

def tickers_in(text,symbols):
    found=[]
    for t in symbols:
        if any(re.search(r"(?<!\w)"+re.escape(alias)+r"(?!\w)",text,re.I) for alias in ALIASES.get(t,[])):
            found.append(t)
        elif len(t)>=3 and t not in {"APP","NOW","NET","SPY"} and re.search(
            r"\("+re.escape(t)+r"\)|\$"+re.escape(t)+r"\b",text,re.I):
            found.append(t)
    return found

def rss_query(group):
    names=[ALIASES.get(t,[t])[0] for t in group["tickers"]]
    query="("+" OR ".join('"'+n+'"' for n in names)+") (earnings OR guidance OR contract OR acquisition OR financing OR capacity OR debt) when:3d"
    return "https://news.google.com/rss/search?"+urlencode({"q":query,"hl":"en-US","gl":"US","ceid":"US:en"})

def parse_news(data,group,now):
    found=[];cutoff=now-dt.timedelta(days=4)
    for article in ET.fromstring(data).findall(".//channel/item"):
        origin=article.find("source")
        publisher=publisher_from(origin.get("url","")) if origin is not None else None
        link=(article.findtext("link") or "").strip()
        try:published=email.utils.parsedate_to_datetime(article.findtext("pubDate") or "").astimezone(UTC)
        except (TypeError,ValueError):continue
        if not (publisher and link.startswith("https://news.google.com/") and cutoff<=published<=now+dt.timedelta(hours=2)):continue
        title=html.unescape((article.findtext("title") or "").strip())
        origin_name=(origin.text or "").strip()
        title=re.sub(r"\s+-\s+"+re.escape(origin_name)+r"$","",title,flags=re.I).strip()
        symbols=tickers_in(title,group["tickers"])
        if not symbols or not MATERIAL.search(title):continue
        normalized=re.sub(r"\W+"," ",title).lower().strip()
        key="news:"+hashlib.sha256((normalized+":"+publisher).encode()).hexdigest()[:18]
        found.append({
            "id":key,"dedupe_key":key,"timestamp":published.isoformat(),"light":"🟡",
            "group":group["title"],"tickers":symbols,"title":"【媒體待核實】"+title,
            "summary":f"Fact（來源報導）：{publisher} 於 {published.date()} 刊出此消息。"
                      "Inference：屬重大事件關鍵字匹配線索，尚未核對公司原文、"
                      "財務影響或市場預期，不能視為已確認利多／利空。",
            "source":publisher+"（Google News RSS）","source_url":link,
            "source_time":published.isoformat(),"first_seen_at":now.isoformat(),
            "verification":"publisher_attributed_unverified"})
    return found

def sec_records(groups,now):
    mapping=json.loads(get("https://www.sec.gov/files/company_tickers.json"))
    lookup={x["ticker"].upper():(int(x["cik_str"]),x["title"]) for x in mapping.values()}
    targets={}
    for g in groups:
        for t in g["tickers"]:
            if t in lookup:targets.setdefault(t,(lookup[t],g["title"]))
    found=[];checked=0;errors=[]
    cutoff=now.date()-dt.timedelta(days=4)
    for ticker,((cik,company),group) in targets.items():
        try:
            rec=json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))["filings"]["recent"]
            checked+=1
            for i,form in enumerate(rec["form"]):
                if form!="8-K":continue
                filed=dt.date.fromisoformat(rec["filingDate"][i])
                if filed<cutoff:continue
                items=(rec.get("items") or [""]*len(rec["form"]))[i] or ""
                types=[label for code,label in SEC_ITEMS.items() if re.search(r"\b"+re.escape(code)+r"\b",items)]
                if not types:continue
                accession=rec["accessionNumber"][i]
                url=(f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                     f"{accession.replace('-','')}/{quote(rec['primaryDocument'][i])}")
                key="sec:"+accession
                found.append({
                    "id":key,"dedupe_key":key,"timestamp":dt.datetime.combine(filed,dt.time(18),UTC).isoformat(),
                    "light":"🟡","group":group,"tickers":[ticker],
                    "title":ticker+" 提交 SEC 8-K："+"、".join(types),
                    "summary":f"Fact：{company} 於 {filed} 提交 SEC 8-K，涉及 {items} 項。"
                              "Inference：目前只核對文件類別，合約金額、營收及估值影響仍需閱讀原文。",
                    "source":"U.S. SEC EDGAR","source_url":url,"source_time":str(filed),
                    "first_seen_at":now.isoformat(),"verification":"official_filing_metadata"})
        except Exception as exc:errors.append(f"SEC {ticker}: {type(exc).__name__}")
        time.sleep(.14)
    return found,checked,len(targets),errors

def update(now=None,root=ROOT,fetch=get,sec_fetch=sec_records,schedule=False):
    now=now or dt.datetime.now(UTC)
    if schedule and now.astimezone(ZoneInfo("Australia/Adelaide")).hour!=9:
        print("Skip non-09:00 Adelaide cron");return 0
    groups=read_groups(root);source=root/"watchlist-signals.json";status_file=root/"watchlist-status.json"
    old=json.loads(source.read_text(encoding="utf8"))
    prev=json.loads(status_file.read_text(encoding="utf8")) if status_file.exists() else {}
    rows=[];errors=[];rss_ok=0
    for group in groups:
        try:rows+=parse_news(fetch(rss_query(group)),group,now);rss_ok+=1
        except Exception as exc:errors.append(f"RSS {group['title']}: {type(exc).__name__}")
    try:
        sec,sec_ok,sec_total,sec_errors=sec_fetch(groups,now)
        rows+=sec;errors+=sec_errors
    except Exception as exc:
        sec_ok=sec_total=0;errors.append(f"SEC index: {type(exc).__name__}")
    if rss_ok==0 and sec_ok==0:
        raise RuntimeError("All news and SEC sources unavailable; history was not changed.")
    known={x.get("dedupe_key") or x.get("id") for x in old.get("signals",[])}
    fresh=[]
    for row in sorted(rows,key=lambda x:x["timestamp"],reverse=True):
        if row["dedupe_key"] not in known:known.add(row["dedupe_key"]);fresh.append(row)
    if fresh:
        old["signals"]=sorted(fresh+old.get("signals",[]),key=lambda x:x["timestamp"],reverse=True)[:500]
        old["updated_at"]=now.isoformat()
        source.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    complete=(rss_ok==len(groups) and sec_ok==sec_total and not errors)
    status={"last_scan_at":now.isoformat(),
            "last_success_at":now.isoformat() if complete else prev.get("last_success_at"),
            "status":"success" if complete else "partial",
            "rss_feeds_ok":rss_ok,"rss_feeds_total":len(groups),
            "sec_issuers_ok":sec_ok,"sec_issuers_total":sec_total,
            "new_signals":len(fresh),"errors":errors[:15],
            "note":"新聞是待核實線索；SEC只確認文件分類，不構成投資建議。"}
    status_file.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(f"scan={status['status']}, RSS={rss_ok}/{len(groups)}, SEC={sec_ok}/{sec_total}, new={len(fresh)}")
    return len(fresh)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--adelaide-9am",action="store_true")
    args=parser.parse_args()
    update(schedule=args.adelaide_9am)
