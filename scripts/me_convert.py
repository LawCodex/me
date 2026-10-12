#!/usr/bin/env python3
"""Convert Montenegrin laws fetched by me_fetch.py to Markdown.

Usage: me_convert.py RAW_DIR OUT_DIR
"""
import datetime, glob, json, os, re, subprocess, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from me_textmd import structure, pdftotext

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()


def slug(s, n=80):
    s = unicodedata.normalize('NFKD', s.lower().replace('đ', 'dj')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:n].rstrip('-')


def yq(s):
    return '"' + re.sub(r'\s+', ' ', s).strip().replace('\\', '\\\\').replace('"', '\\"') + '"'


def text_of(fn):
    if fn.endswith('.pdf'):
        return pdftotext(fn)
    r = subprocess.run(['textutil', '-convert', 'txt', '-stdout', fn], capture_output=True)
    return r.stdout.decode('utf-8', 'replace')


def main():
    idx = {str(x['id']): x for x in json.load(open(os.path.join(RAW, 'sl_index.json')))['zakon']}
    counts = {}
    for fn in sorted(glob.glob(os.path.join(RAW, 'doc', '*.*'))):
        if fn.endswith('.json'):
            continue
        key = os.path.basename(fn).split('.')[0]
        meta = json.load(open(fn + '.json'))
        t = text_of(fn)
        if len(t.strip()) < 300:
            continue
        md = structure(t)
        gov_url = 'https://www.gov.me/dokumenta/' + meta['node_ref']
        if key == 'ustav':
            title, sub, typ, fname, ident, sl = 'Ustav Crne Gore', 'ustav', 'constitution', 'ustav-crne-gore.md', 'Službeni list Crne Gore, broj 1/2007', None
            date = '2007-10-22'
        else:
            x = idx[key]
            title = x['title'].rstrip('*').strip()
            m = re.search(r'broj\s+(\d+)/(\d{4})', x['edition'])
            year, issue = (m.group(2), m.group(1)) if m else ('0000', '0')
            sub, typ = 'zakoni/%s' % year, ('code' if re.match(r'^(Zakonik|Krivični zakonik|Carinski zakon)', title) else 'act')
            fname = '%s-%03d-%s.md' % (year, int(issue), slug(title))
            ident, sl, date = x['edition'], 'https://www.sluzbenilist.me/propisi/' + key, None
        consolidated = bool(re.search(r'pre?[cč]i[sš][cć]en', meta['title'], re.I))
        path = os.path.join(OUT, sub, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fm = ['---', 'title: ' + yq(title), 'identifier: ' + yq(ident), 'type: ' + typ,
              'jurisdiction: me', 'language: cnr']
        if date:
            fm.append('date: ' + date)
        fm += ['status: in_force',
               'text_version: ' + ('consolidated_unofficial' if consolidated else 'unofficial_copy'),
               'source: ' + yq(gov_url), 'source_document_title: ' + yq(meta['title']),
               'source_published: ' + meta.get('published_at', '')[:10]]
        if sl:
            fm.append('register: ' + yq(sl))
        fm += ['retrieved: ' + TODAY, '---']
        open(path, 'w').write('\n'.join(fm) + '\n\n# ' + title + '\n\n' + md + '\n')
        counts[(typ, consolidated)] = counts.get((typ, consolidated), 0) + 1
    # register index (metadata only) of all laws listed by the Official Gazette, with status
    have = {os.path.basename(p).split('.')[0] for p in glob.glob(os.path.join(RAW, 'doc', '*.json'))}
    rows = sorted(idx.values(), key=lambda x: (x['status'] != 'Važeći', x['title'].lower()))
    lines = ['# Registar zakona — Službeni list Crne Gore', '',
             'Metadata of all acts of type *Zakon* in the register of the Official Gazette of Montenegro '
             '(https://www.sluzbenilist.me/propisi?type=0&act=1), retrieved %s. "Tekst" = a text file is '
             'included in this repository (from gov.me).' % TODAY, '',
             '| Zakon | Izdanje | Status | Oblast | Tekst |', '|---|---|---|---|---|']
    for x in rows:
        lines.append('| [%s](https://www.sluzbenilist.me/propisi/%s) | %s | %s | %s | %s |' % (
            x['title'].replace('|', '/'), x['id'], x['edition'].replace('Službeni list Crne Gore, broj ', 'Sl. list CG '),
            x['status'], x['area'], 'da' if str(x['id']) in have else ''))
    os.makedirs(os.path.join(OUT, 'registar'), exist_ok=True)
    open(os.path.join(OUT, 'registar', 'zakoni.md'), 'w').write('\n'.join(lines) + '\n')
    for k, v in sorted(counts.items()):
        print(k, v, file=sys.stderr)


if __name__ == '__main__':
    main()
