/* Shared, read-only calendar view for the homepage and current report. */
(async function(){
  const script=document.currentScript;
  // Resolve assets from this JavaScript file on home and nested report pages.
  const root=new URL(".",script?.src||document.baseURI).href;
  const earnings=document.getElementById("weeklyEarnings");
  const macro=document.getElementById("weeklyMacro");
  if(!earnings||!macro)return;
  const escapeHTML=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const isoToday=()=>{
    const p=Object.fromEntries(new Intl.DateTimeFormat("en-GB",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date()).map(x=>[x.type,x.value]));
    return p.year+"-"+p.month+"-"+p.day;
  };
  const today=isoToday();
  const d=new Date(today+"T12:00:00Z");
  const dow=(d.getUTCDay()+6)%7;
  const monday=new Date(d.getTime()-dow*86400000);
  const sunday=new Date(monday.getTime()+6*86400000);
  const iso=x=>x.toISOString().slice(0,10);
  const begin=iso(monday),end=iso(sunday);
  const timeLocal=value=>{
    if(!value)return"南澳公布時間待確認";
    const parsed=new Date(value);
    return Number.isNaN(parsed.getTime())?"南澳時間待確認":
      new Intl.DateTimeFormat("zh-TW",{timeZone:"Australia/Adelaide",month:"2-digit",day:"2-digit",weekday:"short",hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).format(parsed)+"（南澳）";
  };
  const mark=value=>value==="official"?"官方日期確認":value==="reported"?"已發布・數值待核":"來源日曆預告・待核IR";
  const safeLink=(url,label)=>{
    if(!/^https:\/\//.test(url||""))return"";
    return ' <a href="'+escapeHTML(url)+'" target="_blank" rel="noopener noreferrer">'+escapeHTML(label)+" ↗</a>";
  };
  const block=rows=>'<div class="calRows">'+rows.join("")+"</div>";
  const released=x=>x.result_status==="published" && Array.isArray(x.results) && x.results.some(v=>v.actual!=null);
  const eventPassed=x=>{
    if(!x.datetime_et)return false;
    const t=new Date(x.datetime_et).getTime();
    return Number.isFinite(t)&&Date.now()>=t;
  };
  const renderMacro=x=>{
    const done=released(x);
    const passed=eventPassed(x);
    const tag=done?"已公布":passed?"已到公布時間・待核實":x.impact==="高"?"重要・待公布":"關注・待公布";
    const resultHtml=done?
      '<div class="calResults">'+x.results.map(v=>
        '<div class="calResult"><strong>'+escapeHTML(v.indicator||x.title)+'</strong>'+
        '<div>實際 <b>'+escapeHTML(v.actual)+'</b> · 預期 '+escapeHTML(v.forecast||"未取得")+
        ' · 前值 '+escapeHTML(v.previous||"未取得")+'</div></div>').join("")+'</div>'+
      '<div class="calMuted">數據發布：'+escapeHTML(timeLocal(x.datetime_et))+
      safeLink(x.result_source_url||x.source_url,"官方實際數據")+
      (x.forecast_source_url?safeLink(x.forecast_source_url,"預期值來源"):"")+'</div>'
      :'<div class="calMuted">'+escapeHTML(timeLocal(x.datetime_et))+'</div>'+
       (passed?'<div class="calMuted">預定發布時刻已過，尚未取得可核實的實際數據；不可視為未公布。</div>':"");
    return '<article class="calEvent"><div><strong>'+escapeHTML(x.date.slice(5))+' · '+escapeHTML(x.title)+
      '</strong><span class="calTag">'+tag+'</span></div>'+resultHtml+
      '<div class="calMuted">觀察：'+escapeHTML(x.focus||"市場反應")+
      safeLink(x.source_url,"官方日曆")+'</div></article>';
  };
  const heading='<p class="calIntro">美東事件日 '+escapeHTML(begin)+" 至 "+escapeHTML(end)+"；以下時間另換算南澳。未確認的公布時刻不會推算。</p>";
  const hasFallback=!!(earnings.querySelector(".calEvent")||macro.querySelector(".calEvent"));
  // Display verified build-time data immediately; do not blank it on refresh.
  if(!hasFallback){
    earnings.innerHTML=heading+"<p class=\"calMuted\">正在載入已核實的財報清單…</p>";
    macro.innerHTML=heading+"<p class=\"calMuted\">正在載入官方財經事件…</p>";
  }
  try{
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),12000);
    let r;
    try{r=await fetch(root+"weekly-calendar.json?v="+Date.now(),{cache:"no-store",signal:controller.signal});}
    finally{clearTimeout(timeout)}
    if(!r.ok)throw Error("HTTP "+r.status);
    const c=await r.json();
    const e=(c.earnings||[]).filter(x=>x.date>=begin&&x.date<=end)
      .sort((a,b)=>a.date.localeCompare(b.date)||b.priority-a.priority);
    const m=(c.economic||[]).filter(x=>x.date>=begin&&x.date<=end)
      .sort((a,b)=>a.date.localeCompare(b.date)||String(a.datetime_et).localeCompare(String(b.datetime_et)));
    earnings.innerHTML=heading+(e.length?block(e.map(x=>
      '<article class="calEvent"><div><strong>'+escapeHTML(x.date.slice(5))+' · '+escapeHTML(x.symbol)+'</strong> '+escapeHTML(x.name)+
      '<span class="calTag">'+mark(x.status)+'</span></div><div>'+escapeHTML(x.time_label||"公布時段待核實")+
      '</div><div class="calMuted">'+(x.datetime_et?escapeHTML(timeLocal(x.datetime_et))+
      (x.event_type==="call"?"（會議時間，非發布時間）":""):"南澳發布時刻待確認")+
      '</div><div class="calMuted">重點：'+escapeHTML(x.focus||"財測、CapEx、毛利")+
      safeLink(x.source_url,"來源")+"</div></article>")):
      '<p class="calMuted">本週尚無已收錄的財報時間；不代表沒有公司發布。請查官方 IR 或 Nasdaq 行事曆。</p>');
    macro.innerHTML=heading+(m.length?block(m.map(renderMacro)):
      '<p class="calMuted">這一週目前沒有已收錄的重要官方事件；請查看完整官方行事曆。</p>');
    const foot='<p class="calFoot">已核實基準：'+escapeHTML(c.as_of||"未註明")+
      '。未列出的財報不代表沒有公布；排程可能臨時改期。'+safeLink("https://www.nasdaq.com/market-activity/earnings","更多財報")+'</p>';
    earnings.innerHTML+=foot;
    macro.innerHTML+='<p class="calFoot">'+safeLink("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm","Fed")+
      ' · '+safeLink("https://www.bls.gov/schedule/","BLS")+
      ' · '+safeLink("https://www.bea.gov/news/schedule/","BEA")+"</p>";
    try{
      const status=await fetch(root+"weekly-calendar-status.json?t="+Date.now(),{cache:"no-store"});
      if(status.ok){
        const s=await status.json(),label=s.last_scan_at?
          "來源掃描："+(s.status==="success"?"已完成":"部分來源失敗")+
          "；有些財報可能尚未經官方確認。":"自動資料來源尚未首次掃描；顯示人工核對事件。";
        earnings.innerHTML+='<p class="calFoot">'+escapeHTML(label)+"</p>";
      }
    }catch(_){}
  }catch(_){
    if(hasFallback){
      earnings.insertAdjacentHTML("afterbegin",'<p class="calFoot">即時更新暫時失敗；目前顯示已發布的最後一份資料。</p>');
      macro.insertAdjacentHTML("afterbegin",'<p class="calFoot">即時更新暫時失敗；目前顯示已發布的最後一份資料。</p>');
    }else{
      earnings.innerHTML=heading+'<p class="calMuted">財報資料暫時無法載入。'+safeLink("https://www.nasdaq.com/market-activity/earnings","查看財報日曆")+"</p>";
      macro.innerHTML=heading+'<p class="calMuted">總經日曆資料暫時無法載入。'+safeLink("https://www.bls.gov/schedule/","查看 BLS")+"</p>";
    }
  }
})();
