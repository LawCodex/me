#!/usr/bin/env python3
"""Montenegro: build the list of laws from the official register of the Official Gazette
(Službeni list Crne Gore, https://www.sluzbenilist.me/propisi - metadata incl. status
"Važeći"/"Nevažeći"; the texts themselves are only shown there as page images, which we do
not OCR), then look for the text of each law in force in the document library of the
Government of Montenegro (https://www.gov.me, API https://wapi.gov.me/v1/documents) where
ministries publish the laws they administer, often as consolidated texts ("prečišćen tekst").

Usage: me_fetch.py [RAW_DIR]
"""
import json, os, re, sys, time, unicodedata
import requests
from bs4 import BeautifulSoup

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_raw', 'me')
UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
S = requests.Session(); S.headers['User-Agent'] = UA
DELAY = 1.0
BAD = re.compile(r'nacrt|predlog|prijedlog|izvje[sš]taj|obrazlo[zž]enj|analiz|mi[sš]ljenj|amandman|javn\w* rasprav|'
                 r'konsultacij|komentar|poziv|izmjen|dopun|tabel|uporedn|informacij|odluk|rje[sš]enj|pravilnik', re.I)


def get(url, **kw):
    for i in range(6):
        try:
            r = S.get(url, timeout=180, **kw)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.RequestException('HTTP %d' % r.status_code)
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            w = 5 * 2 ** i
            print('  retry', url, e, w, file=sys.stderr, flush=True); time.sleep(w)
    raise SystemExit('give up ' + url)


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower().replace('đ', 'dj')).encode('ascii', 'ignore').decode()
    t = re.sub(r'\(.*?\)', ' ', t)
    t = re.sub(r'pre?ci[sc]+en\w*\s*tekst\w*|\bslu[zs]beni list\w*.*$', ' ', t)
    t = re.sub(r'[^a-z0-9]+', ' ', t).strip()
    return t


def sl_list(act):
    out, page = [], 1
    while True:
        h = get('https://www.sluzbenilist.me/propisi', params={'type': 0, 'act': act, 'page': page}).text
        s = BeautifulSoup(h, 'lxml')
        new = 0
        seen = {x['id'] for x in out}
        for a in s.find_all('a', href=re.compile(r'/propisi/\d+$')):
            if a.get_text(strip=True) in ('Detaljnije', ''):
                continue
            pid = int(a['href'].rstrip('/').split('/')[-1])
            if pid in seen:
                continue
            c = a
            while c.parent is not None and 'Status:' not in c.get_text():
                c = c.parent
            txt = c.get_text(' | ', strip=True)
            rec = {'id': pid, 'title': a.get_text(' ', strip=True)}
            for k, lab in (('status', 'Status:'), ('edition', 'Izdanje:'), ('regno', 'Registarski broj:'),
                           ('kind', 'Vrsta propisa:'), ('area', 'Oblast:'), ('subarea', 'Podoblast:')):
                m = re.search(re.escape(lab) + r' \| ([^|]+)', txt)
                rec[k] = m.group(1).strip() if m else ''
            out.append(rec); seen.add(pid); new += 1
        if not new:
            return out
        page += 1
        if page % 20 == 0:
            print('sl', act, page, len(out), file=sys.stderr, flush=True)


def gov_search(q):
    r = get('https://wapi.gov.me/v1/documents', params={'q': q})
    try:
        return r.json()['data']['data']
    except Exception:
        return []


def main():
    os.makedirs(RAW + '/doc', exist_ok=True)
    lf = RAW + '/sl_index.json'
    if os.path.exists(lf):
        idx = json.load(open(lf))
    else:
        idx = {'ustav': [], 'zakon': sl_list(1)}  # act=0 (Ustav) is not filterable (0 is ignored by the site)
        json.dump(idx, open(lf, 'w'), ensure_ascii=False)
    laws = [x for x in idx['zakon'] + idx['ustav'] if x['status'].startswith('Važe')]
    print(len(idx['zakon']), 'laws in register,', len(laws), 'in force', file=sys.stderr, flush=True)
    mf = RAW + '/gov_matches.json'
    matches = json.load(open(mf)) if os.path.exists(mf) else {}
    for n, x in enumerate(laws):
        k = str(x['id'])
        if k in matches:
            continue
        want = norm(x['title'])
        cands = []
        for d in gov_search(x['title']):
            t = d.get('title', '')
            if BAD.search(t) and not re.search(r'pre?[cč]i[sš][cć]en', t, re.I):
                continue
            if norm(t) != want:
                continue
            if d.get('mime_type', '') not in ('application/pdf', 'application/msword', 'application/rtf', 'text/rtf',
                                              'application/vnd.openxmlformats-officedocument.wordprocessingml.document'):
                continue
            cands.append(d)
        matches[k] = cands
        if n % 50 == 0:
            json.dump(matches, open(mf, 'w'), ensure_ascii=False)
            print('gov', n, sum(1 for v in matches.values() if v), file=sys.stderr, flush=True)
    json.dump(matches, open(mf, 'w'), ensure_ascii=False)
    # download the best candidate: consolidated first, then newest
    for k, cands in matches.items():
        if not cands:
            continue
        best = sorted(cands, key=lambda d: (bool(re.search(r'pre?[cč]i[sš][cć]en', d['title'], re.I)), d.get('published_at', '')))[-1]
        ext = {'application/pdf': 'pdf', 'application/msword': 'doc', 'application/rtf': 'rtf', 'text/rtf': 'rtf'}.get(best['mime_type'], 'docx')
        fn = RAW + '/doc/%s.%s' % (k, ext)
        if os.path.exists(fn):
            continue
        r = get('https://wapi.gov.me/download/%s' % best['node_ref'], params={'version': best.get('version', '1.0')})
        if r.status_code == 200 and len(r.content) > 1000:
            open(fn, 'wb').write(r.content)
            json.dump(best, open(fn + '.json', 'w'), ensure_ascii=False)
    # Constitution: consolidated text published in the Government document library
    fn = RAW + '/doc/ustav.doc'
    if not os.path.exists(fn):
        for d in gov_search('Ustav Crne Gore'):
            if norm(d['title']) == 'ustav crne gore' and re.search(r'pre?[cč]i[sš][cć]en', d['title'], re.I):
                r = get('https://wapi.gov.me/download/%s' % d['node_ref'], params={'version': d.get('version', '1.0')})
                ext = {'application/pdf': 'pdf', 'application/msword': 'doc'}.get(d['mime_type'], 'docx')
                fn = RAW + '/doc/ustav.' + ext
                open(fn, 'wb').write(r.content); json.dump(d, open(fn + '.json', 'w'), ensure_ascii=False)
                break
    print('done', file=sys.stderr)


if __name__ == '__main__':
    main()
