import json, re, html, datetime, urllib.request
from urllib.parse import quote
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

def google_url(lang, site, kw, when):
    q = "site:%s %s when:%s" % (site, "(%s)" % kw if kw else "", when)
    q = re.sub(r"\s+", " ", q).strip()
    return "https://news.google.com/rss/search?q=%s&hl=%s&gl=US&ceid=%s" % (quote(q), lang["hl"], quote(lang["ceid"]))

def main():
    cfg = json.load(open("feeds.json", encoding="utf-8"))
    result = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "categories": cfg["categories"], "languages": []}
    for lang in cfg["languages"]:
        cats = {}
        for cat in cfg["categories"]:
            cid = cat["id"]
            outlets = []
            for o in lang["outlets"]:
                try:
                    if cid == "top" and o.get("official_top"):
                        url, google = o["official_top"], False
                    else:
                        site = o.get("sites", {}).get(cid) or (o.get("top_site") if cid == "top" else None) or o["site"]
                        url = google_url(lang, site, lang["keywords"].get(cid, ""), "1d" if cid == "top" else "2d")
                        google = True
                    items = parse(get(url), google)
                    err = None if items else "Sin noticias en este momento"
                except Exception as e:
                    items, err = [], "No se pudo leer: %s" % e
                for it in items:
                    it["outlet"] = o["name"]
                outlets.append({"name": o["name"], "items": items, "error": err})
            cats[cid] = outlets
        result["languages"].append({"id": lang["id"], "name": lang["name"], "cats": cats})
    try:
        prev = json.load(open("news.json", encoding="utf-8"))
        if prev.get("languages") == result["languages"]:
            print("Sin cambios en los titulares")
            return
    except Exception:
        pass
    json.dump(result, open("news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
