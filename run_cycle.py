"""One complete persistent SOL/USDT research and paper-signal cycle."""
import json,time
from state_storage import restore
from solana_engine import analyze
from signal_manager import SignalManager,read,write
from news_engine import fetch_news,sentiment_score
from ai_model import gate_status,train,predict_probability

def main():
    restore()
    news=fetch_news();sentiment=sentiment_score(news)
    price,candidate,features,ranked,context=analyze(sentiment)
    state=read()
    state["news_items"]=news[:250];state["news_sentiment"]=sentiment;state["news_updated_at"]=int(time.time())
    write(state)
    gate=gate_status(state.get("history",[]))
    probability=predict_probability(features) if gate["enabled"] else None
    if candidate and probability is not None:
        candidate["ai_win_probability"]=round(probability,5)
        # AI only filters after the 10-closed-signal gate and a valid saved model.
        if probability<0.52:candidate=None
    SignalManager().cycle(price,candidate,ranked,features,context)
    state=read();gate=gate_status(state.get("history",[]));state["ai_gate"]=gate
    closed=[x for x in state.get("history",[]) if x.get("status") in ("TP","SL")]
    last_trained=int(state.get("last_training_samples",0))
    if gate["enabled"] and gate.get("compatible_signals",0)>=max(10,last_trained+5):
        result=train(closed,epochs=2);state["last_training"]=result
        if result.get("trained"):state["last_training_samples"]=len(closed)
    state["strategy_discovery"]={"evaluated":len(ranked),"eligible":sum(1 for x in ranked if x.get("eligible")),
                                  "top":ranked[:20],"updated_at":int(time.time())}
    write(state)
    SignalManager().write_summary(state)
    with open("strategy_history.json","w",encoding="utf-8") as f:
        json.dump({"cycle":state["cycle"],"updated_at":state["updated_at"],"strategies":ranked[:20]},f,ensure_ascii=False,separators=(",",":"))
    print(json.dumps({"cycle":state["cycle"],"price":price,"open":bool(state.get("open_signal")),
                      "news":len(news),"features":len(features),"strategies":len(ranked),
                      "ai_gate":gate,"ai_probability":probability},ensure_ascii=False))

if __name__=="__main__":main()
