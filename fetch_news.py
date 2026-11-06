import json, re, html, datetime, urllib.request
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

N = 5  # noticias por medio

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NoticiasApp)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def clean(t):
    t = html.unescape(re.sub(r"<[^>]+>", "", t or ""))
    return re.sub(r"\s+", " ", t).strip()

def parse(xml, google):
    out, seen = [], set()
    for it in ET.fromstring(xml).iter("item"):
        title = clean(it.findtext("title"))
        if google and " - " in title:
            title = title.rsplit(" - ", 1)[0]
        link = (it.findtext("link") or "").strip()
        if not title or not link or title in seen:
            continue
        seen.add(title)
        item = {"title": title, "link": link}
        try:
            item["pub"] = parsedate_to_datetime(it.findtext("pubDate")).astimezone(datetime.timezone.utc).isoformat()
        except Exception:
            pass
        if not google:
            item["desc"] = clean(it.findtext("description"))[:200]
        out.append(item)
        if len(out) == N:
            break
    return out

def main():
    cfg = json.load(open("feeds.json", encoding="utf-8"))
    result = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sections": []}
    for sec in cfg["sections"]:
        outlets = []
        for o in sec["outlets"]:
            try:
                items = parse(get(o["url"]), o["google"])
                err = None if items else "Sin noticias en este momento"
            except Exception as e:
                items, err = [], "No se pudo leer: %s" % e
            outlets.append({"name": o["name"], "items": items, "error": err})
        result["sections"].append({"id": sec["id"], "name": sec["name"], "outlets": outlets})
    try:
        prev = json.load(open("news.json", encoding="utf-8"))
        if prev.get("sections") == result["sections"]:
            print("Sin cambios en los titulares")
            return
    except Exception:
        pass
    json.dump(result, open("news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
