#!/usr/bin/env python3
"""Update weekly calendars. SEC/IR-confirmed rows remain intact; provider rows are labeled."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ET=ZoneInfo("America/New_York")
AU=ZoneInfo("Australia/Adelaide")
SELECTION={
 "NVDA","AMD","AVGO","MRVL","SMCI","TSM","MU","WDC","STX",
 "ANET","LITE","COHR","CIEN","VRT","ETN","BE","FLNC","EOSE",
 "MSFT","ORCL","GOOGL","AMZN","META","NET","NOW","APP",
 "RKLB","LRCX","KLAC","AMAT","TXN","TSLA","IBM","NFLX",
 "DELL","CRWV","MOD","AAOI","ALAB","VICR","GEV","PWR",
 "VST","NBIS","IREN","SNDK"
}
HIGH_MACRO={
 "consumer price index":("美國 CPI 通膨","高","利率預期與估值"),
 "employment situation":("美國非農就業報告","高","非農、失業率與薪資"),
 "producer price index":("美國 PPI 生產者物價","中","上游通膨與毛利"),
 "employment cost index":("就業成本指數 ECI","高","薪資與服務通膨"),
 "job openings and labor turnover":("美國 JOLTS 職缺","中","勞動需求"),
 "import and export price indexes":("美國進出口價格","中","輸入型通膨"),
}
def request(url,accept="application/json"):
    headers={
      "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept":accept,"Accept-Language":"en-US,en;q=0.9",
      "Origin":"https://www.nasdaq.com"
    }
    with urlopen(Request(url,headers=headers),timeout=20) as response:
        return response.read(8000000)

def market_dates(now):
    local=now.astimezone(ET).date()
    start=local-dt.timedelta(days=local.weekday())
    return [start+dt.timedelta(days=n) for n in range(14)]

def nasdaq_results(payload,date):
    body=json.loads(payload)
    data=body.get("data") or {}
    if not isinstance(data,dict) or not isinstance(data.get("rows"),list):
        raise ValueError("Nasdaq payload has no rows: do not assume zero earnings")
    rows=[]
    for row in data["rows"]:
        symbol=(row.get("symbol") or "").strip().upper()
        if symbol not in SELECTION:continue
        name=re.sub(r"<[^>]*>","",row.get("name") or symbol).strip()
        period=(row.get("time") or "").strip().lower()
        session=("BMO" if "pre" in period or "before" in period else
                 "AMC" if "after" in period else "unknown")
        rows.append({
          "symbol":symbol,"name":name,"date":date.isoformat(),
          "session":session,"event_type":"estimate","datetime_et":None,
          "time_label":"Nasdaq 日曆預告"+("（盤前）" if session=="BMO" else "（盤後）" if session=="AMC" else "（未確認時段）"),
          "focus":"確認營收、指引、訂單、CapEx 與毛利",
          "priority":2,"status":"provider_unverified",
          "source_url":"https://www.nasdaq.com/market-activity/earnings",
        })
    return rows

def unfold_ics(blob):
    lines=[]
    for line in blob.decode("utf-8-sig",errors="replace").replace("\r\n","\n").split("\n"):
        if line.startswith((" ","\t")) and lines:lines[-1]+=line[1:]
        else:lines.append(line)
    events=[];obj=None
    for line in lines:
        if line=="BEGIN:VEVENT":obj={}
        elif line=="END:VEVENT" and obj is not None:
            events.append(obj);obj=None
        elif obj is not None and ":" in line:
            key,value=line.split(":",1);obj[key]=value
    return events

def bls_events(blob,now):
    rows=[]
    earliest=now.astimezone(ET).date()-dt.timedelta(days=1)
    latest=earliest+dt.timedelta(days=65)
    for entry in unfold_ics(blob):
        title=entry.get("SUMMARY","").replace("\\, ",", ").replace("\\, ",",")
        recognized=next((v for k,v in HIGH_MACRO.items() if k in title.lower()),None)
        if not recognized:continue
        stamp=next(((k,v) for k,v in entry.items() if k.startswith("DTSTART")),None)
        if not stamp:continue
        key,value=stamp
        match=re.search(r"\d{8}T\d{6}Z?",value)
        if not match:continue
        raw=match.group()
        parsed=dt.datetime.strptime(raw[:15],"%Y%m%dT%H%M%S")
        if raw.endswith("Z"):parsed=parsed.replace(tzinfo=dt.timezone.utc).astimezone(ET)
        else:parsed=parsed.replace(tzinfo=ET)
        if not earliest<=parsed.date()<=latest:continue
        cn,impact,focus=recognized
        rows.append({
          "id":"bls-"+parsed.date().isoformat()+"-"+re.sub(r"\W+","-",cn.lower()),
          "date":parsed.date().isoformat(),"datetime_et":parsed.isoformat(),
          "title":cn,"impact":impact,"focus":focus,"status":"official",
          "source_url":"https://www.bls.gov/schedule/news_release/bls.ics"})
    return rows

def execute(now=None,root=ROOT,fetch=request):
    now=now or dt.datetime.now(dt.timezone.utc)
    data_path=root/"weekly-calendar.json"
    status_path=root/"weekly-calendar-status.json"
    doc=json.loads(data_path.read_text(encoding="utf-8"))
    existing=doc.get("earnings",[])
    manual=[v for v in existing if v.get("status")=="official"]
    previous=[v for v in existing if v.get("status")=="provider_unverified"]
    errors=[];scraped=[];ok=0
    for date in market_dates(now)[:10]:
        if date.weekday()>4:continue
        url="https://api.nasdaq.com/api/calendar/earnings?"+urlencode({"date":date.isoformat()})
        try:
            scraped+=nasdaq_results(fetch(url),date)
            ok+=1
        except Exception as exc:errors.append(f"Nasdaq {date}: {type(exc).__name__}")
    # Manual verified dates always win when the provider disagrees.
    manual_symbols={r["symbol"] for r in manual
                    if r.get("date","")>=now.astimezone(ET).date().isoformat()}
    new_entries=[r for r in scraped if r["symbol"] not in manual_symbols]
    latest={(r["symbol"],r["date"]):r for r in previous}
    if ok:latest.update({(r["symbol"],r["date"]):r for r in new_entries})
    lower=(now.astimezone(ET).date()-dt.timedelta(days=7)).isoformat()
    cutoff=(now.astimezone(ET).date()+dt.timedelta(days=22)).isoformat()
    provider=[v for v in latest.values() if lower<=v["date"]<=cutoff]
    doc["earnings"]=sorted(manual+provider,key=lambda r:(r["date"],-r.get("priority",1),r["symbol"]))
    bls_ok=False
    try:
        fresh=bls_events(fetch("https://www.bls.gov/schedule/news_release/bls.ics","text/calendar"),now)
        old=[v for v in doc.get("economic",[]) if not v.get("id","").startswith("bls-")]
        existing_ids={(v["date"],v["title"]) for v in old}
        doc["economic"]=sorted(old+[v for v in fresh if (v["date"],v["title"]) not in existing_ids],
                                key=lambda r:(r["date"],r.get("datetime_et") or ""))
        bls_ok=True
    except Exception as exc:errors.append(f"BLS feed: {type(exc).__name__}")
    status={"last_scan_at":now.isoformat(),"status":"success" if ok==10 and bls_ok else "partial",
            "earnings_provider":"Nasdaq 日曆（日期需再核公司 IR）",
            "earnings_provider_ok":bool(ok),"nasdaq_days_ok":ok,"nasdaq_days_total":10,
            "bls_ok":bls_ok,"notes":errors[:12]}
    doc["last_scan_at"]=now.isoformat()
    data_path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Calendar: Nasdaq {ok}/10, BLS={bls_ok}, earnings={len(doc['earnings'])}, macro={len(doc['economic'])}")
    return status

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--adelaide-9am",action="store_true")
    args=parser.parse_args()
    current=dt.datetime.now(dt.timezone.utc)
    if args.adelaide_9am and current.astimezone(AU).hour!=9:
        print("skip alternate UTC slot")
    else:
        execute(current)
