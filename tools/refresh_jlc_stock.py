#!/usr/bin/env python3
"""Refresh existing selections from JLCPCB's public catalogue search, without login.

This only reads public data and updates a local JSON file. It never changes part
selections, orders, carts, or schematics. Run check_assembly_readiness.py afterward.
The website endpoint is undocumented and can change; mismatches fail closed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'docs/assembly/jlc-stock-snapshot.json'
URL = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2'
FIELDS = ('componentCode', 'componentModelEn', 'componentBrandEn', 'componentSpecificationEn',
          'describe', 'componentLibraryType', 'stockCount', 'canPresaleNumber',
          'minPurchaseNum', 'preMinPurchaseNum', 'leastPatchNumber', 'lossNumber')


def fetch(item):
    code, original = item
    payload = dict(keyword=code, currentPage=1, pageSize=50, presaleType='stock', searchType=2,
                   searchSource='search', stockFlag=False, paramList=[], componentBrandList=[],
                   componentSpecificationList=[], componentAttributeList=[])
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json',
                                          'User-Agent': 'Mozilla/5.0', 'Origin': 'https://jlcpcb.com'})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read()
    data = json.loads(raw)['data']['componentPageInfo']['list'] or []
    matches = [p for p in data if p['componentCode'] == code]
    assert len(matches) == 1, f'{code}: exact catalogue record missing'
    p = matches[0]
    for field in ['componentCode', 'componentModelEn', 'componentBrandEn', 'componentSpecificationEn']:
        assert p[field] == original[field], f'{code}: {field} changed; manual review required'
    for field in ['canPresaleNumber', 'leastPatchNumber', 'lossNumber']:
        assert isinstance(p[field], (int, float)), f'{code}: missing quantity field {field}'
    updated = dict(original)
    for field in ['overseasStockCount', 'page_sha256']:
        updated.pop(field, None)  # Do not leave older page values alongside new API values.
    updated.update({k: p[k] for k in FIELDS if k in p})
    updated.update(retrieved_at=datetime.now(timezone.utc).isoformat(), source='https://jlcpcb.com/partdetail/' + code,
                   api_source=URL, query=payload, response_sha256=hashlib.sha256(raw).hexdigest())
    return code, updated


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('codes', nargs='*', help='Selected C-codes; defaults to all selected parts')
    ap.add_argument('--output', type=Path, default=SNAPSHOT)
    args = ap.parse_args()
    doc = json.loads(SNAPSHOT.read_text())
    codes = args.codes or list(doc['parts'])
    assert set(codes) <= set(doc['parts']), 'This tool cannot add unqualified parts'
    with ThreadPoolExecutor(max_workers=3) as pool:
        refreshed = dict(pool.map(fetch, [(c, doc['parts'][c]) for c in codes]))
    doc['parts'].update(refreshed)
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n')
    for code, p in refreshed.items():
        print(code, p['componentModelEn'], 'available:', max(0, p['canPresaleNumber']))


if __name__ == '__main__':
    main()
