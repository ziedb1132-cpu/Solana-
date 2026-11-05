"""SOL/USDT spot scanner and paper-signal generator (no live orders)."""
import os, time, requests
from signal_manager import SignalManager
from feature_engine import build_features

BASE="https://www.okx.com/api/v5"
def candles(limit=300):
    r=requests.get(BASE+"/market/candles",params={"instId":"SOL-USDT","bar":"5m","limit":str(limit)},timeout=20)
    r.raise_for_status()
    rows=r.json().get("data",[])
    return [{"ts":int(x[0]),"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4]),"vol":float(x[5])} for x in reversed(rows)]
def current_price():
    r=requests.get(BASE+"/market/ticker",params={"instId":"SOL-USDT"},timeout=20);r.raise_for_status()
    return float(r.json()["data"][0]["last"])
def analyze():
    cs=candles()
    feats=build_features(cs)
    # Conservative baseline trigger; AI may provide an additional score once trained.
    fast=sum(x["c"] for x in cs[-12:])/12
    slow=sum(x["c"] for x in cs[-48:])/48
    price=cs[-1]["c"]
    signal=None
    if fast>slow and price>cs[-2]["c"]:
        signal={"side":"BUY","entry":price,"tp":price*1.012,"sl":price*0.993,"features":feats}
    return price,signal
if __name__=="__main__":
    m=SignalManager(); p,s=analyze(); m.cycle(p,s)
