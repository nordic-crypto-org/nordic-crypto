# Nordic Crypto – new source proposals, November 2026

Status: proposal for editor review. Nothing has been added to `sources.json`, nothing committed.
Checked 2026-11-02 from the box: compared every candidate by domain and feed URL against the 1,037 outlets and 38 event sources in `sources.json` (plus `data/podcasts.json` and `data/talks.json`). Feeds were parsed with Python `xml.etree`. robots.txt was checked with `urllib.robotparser` for `NordicCryptoBot` and `*`.

## Summary

| # | Candidate | Feed | Type | Verdict |
|---|---|---|---|---|
| 1 | Ny Teknik – bitcoin topic (SE) | https://www.nyteknik.se/amnen/bitcoin?lab_viewport=rss | rss-all | Recommend |
| 2 | forskning.no (NO) | https://www.forskning.no/?lab_viewport=rss | rss | Recommend |
| 3 | ESMA (EU) | https://www.esma.europa.eu/rss.xml | rss | Recommend |
| 4 | EBA (EU) | https://www.eba.europa.eu/rss.xml | rss | Recommend |
| 5 | Coinmotion blog (FI) | https://coinmotion.com/fi/blog/feed/ | rss | Optional (company blog) |
| 6 | Teknisk Ukeblad / tu.no (NO) | https://www.tu.no/?lab_viewport=rss | rss | Editor decision on terms |
| 7 | Bergen Bitcoin Meetup (event source, NO) | https://www.meetup.com/bergen-bitcoin-meetup/ | jsonld | Recommend |

---

## 1. Ny Teknik – bitcoin topic feed

