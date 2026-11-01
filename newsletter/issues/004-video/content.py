"""All on-screen and spoken content for Nordic Crypto #4 (newsreel site cut).

Facts only from newsletter issue #4 (editor-approved stories, 19–25 October 2026).
Brand is Nordic Crypto. Presenter: the fictional anchor Anders Fjell (reference image
assets/anchor/anchor-v1.jpg). The sign-off card is "The Nordic Crypto team". No story this
week comes from Kaupr. Charges stay framed as charges. Nothing on screen or in the narration
says the programme is made with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "en-GB-ThomasNeural"
RATE = "+20%"
NUMBER = "4"
ISSUE = "Issue #4"
ISSUE_RIBBON = "ISSUE #4"
DATES = "19–25 October 2026"
DATES_SHORT = "19–25 Oct 2026"
BUG_LINE = "ISSUE #4 · 19–25 OCT 2026"
SITE = site_url.HOST
LANG = "en"
ANCHOR = "Anders Fjell"
ANCHOR_ROLE = "NORDIC CRYPTO"
ANCHOR_IMG = "anchor-v1.jpg"

STORIES = {
 "s1": dict(section="NORWAY", head="Minister: crypto mining in data centres is not widespread",
            src="Ságat (Norway) · 22 Oct · may require a subscription", big="8 OF 113", kicker="DATA CENTRES WITH MINING", art="nodes"),
 "s2": dict(section="NORWAY", head="Five charged over an Oslo home robbery in which crypto was demanded",
            src="TV 2 (Norway) · 20 Oct", big="CHARGED", kicker="NOT CONVICTED · TRIAL UNDER WAY", art="scan"),
 "s3": dict(section="SWEDEN", head="Riksbank deputy governor: Sweden should prepare for a possible e-krona",
            src="hurbra (Sweden) · 22 Oct", big="E-KRONA", kicker="NO DECISION TAKEN", art="globe"),
 "s4": dict(section="SWEDEN", head="Netanyahu floats crypto against sanctions; the Bank of Israel pushes back",
            src="Dagens Nyheter (Sweden) · 24 Oct · may require a subscription", big="SANCTIONS", kicker="CENTRAL BANK SAYS NO", art="globe", logo="dn"),
 "s5": dict(section="SWEDEN", head="Apple asks court to dismiss suit over a fake bitcoin wallet app",
            src="Realtid (Sweden) · 21 Oct", big="$1.8M", kicker="A LAWSUIT · NOT A RULING", art="scan", logo="realtid"),
 "s6": dict(section="MARKETS", head="BlackRock files for a bitcoin ETF designed to limit losses",
            src="Kryptovalutaguiden (Sweden) · 20 Oct", big="PBIT", kicker="FILING · NOT YET EFFECTIVE", art="bars", logo="kryptovalutaguiden"),
 "s7": dict(section="NORDIC", head="Tiny Vikings planned a giant figure for the Marfa art weekend",
            src="Nordic Crypto · 20 Oct", big="VIKING", kicker="BITCOIN ORDINALS ART", art="stars"),
}
END_DISCLOSURE = "Nothing here is investment advice."
TICKER = [
 "NORDIC CRYPTO · ISSUE #4 · " + DATES_SHORT.upper(),
 "Norway's digitalisation minister: crypto mining at 8 of 113 registered data centres (Ságat)",
 "A temporary, limited ban on power-hungry crypto data centres is being assessed, subject to EEA law",
 "Oslo: five charged over a home robbery in which USD 2 million in crypto was demanded. Not convicted (TV 2)",
 "Riksbank's Per Jansson: Sweden should prepare for a possible e-krona. No decision taken (hurbra)",
 "Bank of Israel: cryptocurrencies cannot be used to get around sanctions (Dagens Nyheter)",
 "Apple asks a US court to dismiss a lawsuit over a fake Sparrow Wallet app (Realtid, citing Law360)",
 "BlackRock files for the iShares Bitcoin Managed Protection ETF, ticker PBIT. Not yet effective (Kryptovalutaguiden)",
 "Tiny Vikings planned to unveil a giant figure in Marfa, Texas, on 22 October",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good evening, I'm Anders Fjell, and this is Nordic Crypto. Issue number four, with the Nordic crypto news from the 19th to the 25th of October, 2026.",
 "open_b": "Tonight: Norway's minister says crypto mining in data centres is not widespread. Sweden's central bank looks at an e-krona. And Apple and BlackRock in the bitcoin headlines.",
 "s1": "Norway's digitalisation minister, Torgeir Micaelsen, told the Storting in a written answer that crypto mining in data centres is not widespread. The register shows mining at eight of 113 data centres. The government is assessing a temporary, limited ban, subject to EEA law. Ságat reported the answer.",
 "s2": "TV 2 reports that five people are on trial in Oslo District Court over a home robbery in which the robbers demanded two million dollars in crypto. One posed as a food courier. The five are charged, and have not been convicted.",
 "s3": "In Sweden, Riksbank deputy governor Per Jansson told Reuters that Sweden should prepare for a possible e-krona, pointing to the digital euro and stablecoins. No decision has been taken. Hurbra reported the interview.",
 "s4": "Dagens Nyheter reports on criticism after Israel's prime minister Benjamin Netanyahu suggested crypto could help get around possible sanctions. The Bank of Israel replied that cryptocurrencies cannot serve that purpose.",
 "s5": "Realtid reports that Apple has asked a US court to dismiss a lawsuit from three investors who say they lost one point eight million dollars through a fake bitcoin wallet app in the App Store. Apple says it cannot be held responsible for outside fraudsters.",
 "s6": "And BlackRock has filed for a bitcoin fund designed to limit losses, ticker P-BIT, Kryptovalutaguiden reports. The filing is incomplete, and the shares may not be sold until it becomes effective.",
 "s7": "Finally, the Bitcoin Ordinals art project Tiny Vikings planned to unveil what it calls the world's largest Tiny Viking in Marfa, Texas, on the 22nd of October, according to its event page.",
 "close": "That's all for issue number four. Every story, with a link to the original source, is at nordiccrypto.no. Nothing here is investment advice.",
 "signoff": "I'm Anders Fjell. See you next week.",
}

TONIGHT = [
 ("NORWAY", "Minister: crypto mining in data centres is not widespread", "data centres"),
 ("SWEDEN", "The Riksbank looks at a possible e-krona", "e-krona"),
 ("MARKETS", "Apple and BlackRock in the bitcoin headlines", "Apple"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "anchor", {"lower_third": True}),
 ("open_b", "tonight", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "Data centres, and a robbery trial in Oslo"}),
 ("s1", "story", {}), ("s2", "story", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "An e-krona, sanctions and a fake wallet app"}),
 ("s3", "story", {}), ("s4", "story", {}), ("s5", "story", {}),
 ("b_more", "section", {"label": "MORE NEWS", "sub": "Markets and art"}),
 ("s6", "story", {}), ("s7", "story", {}),
 ("close", "end", {"fade": False}),
 ("signoff", "anchor", {"lower_third": True, "last": True}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE NUMBER FOUR"
BUMPER_LEN = {"bumper": 4.5, "section": 1.6, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "8 OF 113"
THUMB_KICKER = "NORWAY · ISSUE #4"
THUMB_HEAD = "Norway's minister on crypto mining in data centres, and a possible e-krona"
