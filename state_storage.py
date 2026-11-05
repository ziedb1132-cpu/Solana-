"""GitHub-safe persistent state splitting at 90 MiB with SHA-256 verification."""
import hashlib,json,os,shutil
from pathlib import Path
STATE=Path("solana_state.json")
PARTS=Path("solana_state.parts")
MANIFEST=Path("solana_state.manifest.json")
LIMIT=90*1024*1024
BLOCK=1024*1024

def _hash(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(BLOCK),b""):h.update(b)
    return h.hexdigest()

def restore():
    if STATE.exists():return "plain"
    if not MANIFEST.exists():return "missing"
    meta=json.loads(MANIFEST.read_text(encoding="utf-8"))
    tmp=STATE.with_suffix(".json.restore")
    h=hashlib.sha256();size=0
    with tmp.open("wb") as out:
        for name in meta["parts"]:
            p=(PARTS/name).resolve()
            if PARTS.resolve() not in p.parents or not p.is_file():raise RuntimeError("Missing or unsafe state part: "+name)
            with p.open("rb") as src:
                for b in iter(lambda:src.read(BLOCK),b""):
                    out.write(b);h.update(b);size+=len(b)
    if size!=meta["size"] or h.hexdigest()!=meta["sha256"]:
        tmp.unlink(missing_ok=True);raise RuntimeError("Solana state parts integrity check failed")
    os.replace(tmp,STATE)
    return "restored"

def pack():
    if not STATE.exists():return "no-state"
    size=STATE.stat().st_size
    if size<=LIMIT:
        return "plain"
    if PARTS.exists():shutil.rmtree(PARTS)
    PARTS.mkdir(parents=True)
    h=hashlib.sha256();names=[];index=0;total=0
    with STATE.open("rb") as src:
        while True:
            b=src.read(LIMIT)
            if not b:break
            name=f"state-{index:04d}.part";(PARTS/name).write_bytes(b)
            names.append(name);h.update(b);total+=len(b);index+=1
    meta={"format":1,"size":total,"sha256":h.hexdigest(),"chunk_size":LIMIT,"parts":names}
    tmp=MANIFEST.with_suffix(".tmp");tmp.write_text(json.dumps(meta,separators=(",",":")),encoding="utf-8")
    os.replace(tmp,MANIFEST);STATE.unlink()
    return f"split:{len(names)}"

if __name__=="__main__":
    import sys
    action=sys.argv[1] if len(sys.argv)>1 else "restore"
    print(restore() if action=="restore" else pack())
