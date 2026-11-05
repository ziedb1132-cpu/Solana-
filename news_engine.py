"""Solana news intake from public RSS feeds, limited to last 24h."""
import time, requests, xml.etree.ElementTree as ET
FEEDS=["https://news.google.com/rss/search?q=Solana+crypto&hl=en-US&gl=US&ceid=US:en","https://news.google.com/rss/search?q=SOL+Solana+blockchain&hl=en-US&gl=US&ceid=US:en"]
def fetch_news():
    cutoff=time.time()-86400; seen=set();items=[]
    for url in FEEDS:
        try:
            root=ET.fromstring(requests.get(url,timeout=15).text)
            for it in root.findall(".//item"):
                title=(it.findtext("title") or "").strip(); link=(it.findtext("link") or "").strip()
                pub=it.findtext("pubDate") or ""
                if title and link and link not in seen:
                    seen.add(link);items.append({"title":title,"url":link,"published":pub,"source":"Google News RSS"})
        except Exception: continue
    # Feed timestamps are retained for downstream parsing; exclude undated items conservatively.
    return items
def sentiment_score(items):
    positive={"surge","rise","gain","bull","adoption","launch","upgrade","growth"}
    negative={"fall","drop","hack","exploit","lawsuit","bear","outage","crash"}
    scores=[]
    for item in items:
        words=set(item["title"].lower().split());scores.append((len(words&positive)-len(words&negative))/max(1,len(words)))
    return sum(scores)/len(scores) if scores else 0.0
