"""SOL/USDT spot scanner and explainable strategy selector; paper signals only."""
import requests
from feature_engine import build_features
from strategy_engine import select_strategy

BASE="https://www.okx.com/api/v5"

def candles(bar="5m",limit=300):
    r=requests.get(BASE+"/market/candles",params={"instId":"SOL-USDT","bar":bar,"limit":str(limit)},timeout=20)
    r.raise_for_status();rows=r.json().get("data",[])
    return [{"ts":int(x[0]),"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4]),"vol":float(x[5])} for x in reversed(rows)]

def current_price():
    r=requests.get(BASE+"/market/ticker",params={"instId":"SOL-USDT"},timeout=20)
    r.raise_for_status();return float(r.json()["data"][0]["last"])

def orderbook_context():
    try:
        r=requests.get(BASE+"/market/books",params={"instId":"SOL-USDT","sz":"20"},timeout=15);r.raise_for_status()
        d=r.json()["data"][0];bids=d.get("bids",[]);asks=d.get("asks",[])
        bid=sum(float(x[1]) for x in bids);ask=sum(float(x[1]) for x in asks)
        bp=float(bids[0][0]);ap=float(asks[0][0]);mid=(bp+ap)/2
        return {"imbalance":(bid-ask)/max(1e-12,bid+ask),"spread_pct":(ap-bp)/mid*100 if mid else 0}
    except Exception:return {"imbalance":0.0,"spread_pct":0.0}

def _regime(cs,cs15,cs1h,cs4h):
    c=[x["c"] for x in cs];rets=[c[i]/c[i-1]-1 for i in range(max(1,len(c)-20),len(c)) if c[i-1]]
    trend=c[-1]/c[-21]-1 if len(c)>=21 and c[-21] else 0
    vol=(sum(x*x for x in rets)/max(1,len(rets)))**0.5
    mtf=[]
    for series in (cs15,cs1h,cs4h):
        vals=[x["c"] for x in series]
        mtf.append(vals[-1]/vals[-5]-1 if len(vals)>=5 and vals[-5] else 0)
    regime="bullish" if trend>0.002 else ("bearish" if trend< -0.002 else "range")
    return {"regime":regime,"trend":round(trend,6),"volatility":round(vol,6),
            "volatility_state":"high" if vol>0.006 else "normal",
            "trend_15m":round(mtf[0],6),"trend_1h":round(mtf[1],6),"trend_4h":round(mtf[2],6)}

def analyze(news_sentiment=0.0):
    cs=candles("5m",300);cs15=candles("15m",120);cs1h=candles("1H",100);cs4h=candles("4H",80)
    price=current_price();book=orderbook_context();context=_regime(cs,cs15,cs1h,cs4h)
    selected,ranked=select_strategy(cs)
    features=build_features(cs,context,book,news_sentiment)
    candidate=None
    if selected:
        candidate={"side":"BUY","entry":price,"tp":price*1.012,"sl":price*0.993,
                   "strategy_name":selected["name"],"strategy_description":selected["description"],
                   "strategy_score":selected["score"],"entry_reason":selected["description"],
                   "timeframe":"5m","features":features,"feature_version":"solana-1200-v2"}
    return price,candidate,features,ranked,context

if __name__=="__main__":
    from signal_manager import SignalManager
    p,c,f,r,m=analyze();SignalManager().cycle(p,c,r,f,m)
