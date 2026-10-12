# Montenegro — legislation as Markdown (LawCodex)

Legislation of **Montenegro** (Crna Gora) as plain Markdown. Language: Montenegrin (`cnr`;
texts are in Latin or Cyrillic script as published by the source).

Part of [LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

## Sources and their limits

1. **Službeni list Crne Gore** (Official Gazette, https://www.sluzbenilist.me/propisi) — the
   official register of all acts, with status *Važeći* (in force) / *Nevažeći*. It is used for
   the list of laws and their status. The register shows the **texts only as page images**
   (scans); full text is sold by subscription (podaci.net). The images were **not** OCR'd.
   `registar/zakoni.md` reproduces the register metadata of all 2,319 acts of type *Zakon*
   (1,565 in force), each linked to the official record.
2. **Government of Montenegro document library** (https://www.gov.me, "Dokumenta", API
   `wapi.gov.me/v1/documents`) — ministries publish there the laws in their field, often as
   consolidated texts ("prečišćen tekst"). For every law in force in the register, the library
   was searched by exact title; drafts, proposals, reports and amending acts were excluded.
   When several documents matched, a consolidated text was preferred, then the most recent.
   These texts are **unofficial copies**: they may be the original text, a ministry's
   consolidated version, or the gazette page as published, and may not reflect the latest
   amendments — check `source_published` and the official register (`register` link).
3. The Parliament (https://zakoni.skupstina.me) publishes adopted laws only as scanned
   decrees (Ukaz) with poor embedded OCR; not used.

## What is covered

| Directory | Content | Files |
|---|---|---|
| `ustav/` | Ustav Crne Gore (2007, with Amendments I–XVI of 2013) — consolidated text from gov.me | 1 |
| `zakoni/<year>/` | Laws in force (status *Važeći* in the official register) for which a text was found in the Government library: 3 codes, 295 laws (25 of them marked as consolidated) | 298 |
| `registar/zakoni.md` | Metadata index of all laws in the official register (title, gazette, status, field) | 1 |

`<year>` is the year of the original publication in the *Službeni list*. File names:
`<year>-<issue>-<slug>.md`. Front matter: `title`, `identifier` (Službeni list issue of the
original act), `type`, `status: in_force` (from the register), `text_version`
(`consolidated_unofficial` / `unofficial_copy`), `source` (gov.me document),
`source_document_title`, `source_published`, `register` (official record), `retrieved`.

## What is NOT covered

- ~1,270 laws in force for which no matching text exists in the Government library
  (see `registar/zakoni.md`); amending laws as separate acts.
- Official texts of the Službeni list (images only / paid), secondary legislation,
  municipal regulations, international treaties.

## Licence

Under the Montenegrin Law on Copyright and Related Rights (čl. 9), laws, regulations and other
official texts of state bodies are not protected by copyright.

## Regenerating

```
python scripts/me_fetch.py  ../_raw/me      # register list + gov.me search and downloads
python scripts/me_convert.py ../_raw/me .
```

Needs `pdftotext` and macOS `textutil` (for .doc/.docx/.rtf); `scripts/requirements.txt`.
Retrieved 2026-10-12.
