"""All on-screen and spoken content for Nordic Crypto #3 (newsreel site cut).

Facts only from newsletter issue #3 (editor-approved stories, 12–19 October 2026).
Brand is Nordic Crypto. The sign-off is "The Nordic Crypto team". Kaupr is named
only as the source of the stories that come from Kaupr. Allegations stay framed
as allegations. Nothing on screen or in the narration says the programme is made
with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "en-GB-ThomasNeural"
RATE = "+18%"
NUMBER = "3"
ISSUE = "Issue #3"
ISSUE_RIBBON = "ISSUE #3"
DATES = "12–19 October 2026"
DATES_SHORT = "12–19 Oct 2026"
BUG_LINE = "ISSUE #3 · 12–19 OCT 2026"
SITE = site_url.HOST
LANG = "en"   # source label: "Source:" (en) or «Kilde:» (nb/nn)

# story key -> lower third + graphic data. section is the label on the card.
# logo: key in assets/img/logos/logos.json, shown small on that story's source chip only.
STORIES = {
 "s1": dict(section="SWEDEN", head="Riksbank asks the Riksdag to prepare a possible digital krona",
            src="Kaupr (Sweden) · 15 Oct", big="KRONA", kicker="NO DECISION TO ISSUE ONE", art="globe", logo="kaupr"),
 "s2": dict(section="SWEDEN", head="Kraken's owner moves to buy a bank used by Swedish savers",
            src="Realtid (Sweden) · 14 Oct", big="2027", kicker="NEEDS REGULATORY APPROVAL", art="bars", logo="realtid"),
 "s3": dict(section="NORWAY", head="Arctic Core's mining claim is now a question in the Storting",
            src="Ságat (Norway) · 16 Oct · may require a subscription", big="CLAIM", kicker="FOLLOW-UP · KAUTOKEINO", art="nodes"),
 "s4": dict(section="NORWAY", head="Industry body says starting with crypto mining is not common",
            src="Ságat (Norway) · 16 Oct · may require a subscription", big="REJECT", kicker="NORSK DATASENTER INDUSTRI", art="nodes"),
 "s5": dict(section="NORWAY", head="Crypto miners among the largest data-centre taxpayers",
            src="Digi.no (Norway) · 14 Oct · may require a subscription", big="TAX", kicker="MINISTER'S ANSWER · 2024", art="bars", logo="digi"),
 "s6": dict(section="NORWAY", head="Local group wants Arctic Core's building permit withdrawn",
            src="Ságat (Norway) · 12 Oct · may require a subscription", big="PERMIT", kicker="A COMPLAINT · NOT A RULING", art="globe"),
 "s7": dict(section="RULES", head="Norway adopts MiCA procedures for fines on significant issuers",
            src="Finanstilsynet (Norway) · 15 Oct", big="MICA", kicker="LEVEL 2 · FINES PROCEDURE", art="stars", logo="finanstilsynet"),
 "s8": dict(section="RULES", head="Bank-backed firm authorised for euro tokens under MiCA",
            src="Finanswatch (Norway) · 14 Oct · may require a subscription", big="EURO", kicker="37 BANKS · LAUNCH SAID SOON", art="bars", logo="finanswatch"),
 "s9": dict(section="DENMARK", head="Government signals new crypto tax rules after a year on the shelf",
            src="Børsen (Denmark) · 12 Oct · may require a subscription", big="TAX", kicker="A SIGNAL · NOT THE STATUTE", art="scan", logo="borsen"),
 "s10": dict(section="MARKETS", head="K33: heavy bitcoin outflows, with low leverage",
             src="Investornytt (Norway) · 13 Oct", big="10,064", kicker="K33'S ASSESSMENT · NOT ADVICE", art="bars"),
 "s11": dict(section="FINLAND", head="Turkish media: a suspect wanted in Finland detained in Istanbul",
             src="Yle (Finland) · 14 Oct", big="CASE", kicker="SUSPECT · NOT A CONVICTION", art="scan", logo="yle"),
}
END_DISCLOSURE = "Nothing here is investment advice."
# Kaupr is named only as the source of its own stories (the Riksbank report, and the tokenisation roundup on the ticker).
TICKER = [
 "NORDIC CRYPTO · ISSUE #3 · " + DATES_SHORT.upper(),
 "Riksbank asks the Riksdag to prepare a possible digital krona; no decision to issue one, and at least five years after the legal work (Kaupr)",
 "Payward, owner of Kraken, to buy Saldo Bank; the deal needs approval and is expected in 2027 (Realtid, citing the Financial Times)",
 "Arctic Core's claim that crypto mining is common is now a question in the Storting (Ságat)",
 "Norsk Datasenter Industri rejects that claim (Ságat; part of the article needs a subscription)",
 "Crypto miners are among the largest data-centre taxpayers for 2024, Digi.no reports from the minister's answer",
 "Naturvernforbundet in Kautokeino wants Arctic Core's building permit withdrawn (Ságat)",
 "Altaposten: an MP has asked how common mining is; the question is behind a subscription",
 "Finanstilsynet adopts EU procedural rules on fines for issuers of significant tokens",
 "A firm backed by 37 banks, including Nordic banks, plans euro tokens under MiCA (Finanswatch; details behind a subscription)",
 "Finanswatch: an EU supervisor is said to be tightening rules on non-compliant stablecoins; the visible text names no coins",
 "Denmark's government signals new crypto tax rules (Børsen)",
 "K33, via Investornytt: net outflows of 10,064 bitcoin in five days. That is K33's assessment, not advice",
 "A French finance committee votes to extend an exit tax to large crypto holdings. Not yet law (Realtid)",
 "Germany plans less favourable crypto tax, EFN reports. A plan, not a final decision",
 "A UK claim seeks 20 million pounds from BitMEX. The owner says it has not been formally served (Dagens PS, citing The Guardian)",
 "Yle, via STT and Turkish media: Richard Schueler detained in Istanbul. A suspect in tax fraud, not a conviction",
 "OpenAI says an internal research model used a test-network wallet it was not given. Test tokens, not real money (Hurbra)",
 "Canton Foundation and a South Korean firm sign a letter of intent on tokenisation, not a live service (Kryptovalutaguiden)",
 "Kaupr summarises US press coverage of stock tokenisation",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good evening, and welcome to Nordic Crypto. This is issue number three, with the Nordic crypto news from the 12th to the 19th of October, 2026.",
 "open_b": "Tonight: Sweden's central bank asks parliament to prepare a possible digital krona. Norway argues over crypto mining at data centres. And new steps on stablecoins and crypto tax.",
 "s1": "Kaupr reports that the Riksbank has asked the Riksdag to prepare legislation for a possible digital krona. The bank has not decided to introduce one. Any issue would need the Riksdag's consent.",
 "s2": "Realtid reports, citing the Financial Times, that Payward, owner of Kraken, is buying Saldo Bank, which offers savings accounts in Sweden. The deal needs approval and is expected in 2027.",
 "s3": "Ságat reports that a claim by the data-centre firm Arctic Core, that crypto mining is common in the industry, is now a question in the Storting. The paper had reported that the firm would do a little mining in Kautokeino.",
 "s4": "The industry body Norsk Datasenter Industri rejects that claim. Its chief executive tells Ságat that it is not common to start with crypto mining. Part of the article is behind a subscription.",
 "s5": "Digi.no reports, from the digitalisation minister's answer to MP Lars Haltbrekken, that fewer than half of Norway's data-centre operators paid corporate tax for 2024. Crypto miners are among the largest taxpayers in that overview.",
 "s6": "Ságat also reports that Naturvernforbundet in Kautokeino wants the municipality to withdraw Arctic Core's building permit. The complaint is not due to be handled before November.",
 "s7": "Finanstilsynet has put EU rules on fines for issuers of significant tokens into Norwegian law. It says the EFTA Surveillance Authority holds that power in the EEA and EFTA states.",
 "s8": "Finanswatch reports that a company backed by 37 banks, including Nordic banks, has an authorisation for blockchain-based euro tokens, with a launch expected soon. Further detail is behind a subscription.",
 "s9": "Børsen reports that Denmark's government is signalling new crypto tax rules. A model agreed by the authorities and the industry more than a year ago had been left on the shelf.",
 "s10": "Investornytt quotes K33: exchange-traded bitcoin products saw net outflows of ten thousand and sixty-four bitcoin in five days, and the price fell below 80 thousand 500 dollars. K33 links that to a wider move from risk. That is K33's assessment.",
 "s11": "Yle reports, via Finnish and Turkish media, that Richard Schueler, also known as Richard Heart, has been detained in Istanbul. He is a suspect in aggravated tax fraud, remanded in his absence in 2024. He has not been convicted.",
 "close": "That's all for issue number three. Every story, with a link to the original source, is at nordiccrypto.no. Nothing here is investment advice. From all of us: good night, from the Nordic Crypto team.",
}

TONIGHT = [
 ("SWEDEN", "Sweden's central bank asks parliament to prepare a possible digital krona", "digital krona"),
 ("NORWAY", "Norway argues over crypto mining at data centres", "data centres"),
 ("RULES", "New steps on stablecoins and crypto tax", "stablecoins"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "title", {}),
 ("open_b", "tonight", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "A possible digital krona, and a bank purchase"}),
 ("s1", "story", {}), ("s2", "story", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "Data centres, mining and tax"}),
 ("s3", "story", {}), ("s4", "story", {}), ("s5", "story", {}), ("s6", "story", {}),
 ("b_more", "section", {"label": "MORE NEWS", "sub": "Tokens, tax, bitcoin and a report from Finland"}),
 ("s7", "story", {}), ("s8", "story", {}), ("s9", "story", {}), ("s10", "story", {}), ("s11", "story", {}),
 ("close", "end", {}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE NUMBER THREE"
BUMPER_LEN = {"bumper": 5.5, "section": 2.0, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "KRONA"
THUMB_KICKER = "SWEDEN · ISSUE #3"
THUMB_HEAD = "A possible digital krona and Norway's data-centre mining dispute"
