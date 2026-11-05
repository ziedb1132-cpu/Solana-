"""Thirty-layer model; learning starts after 10 closed paper signals."""
import os,math
MODEL_PATH="solana_model.pt"
GATE_CLOSED=10
try:
 import torch
 from torch import nn
 class DeepSignalModel(nn.Module):
    def __init__(self,input_dim=1205):
        super().__init__();layers=[];d=input_dim
        for _ in range(30):
            layers.extend([nn.Linear(d,128),nn.ReLU(),nn.Dropout(.08)]);d=128
        layers.append(nn.Linear(d,1));self.net=nn.Sequential(*layers)
    def forward(self,x):return self.net(x)
except ImportError:
 torch=None;DeepSignalModel=None;nn=None

def _outcome(item):
    net=item.get("net_return_pct")
    try:
        if net is not None and math.isfinite(float(net)):return 1 if float(net)>0 else 0
    except (TypeError,ValueError):pass
    return 1 if item.get("status")=="TP" else 0

def gate_status(history):
    closed=[x for x in history if x.get("status") in ("TP","SL")]
    compatible=[x for x in closed if isinstance(x.get("features"),dict) and len(x["features"])==1205]
    wins=sum(1 for x in closed if _outcome(x)==1)
    losses=len(closed)-wins
    return {"closed_signals":len(closed),"compatible_signals":len(compatible),
            "required_closed":GATE_CLOSED,"wins":wins,"losses":losses,
            "enabled":len(compatible)>=GATE_CLOSED}

def _row(signal):
    features=signal.get("features") or {}
    return [float(features[k]) for k in sorted(features)]

def train(history,epochs=2):
    gate=gate_status(history)
    if torch is None:return {"trained":False,"reason":"torch unavailable","gate":gate}
    if not gate["enabled"]:return {"trained":False,"reason":"10 closed signals with compatible feature snapshots required","gate":gate}
    rows=[];labels=[]
    for item in history:
        if item.get("status") not in ("TP","SL") or not item.get("features"):continue
        row=_row(item)
        if len(row)!=1205:continue
        rows.append(row);labels.append(_outcome(item))
    if len(rows)<GATE_CLOSED:return {"trained":False,"reason":"10 compatible closed signals required","gate":gate}
    split=max(1,int(len(rows)*0.8))
    if split>=len(rows):split=len(rows)-1
    x=torch.tensor(rows[:split],dtype=torch.float32);y=torch.tensor(labels[:split],dtype=torch.float32).view(-1,1)
    xv=torch.tensor(rows[split:],dtype=torch.float32);yv=torch.tensor(labels[split:],dtype=torch.float32).view(-1,1)
    model=DeepSignalModel(len(rows[0]));opt=torch.optim.AdamW(model.parameters(),lr=1e-4);loss_fn=nn.BCEWithLogitsLoss()
    model.train()
    for _ in range(max(1,epochs)):
        opt.zero_grad();loss=loss_fn(model(x),y);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);opt.step()
    model.eval()
    with torch.no_grad():val_loss=float(loss_fn(model(xv),yv)) if len(xv) else None
    torch.save({"state_dict":model.state_dict(),"input_dim":len(rows[0]),"feature_version":"solana-1200-v2","trained_samples":len(rows)},MODEL_PATH)
    return {"trained":True,"samples":len(rows),"train_samples":len(x),"validation_samples":len(xv),
            "train_loss":float(loss.detach()),"validation_loss":val_loss,"gate":gate,"warning":"Early-stage model: small sample size; probability is experimental."}

def predict_probability(features):
    if torch is None or not os.path.isfile(MODEL_PATH):return None
    try:
        data=torch.load(MODEL_PATH,map_location="cpu",weights_only=False);keys=sorted(features)
        if data.get("feature_version")!="solana-1200-v2" or len(keys)!=int(data.get("input_dim",0)):return None
        model=DeepSignalModel(len(keys));model.load_state_dict(data["state_dict"]);model.eval()
        with torch.no_grad():
            value=torch.sigmoid(model(torch.tensor([[float(features[k]) for k in keys]],dtype=torch.float32))).item()
        return float(value)
    except Exception:return None
