"""One complete SOL/USDT research cycle."""
import json, os, time
from solana_engine import analyze
from signal_manager import SignalManager, read, write
from news_engine import fetch_news, sentiment_score
from ai_model import train

def main():
    price,candidate=analyze()
    news=fetch_news()
    state=read()
    # Keep news intelligence and counters in the persisted state.
    state["news_items"]=news[:250]
    state["news_sentiment"]=sentiment_score(news)
    state["news_updated_at"]=int(time.time())
    write(state)
    SignalManager().cycle(price,candidate)
    state=read()
    closed=state.get("history",[])
    # Label only fully closed outcomes; defer model fitting until sufficient samples exist.
    labels=[1 if x.get("status")=="TP" else 0 for x in closed if x.get("status") in ("TP","SL")]
    rows=[list((x.get("features") or {}).values()) for x in closed if x.get("status") in ("TP","SL")]
    if rows and len(rows)==len(labels):
        result=train(rows,labels)
        state["last_training"]=result
        write(state)
    print(json.dumps({"cycle":state["cycle"],"price":price,"open":bool(state.get("open_signal")),"news":len(news)}))
if __name__=="__main__":main()
