"""Persistent paper signal manager. No time-based exit by design."""
import json, os, time
STATE="solana_state.json"
def read():
    try:
        with open(STATE,encoding="utf-8") as f:return json.load(f)
    except (OSError,ValueError):return {"cycle":0,"total_signals":0,"tp_count":0,"sl_count":0,"open_signal":None,"history":[]}
def write(s):
    with open(STATE,"w",encoding="utf-8") as f:json.dump(s,f,ensure_ascii=False,separators=(",",":"))
class SignalManager:
    def cycle(self,price,candidate=None):
        s=read();s["cycle"]+=1; now=int(time.time())
        a=s.get("open_signal")
        if a:
            # Long-only price exits; no timeout exit.
            if price>=a["tp"]:
                a.update(status="TP",exit_price=price,closed_at=now);s["tp_count"]+=1;s["history"].append(a);s["open_signal"]=None
            elif price<=a["sl"]:
                a.update(status="SL",exit_price=price,closed_at=now);s["sl_count"]+=1;s["history"].append(a);s["open_signal"]=None
            elif price>a.get("high_water",a["entry"]):
                old=a["sl"];a["high_water"]=price
                # Tighten stop in a one-way manner as price advances.
                proposed=price*0.993
                if proposed>old:
                    a["sl_old"]=old;a["sl"]=proposed;a["sl_updated_at"]=now;a["change_reason"]="trailing"
        if not s.get("open_signal") and candidate and candidate.get("side")=="BUY":
            s["total_signals"]+=1
            s["open_signal"]={"id":s["total_signals"],"side":"BUY","entry":candidate["entry"],"tp":candidate["tp"],"sl":candidate["sl"],"tp_old":None,"sl_old":None,"high_water":candidate["entry"],"opened_at":now,"status":"OPEN"}
        s["price"]=price;s["updated_at"]=now
        write(s);self.write_summary(s)
    def write_summary(self,s):
        a=s.get("open_signal")
        summary={"price":s.get("price"),"total_signals":s["total_signals"],"tp_count":s["tp_count"],"sl_count":s["sl_count"],"cycle":s["cycle"],"updated_at":s.get("updated_at"),"open_signal":a}
        with open("solana_summary.json","w",encoding="utf-8") as f:json.dump(summary,f,ensure_ascii=False,separators=(",",":"))