- URL: https://www.nyteknik.se
- Feed: https://www.nyteknik.se/amnen/bitcoin?lab_viewport=rss (topic feed, 81 items. The newest are 30 Oct 2026 "Kryptobörsen hackad – 62 miljarder kronor kan ha påverkats", 28 Sep 2026 and 28 Aug 2026). The front-page feed https://www.nyteknik.se/?lab_viewport=rss (98 items) is optional; https://www.nyteknik.se/nt-rss.xml redirects to it.
- Type: Tech media. Sweden, Swedish.
- Why reputable: Sweden's main engineering/tech weekly, first issue 26 Oct 1967, published by Ny Teknik Group Sverige AB (source: https://www.nyteknik.se/amnen/rss). It isn't in the list yet: SE tech coverage today is only Breakit.
- robots.txt (https://www.nyteknik.se/robots.txt): allowed for NordicCryptoBot and `*`. It blocks only named training bots (GPTBot, CCBot, ClaudeBot and others).
- Terms: the user terms at https://www.nyteknikgroup.se/anvandarvillkor/ are JS-rendered and could not be read by curl (WebFetch returned 403). A web-search summary of them says reading is allowed for private use, and the subscription terms forbid copying or republishing content. Nothing found forbids linking to headlines from a public RSS feed. Some articles are Premium, so paywall=true.
- Proposed entry:
```json
{"id": "nyteknik-bitcoin", "name": "Ny Teknik (topic: bitcoin)", "country": "SE", "kind": "Tech media", "url": "https://www.nyteknik.se", "feed": "https://www.nyteknik.se/amnen/bitcoin?lab_viewport=rss", "type": "rss-all", "paywall": true, "enabled": true, "status": "ok (81 items, newest 2026-10-30)", "verified": "2026-11-02", "coverage": "national", "language": "Swedish", "method": "rss"}
```
- Optional second entry (front page, keyword-filtered):
```json
{"id": "nyteknik", "name": "Ny Teknik", "country": "SE", "kind": "Tech media", "url": "https://www.nyteknik.se", "feed": "https://www.nyteknik.se/?lab_viewport=rss", "type": "rss", "paywall": true, "enabled": true, "status": "ok (98 items on 2026-11-02)", "verified": "2026-11-02", "coverage": "national", "language": "Swedish", "method": "rss"}
```

## 2. forskning.no

- URL: https://www.forskning.no
- Feed: https://www.forskning.no/?lab_viewport=rss (151 items, newest 2 Nov 2026). Note that https://www.forskning.no/rss returns malformed XML. The English sister site's feed https://www.sciencenorway.no/?lab_viewport=rss (121 items) is also valid.
- Type: research news. Norway, Norwegian.
- Why reputable: an edited research-news outlet that follows Redaktørplakaten, Vær Varsom-plakaten and Tekstreklameplakaten (source: https://www.forskning.no/om-forskningno/om-forskningno/990992). It fills the academic gap next to `data/academia.json` for Norwegian research on crypto, blockchain and CBDC.
- robots.txt (https://www.forskning.no/robots.txt): allowed.
- Terms: the about page says articles may not be copied or reused without agreement beyond quotation rights, and it explicitly offers "RSS-feeds gir deg nyheter fra forskning.no på ditt nettsted". Headlines and links via RSS are therefore invited.
- Proposed entry:
```json
{"id": "forskning-no", "name": "forskning.no", "country": "NO", "kind": "Research news", "url": "https://www.forskning.no", "feed": "https://www.forskning.no/?lab_viewport=rss", "type": "rss", "paywall": false, "enabled": true, "status": "ok (151 items on 2026-11-02)", "verified": "2026-11-02", "coverage": "national", "language": "Norwegian", "method": "rss"}
```

## 3. ESMA – European Securities and Markets Authority

- URL: https://www.esma.europa.eu
- Feed: https://www.esma.europa.eu/rss.xml (valid RSS 2.0, 10 items, newest "ESMA publishes latest edition of its newsletter", 29 Oct 2026). Items have no `<pubDate>`; the date is only in the description's `<time datetime=…>`, so the fetcher has to fall back to the page date via `resolve_published`.
- Type: Regulator. EU, English.
- Why reputable: the EU securities regulator. It runs the MiCA interim register and MiCA guidance that apply to SE/DK/FI and, through the EEA, to NO/IS (source: https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica). The register itself has no RSS; it is published as weekly CSV files.
- robots.txt: allowed.
- Terms: per the legal notice (https://www.esma.europa.eu/legal-notice), "Reproduction of all information on this site … is authorised" with source attribution. The logo may not be used without permission, so set `logo_skipped`.
- Proposed entry (keyword-filtered; most items aren't about crypto):
```json
{"id": "esma", "name": "ESMA (EU securities regulator)", "country": "EU", "kind": "Regulator", "url": "https://www.esma.europa.eu", "feed": "https://www.esma.europa.eu/rss.xml", "type": "rss", "paywall": false, "enabled": true, "status": "ok (10 items; no pubDate, date read from the page)", "verified": "2026-11-02", "coverage": "national", "language": "English", "match_extra": ["MiCA", "crypto-asset", "CASP", "stablecoin", "DLT"], "method": "rss"}
```

## 4. EBA – European Banking Authority

- URL: https://www.eba.europa.eu
- Feed: https://www.eba.europa.eu/rss.xml (valid RSS 2.0, 10 items, items dated 29 Oct and 23 Oct 2026; one pinned item from 2024).
- Type: Regulator. EU, English.
- Why reputable: the EU banking authority, responsible under MiCA for asset-referenced and e-money tokens (stablecoins). ESMA's MiCA page says the register is fed by the NCAs and the EBA.
- robots.txt: allowed.
- Terms: per the legal notice (https://www.eba.europa.eu/find-out-about-us/legal-notice), "Reproduction of all EBA material on this site is authorised, provided the source is acknowledged". The logo needs prior permission, so set `logo_skipped`.
- Proposed entry:
```json
{"id": "eba", "name": "EBA (European Banking Authority)", "country": "EU", "kind": "Regulator", "url": "https://www.eba.europa.eu", "feed": "https://www.eba.europa.eu/rss.xml", "type": "rss", "paywall": false, "enabled": true, "status": "ok (10 items on 2026-11-02)", "verified": "2026-11-02", "coverage": "national", "language": "English", "match_extra": ["MiCA", "crypto-asset", "e-money token", "asset-referenced token", "stablecoin"], "method": "rss"}
```

## 5. Coinmotion blog (optional, company blog)

- URL: https://coinmotion.com/fi/blog/
- Feed: https://coinmotion.com/fi/blog/feed/ (100 items, newest 30 Oct 2026 "Hakkerit veivät Binancesta ennätyssumman"). https://coinmotion.com/fi/feed/ serves the same items.
- Type: company blog of a Finnish exchange. Finland, Finnish.
- Why considered: Coinmotion Oy is a Finnish crypto-asset service provider with MiCA authorisation from FIN-FSA (2 July 2025, per web search citing https://paymentinstitutionsregister.eu/dasp/fi/coinmotion-oy-86 and Coinmotion's own post https://coinmotion.com/fi/coinmotion-sai-mica-toimiluvan-kryptosijoittaminen-jatkuu-varmalla-pohjalla/). This is the same kind of source as Bare Bitcoin (blogg). Its podcast Kryptopodi is already in `data/podcasts.json`. Conflict of interest: it's a company that sells crypto, so stories should be labelled as company sources.
- robots.txt (https://coinmotion.com/robots.txt): the feed and blog are allowed. Only corporate pages such as terms, contact and newsletter are disallowed.
- Terms: no clause about reusing website content was found. The public terms found are customer and payment-service terms. The /fi/kayttoehdot/ page is robots-disallowed and was not fetched.
- Proposed entry (keyword-filtered, since much of it is global market commentary):
```json
{"id": "coinmotion-blog", "name": "Coinmotion (blog)", "country": "FI", "kind": "Company blog", "url": "https://coinmotion.com/fi/blog/", "feed": "https://coinmotion.com/fi/blog/feed/", "type": "rss", "paywall": false, "enabled": true, "status": "ok (100 items on 2026-11-02)", "verified": "2026-11-02", "coverage": "national", "language": "Finnish", "max_new_per_run": 8, "method": "rss"}
```

## 6. Teknisk Ukeblad / tu.no (editor decision needed on terms)

- URL: https://www.tu.no
- Feed: https://www.tu.no/?lab_viewport=rss (https://www.tu.no/rss redirects here, 259 items, newest 2 Nov 2026). The tag feed https://www.tu.no/tag/kryptovaluta?lab_viewport=rss has only 3 items (newest 22 Jul 2026 "Kryptosentre tilpasser seg for å få strøm i nord"), so the main feed with a keyword filter is better.
- Type: Tech media. Norway, Norwegian.
- Why reputable: Norway's main engineering paper, with an archive back to 1854 (per https://www.tumedia.no/brukeravtale). It is published by Teknisk Ukeblad Media, the same publisher as Digi.no and Kode24, which are already sources. It covers data centres, mining, energy and cyber security.
- robots.txt (https://www.tu.no/robots.txt): allowed for NordicCryptoBot and `*`.
- Terms: the subscriber agreement at https://www.tumedia.no/brukeravtale says that "systematisk nedlasting av innhold, herunder automatisert innhenting og bruk av innhold til trening av kunstig intelligens" is not allowed without a written agreement. It is written about subscription content, and the same publisher's Digi.no and Kode24 feeds are already in use, but read strictly it could cover automated feed reading. Editors should decide this, or ask TU Media. This applies equally to the existing Digi.no and Kode24 entries.
- Proposed entry:
```json
{"id": "tu", "name": "Teknisk Ukeblad (tu.no)", "country": "NO", "kind": "Tech media", "url": "https://www.tu.no", "feed": "https://www.tu.no/?lab_viewport=rss", "type": "rss", "paywall": true, "enabled": true, "status": "ok (259 items on 2026-11-02)", "verified": "2026-11-02", "coverage": "national", "language": "Norwegian", "method": "rss"}
```

## 7. Bergen Bitcoin Meetup (event source)

- URL: https://www.meetup.com/bergen-bitcoin-meetup/
- Type: event source (Meetup group). Bergen, Norway.
- Why: an active bitcoin group with 301 members on the group page. Its 2026 events were 22 Jan, 18 Mar and 17 Jun; the June event was a pub meetup at Biskopen (per https://bitcoinonly.events/bergen-bitcoin-pa-pub-2607/). Current event sources only cover Oslo groups and the Meetup searches for Oslo.
- Machine-readable: Event JSON-LD appears on the group page when an event is upcoming, the same as for oslo-blockchain-meetup (which shows one Event block today). Bergen has no upcoming event right now, so there are 0 Event blocks today.
- robots.txt (https://www.meetup.com/robots.txt): the group page is allowed. Meetup group pages are already used for Oslo.
- Location rule: verify the venue and address of each event against the Meetup event page before it is published.
- Proposed `event_sources` entry:
```json
{"id": "bergen-bitcoin-meetup", "name": "Bergen Bitcoin Meetup (Meetup.com)", "url": "https://www.meetup.com/bergen-bitcoin-meetup/", "type": "jsonld", "trusted": true, "organiser": "Bergen Bitcoin Meetup", "city": "Bergen", "enabled": true, "status": "ok (JSON-LD on the group page when an event is scheduled; 301 members, last event 2026-06-17)", "country": "NO"}
```

---

## Rejected

- Computer Sweden (computersweden.se/feed/): the feed is valid, but robots.txt has `Disallow: /feed/` for `*`.
- Arvopaperi (arvopaperi.fi/api/feed/v2/rss/ap) and Tekniikka & Talous (tekniikkatalous.fi/api/feed/v2/rss/tt): the feeds are valid, but robots.txt only allows named search, social and ad bots, and Alma Media makes a TDM reservation under § 13 b of the Finnish Copyright Act.
- Housekeeping, not a new source: the existing Talouselämä and Tivi entries (also Alma) are blocked by the same robots.txt. fetch.py already skips them: `logs/fetch-20261102-042829.log` shows "SKIP robots tivi" and "SKIP robots talouselama". Their status still says "ok".
- Affärsvärlden, Privata Affärer, Placera: no RSS found (/rss returns 404, and affarsvarlden.se?lab_viewport=rss failed TLS).
- FinansWatch DK (finanswatch.dk/rss): returns HTML, not RSS.
- Kryptolehti.fi (feed.xml is valid): no named publisher or about page, and about 8 posts a day rewriting global news, so reputation can't be established.
- Bitcoin Suomi, BitcoinUutiset.fi: no feed (/feed/ is HTML or fails TLS), and no named publisher.
- TrijoNews (news.trijo.co, Swedish exchange Trijo): the feed has 0 items, and the site mostly rewrites CoinDesk and Cointelegraph with exchange ads.
- CryptoFeber.se: the feed returns 410 Gone.
- ECB press (ecb.europa.eu/rss/press.html): valid and allowed, but only Finland is in the euro area and Bank of Finland already covers the digital euro. Left out to keep the list short.
- MiCA register trackers (casp-tracker.com, cryptolicit.com): third-party, unclear operators, and the guessed RSS URLs return 404.
- Mikrobitti (redirects to iltalehti.fi/rss/bitti.xml): valid, but Iltalehti is already a source, and its tech section adds little crypto coverage.
- The Local SE/NO/DK: valid feeds, but general English news with little crypto.
- Oslo Freedom Forum (event): returns 403 to non-browser clients, and it is a single annual event (31 May–2 June 2027 per enogtyve.org) better added by hand.
- Enogtyve.org, Undoqo events, bitcoinonly.events: no usable feed, an empty Atom feed, or a global directory whose feed has posting dates rather than event dates.
