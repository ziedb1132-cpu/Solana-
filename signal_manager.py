"""Persistent SOL paper-signal lifecycle. No time-based exits and no live orders."""
import json, os, time
STATE="solana_state.json"
FEE_PCT=float(os.getenv("PAPER_FEE_PCT","0.10"))
SLIPPAGE_PCT=float(os.getenv("PAPER_SLIPPAGE_PCT","0.05"))
def read():
    try:
        with open(STATE,encoding="utf-8") as f:s=json.load(f)
    except (OSError,ValueError):s={"cycle":0,"total_signals":0,"tp_count":0,"sl_count":0,"open_signal":None,"history":[]}
    s.setdefault("history",[]);s.setdefault("total_signals",len(s["history"]))
    s.setdefault("tp_count",sum(1 for x in s["history"] if x.get("status")=="TP"))
    s.setdefault("sl_count",sum(1 for x in s["history"] if x.get("status")=="SL"))
    s.setdefault("open_signal",None);s.setdefault("strategy_stats",{})
    return s
def write(s):
    tmp=STATE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:json.dump(s,f,ensure_ascii=False,separators=(",",":"))
    os.replace(tmp,STATE)
def _close(a,status,price,now,s):
    entry=float(a.get("entry",price));gross=(price/entry-1)*100 if entry else 0.0
    net=gross-(2*FEE_PCT)-SLIPPAGE_PCT
    a.update(status=status,exit_price=price,closed_at=now,gross_return_pct=round(gross,5),
             fees_pct=2*FEE_PCT,slippage_pct=SLIPPAGE_PCT,net_return_pct=round(net,5),close_reason=status)
    s["history"].append(a)
    if status=="TP":s["tp_count"]+=1
    else:s["sl_count"]+=1
    stats=s.setdefault("strategy_stats",{}).setdefault(a.get("strategy_name","BASELINE"),{"trades":0,"wins":0,"losses":0,"net_return_pct":0.0})
    stats["trades"]+=1;stats["wins" if net>0 else "losses"]+=1
    stats["net_return_pct"]=round(stats["net_return_pct"]+net,5)
class SignalManager:
    def cycle(self,price,candidate=None,ranked_strategies=None,features=None,market_context=None):
        s=read();s["cycle"]+=1;now=int(time.time());a=s.get("open_signal")
        if a:
            a.setdefault("original_tp",a.get("tp"));a.setdefault("original_sl",a.get("sl"))
            if price>=float(a["tp"]):_close(a,"TP",price,now,s);s["open_signal"]=None
            elif price<=float(a["sl"]):_close(a,"SL",price,now,s);s["open_signal"]=None
            elif price>float(a.get("high_water",a["entry"])):
                old=float(a["sl"]);a["high_water"]=price;proposed=price*0.993
                if proposed>old:
                    trail_log=a.setdefault("risk_history",[])
                    trail_log.append({"at":now,"price":price,"sl_old":old,"sl_new":proposed,"reason":"trailing_stop_tightened"})
                    a.update(sl_old=old,sl=proposed,sl_new=proposed,sl_updated_at=now,
                             change_reason="trailing_stop_tightened",trailing_updates=int(a.get("trailing_updates",0))+1)
        if not s.get("open_signal") and candidate and candidate.get("side")=="BUY":
            s["total_signals"]+=1;entry=float(candidate.get("entry",price))
            tp=float(candidate.get("tp",entry*1.012));sl=float(candidate.get("sl",entry*0.993))
            s["open_signal"]={"id":s["total_signals"],"symbol":"SOL-USDT","side":"BUY","entry":entry,"tp":tp,"sl":sl,
              "original_tp":tp,"original_sl":sl,"tp_old":None,"tp_new":tp,"sl_old":None,"sl_new":sl,
              "high_water":entry,"opened_at":now,"status":"OPEN","features":features or candidate.get("features",{}),
              "feature_version":candidate.get("feature_version","solana-1200-v2"),
              "strategy_name":candidate.get("strategy_name","BASELINE_MOMENTUM"),
              "strategy_description":candidate.get("strategy_description","Fast average above slow average with positive candle momentum"),
              "strategy_score":float(candidate.get("strategy_score",50)),"ai_win_probability":candidate.get("ai_win_probability"),
              "entry_reason":candidate.get("entry_reason","Bullish SOL/USDT setup"),"timeframe":candidate.get("timeframe","5m"),
              "market_regime":(market_context or {}).get("regime","unknown"),"opened_price":price,"trailing_updates":0}
        s["price"]=price;s["updated_at"]=now;s["ranked_strategies"]=(ranked_strategies or [])[:20]
        s["market_context"]=market_context or {}
        write(s);self.write_summary(s)
    def write_summary(self,s):
        a=s.get("open_signal")
        closed=[x for x in s.get("history",[]) if x.get("status") in ("TP","SL")]
        net_values=[float(x.get("net_return_pct",0) or 0) for x in closed]
        profitable=sum(1 for x in net_values if x>0)
        summary={"price":s.get("price"),"current_price":s.get("price"),"closed_signals":len(closed),
          "net_profit_pct":round(sum(net_values),5),"win_rate_pct":round(100*profitable/len(net_values),2) if net_values else None,
          "total_signals":s["total_signals"],
          "tp_count":s["tp_count"],"sl_count":s["sl_count"],"cycle":s["cycle"],"updated_at":s.get("updated_at"),
          "open_signal":a,"strategy_count":len(s.get("ranked_strategies",[])),"top_strategies":s.get("ranked_strategies",[])[:20],
          "feature_count":1205,"ai_gate":s.get("ai_gate",{}),"last_training":s.get("last_training",{}),
          "market_context":s.get("market_context",{})}
        tmp="solana_summary.json.tmp"
        with open(tmp,"w",encoding="utf-8") as f:json.dump(summary,f,ensure_ascii=False,separators=(",",":"))
        os.replace(tmp,"solana_summary.json")
