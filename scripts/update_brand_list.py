import json
import os
import re
import sys
import urllib.request

SOURCE_URL = "https://bucketstore.com/brands/list"
OUTPUT_PATH = "bucketstore_brand_list.json"
MIN_RATIO = 0.8


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MartineeCRM brand list sync)"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read().decode("utf-8")


def extract_payload(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html)
    return "".join(json.loads(c) for c in chunks)


def grab(payload, key):
    marker = '"' + key + '":'
    start = payload.find(marker)
    if start < 0:
        raise ValueError(f"'{key}' not found in page")
    value, _ = json.JSONDecoder().raw_decode(payload, start + len(marker))
    return value


def build_rows(types, brands):
    type_map = {t["id"]: t["name"] for t in types}
    rows = []
    for b in brands:
        names = b.get("names") or {}
        rows.append([
            {"brand_id": str(b["id"])},
            {"brand_name": (names.get("title") or "").strip()},
            {"brand_name_ko": (names.get("ko") or "").strip()},
            {"category": "|".join(type_map.get(t, str(t)) for t in (b.get("typeIdList") or []))},
            {"sub_brand_ids": "|".join(str(s) for s in (b.get("subIdList") or []))},
            {"url": f"https://bucketstore.com/brands/{b['id']}"},
        ])
    return rows


def render(rows):
    lines = ["[" + ", ".join(json.dumps(cell, ensure_ascii=False) for cell in row) + "]" for row in rows]
    return '{ "brand" :\n[\n' + ",\n".join(lines) + "\n]\n}\n"


def main():
    payload = extract_payload(fetch_html(SOURCE_URL))
    types = grab(payload, "brandTypeList")
    brands = [b for b in grab(payload, "initBrandList") if b.get("isUse", True)]

    prev_count = 0
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            prev_count = len(json.load(f).get("brand", []))

    if not brands:
        sys.exit("No brands found. Aborting without overwriting.")
    if prev_count and len(brands) < prev_count * MIN_RATIO:
        sys.exit(f"Brand count dropped sharply ({prev_count} -> {len(brands)}). Aborting without overwriting.")

    out = render(build_rows(types, brands))
    json.loads(out)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"OK: {prev_count} -> {len(brands)} brands")


if __name__ == "__main__":
    main()
