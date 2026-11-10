"""On-screen and spoken content for Nordic Crypto #5 (26 Oct–1 Nov 2026).

Facts only from the editor-approved stories digest.py selects for this week.
Brand is Nordic Crypto. Presenter: the fictional anchor Anders Fjell (anchor-v1.jpg).
The sign-off card is "The Nordic Crypto team". Kaupr is named only as the source of its
own stories. The FBI's North Korea attribution stays attributed to the FBI. Investornytt's
"possible record hack" stays possible. Nothing on screen or in the narration says the
programme is made with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "nb-NO-FinnNeural"  # male Norwegian Bokmål; English script, Norwegian accent
RATE = "+22%"
NUMBER = "5"
ISSUE = "Issue #5"
ISSUE_RIBBON = "ISSUE #5"
DATES = "26 October–1 November 2026"
DATES_SHORT = "26 Oct–1 Nov 2026"
BUG_LINE = "ISSUE #5 · 26 OCT–1 NOV 2026"
SITE = site_url.HOST
LANG = "en"
ANCHOR = "Anders Fjell"
ANCHOR_ROLE = "NORDIC CRYPTO"
ANCHOR_IMG = "anchor-v1.jpg"
# Kinds where Anders is on camera. The shared lip-sync step refuses a still for these.
ON_CAMERA = ("anchor", "tonight", "story", "end")
TITLE_CARD = "NORDIC CRYPTO #5"

STORIES = {
 "s1": dict(section="NORWAY", head="Binance says about 90 percent of stolen assets are replaced",
            src="NRK (Norway) · 31 Oct", big="90%", kicker="REPLACED · NOT RETURNED", art="nodes", logo="nrk",
            news_id="ba58141d7134"),
 "s2": dict(section="NORWAY", head="FBI says North Korea's TraderTraitor was behind the Binance hack",
            src="E24 (Norway) · 30 Oct · may require a subscription", big="FBI", kicker="AN ATTRIBUTION · NOT A CONVICTION", art="scan", logo="e24",
            news_id="2ba8ad647f8e"),
 "s3": dict(section="NORWAY", head="Justice minister and Swedish experts concerned after the hack",
            src="Kaupr (Norway) · 30 Oct", big="NSM", kicker="PUBLIC SECURITY", art="globe", logo="kaupr",
            news_id="dd9efe763b0e"),
 "s4": dict(section="NORWAY", head="Binance confirms a loss of about 6.3 billion dollars",
            src="Investornytt (Norway) · 29 Oct", big="$6.3BN", kicker="POSSIBLE RECORD HACK", art="bars"),
 "s5": dict(section="NORWAY", head="Kautokeino: data-centre plot decided politically",
            src="Ságat (Norway) · 28 Oct · may require a subscription", big="PLOT", kicker="ARCTIC CORE STILL INVOLVED", art="nodes"),
 "s6": dict(section="NORWAY", head="VIALET to use tokenised funds via Axiology",
            src="Kaupr (Norway) · 27 Oct", big="FUNDS", kicker="BANK OF LITHUANIA SUPERVISES", art="globe", logo="kaupr"),
 "s7": dict(section="NORWAY", head="ESMA seeks input on tokenised collateral",
            src="Finanstilsynet (Norway) · 26 Oct", big="ESMA", kicker="OPEN UNTIL 15 JAN 2027", art="scan", logo="finanstilsynet"),
 "s8": dict(section="NORWAY", head="Latvia's minister aims for tokenisation rules in 2027",
            src="Kaupr (Norway) · 26 Oct", big="2027", kicker="A GOAL · NOT ADOPTED POLICY", art="globe", logo="kaupr"),
 "s9": dict(section="NORWAY", head="DTCC plans a tokenisation service for 25 securities",
            src="Kaupr (Norway) · 26 Oct", big="25", kicker="NOT CONFIRMED AS LIVE", art="bars", logo="kaupr"),
 "s10": dict(section="SWEDEN", head="Coinbase: third-quarter net income of 719 million dollars",
            src="hurbra (Sweden) · 30 Oct", big="$719M", kicker="MOSTLY CRYPTO GAINS", art="bars",
            news_id="821ef96a53e2"),
 "s11": dict(section="SWEDEN", head="Galaxy Digital: third-quarter net income of 323 million dollars",
            src="Kryptovalutaguiden (Sweden) · 29 Oct", big="$323M", kicker="AFTER A LOSS", art="bars", logo="kryptovalutaguiden"),
 "s12": dict(section="SWEDEN", head="FI seeks participants for a tokenised-money project",
            src="Finansinspektionen (Sweden) · 29 Oct", big="FI", kicker="GUIDANCE ON TOKENISED MONEY", art="globe", logo="se-fi"),
 "s13": dict(section="SWEDEN", head="Kryptos launches a ChatGPT plugin for portfolios",
            src="Kaupr (Sweden) · 29 Oct", big="GPT", kicker="CANNOT TRADE OR WITHDRAW", art="nodes", logo="kaupr"),
 "s14": dict(section="SWEDEN", head="Bitcoin Suisse prepares a Nordic launch",
            src="Kaupr (Sweden) · 29 Oct", big="MICA", kicker="PLANNED · EARLY NOVEMBER", art="globe", logo="kaupr"),
 "s15": dict(section="SWEDEN", head="GreenMerc reports unauthorised access at NorthCrypto",
            src="Kaupr (Sweden) · 28 Oct", big="DATA", kicker="KEYS NOT AFFECTED, FIRM SAYS", art="scan", logo="kaupr"),
 "s16": dict(section="SWEDEN", head="Zcash co-founder proposes ending automatic grant funding",
            src="Kryptovalutaguiden (Sweden) · 27 Oct", big="DRAFT", kicker="NO ACTIVATION DATE", art="stars", logo="kryptovalutaguiden"),
 "s17": dict(section="SWEDEN", head="Goobit presents a planned bitcoin-and-gold product",
            src="Kaupr (Sweden) · 26 Oct", big="GOLD", kicker="NOT INVESTMENT ADVICE", art="bars", logo="kaupr"),
 "s18": dict(section="DENMARK", head="Coop Bank opens read-only access for assistants",
            src="Kaupr (Denmark) · 28 Oct", big="READ", kicker="SHARES AND FUNDS · NOT CRYPTO", art="scan", logo="kaupr"),
}
END_DISCLOSURE = "Nothing here is investment advice."
TICKER = [
 "NORDIC CRYPTO · ISSUE #5 · " + DATES_SHORT.upper(),
 "Binance says about 90 percent of stolen assets have been replaced with its own funds (NRK)",
 "FBI says North Korea's TraderTraitor was behind the Binance theft. An attribution, not a conviction (E24)",
 "Norway's justice minister: cybersecurity can be a matter of public security (Kaupr)",
 "Binance confirms a loss of about 6.3 billion dollars. Investornytt called it a possible record hack",
 "Kautokeino: mayor says a data-centre plot was decided politically. Arctic Core still involved (Ságat)",
 "VIALET to use tokenised money-market funds via Axiology, Bank of Lithuania supervises (Kaupr)",
 "ESMA seeks evidence on tokenised collateral. Open until 15 January 2027 (Finanstilsynet)",
 "Latvia's economy minister aims for tokenisation rules in 2027. A goal, not adopted policy (Kaupr)",
 "DTCC plans a tokenisation service for 25 securities. Not confirmed as live (Kaupr)",
 "Coinbase: third-quarter net income about 719 million dollars, mostly crypto gains (hurbra)",
 "Galaxy Digital: third-quarter net income 323 million dollars (Kryptovalutaguiden)",
 "Finansinspektionen invites a reference group on tokenised money, including deposits and e-money tokens",
 "Kryptos launches a ChatGPT plugin. It cannot trade or withdraw, the firm says (Kaupr)",
 "Bitcoin Suisse Europe plans a Nordic launch in early November under its MiCA licence (Kaupr)",
 "GreenMerc: unauthorised access to customer data at NorthCrypto. Keys not affected, firm says (Kaupr)",
 "Zcash co-founder drafts an end to automatic community-grant funding. A draft only (Kryptovalutaguiden)",
 "Goobit presents planned Futureproof bitcoin-and-gold product. Not investment advice (Kaupr)",
 "Danish Coop Bank: read-only assistant access to investment accounts. Not crypto (Kaupr)",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good morning, I'm Anders Fjell, and this is Nordic Crypto.",
 "open_b": "This week: Binance says most stolen assets have been replaced. The FBI blames North Korea for the hack. And Sweden looks at tokenised money.",
 "s1": "Binance says about ninety percent of the stolen assets have been replaced with its own funds. The stolen coins are not back. NRK reported it.",
 "s2": "The FBI says North Korea was behind the theft of more than six billion dollars from Binance, under the name TraderTraitor. E24 reported the FBI's statement.",
 "s3": "Norway's justice minister told Aftenposten the theft shows cybersecurity can be a public-security matter. Kaupr reported that, and Swedish experts' concern.",
 "s4": "Binance confirms a loss of about six point three billion dollars, with about three billion frozen. Investornytt called it a possible record hack.",
 "s5": "In Kautokeino the mayor says a data-centre plot was decided politically, and Arctic Core is still involved, Ságat reports.",
 "s6": "Vialet says it will use tokenised money-market funds through Axiology, supervised by the Bank of Lithuania. Kaupr reported it.",
 "s7": "ESMA wants evidence on tokenised collateral at central counterparties, until the fifteenth of January. Finanstilsynet reported the call.",
 "s8": "Latvia's economy minister aims to have tokenisation rules in early 2027. That is a goal, not adopted policy. Kaupr reported it.",
 "s9": "DTCC plans a tokenisation service for twenty-five securities. Kaupr reported the plan. It is not confirmed as live.",
 "s10": "Coinbase reported third-quarter net income of about seven hundred and nineteen million dollars, mostly from crypto gains. Hurbra reported the figures.",
 "s11": "Galaxy Digital reported third-quarter net income of three hundred and twenty-three million dollars, after a loss. Kryptovalutaguiden reported it.",
 "s12": "Sweden's Finansinspektionen is inviting a reference group for guidance on tokenised money, including tokenised deposits and e-money tokens.",
 "s13": "Kryptos has launched a ChatGPT plugin for portfolio and tax questions. It cannot trade, Kryptos says. Kaupr reported the launch.",
 "s14": "Bitcoin Suisse Europe plans a Nordic launch in early November under its MiCA licence, Kaupr reports.",
 "s15": "GreenMerc says outsiders reached customer data at Finnish subsidiary NorthCrypto. Crypto keys were not affected, the company says. Kaupr reported it.",
 "s16": "Zcash co-founder Sean Bowe has drafted a plan to end automatic funding for community grants. It is a draft only. Kryptovalutaguiden reported the dispute.",
 "s17": "Goobit is presenting Futureproof, a planned bitcoin and gold product. Its return figures are its own, and this is not advice. Kaupr reported it.",
 "s18": "Coop Bank in Denmark lets customers connect an assistant to investment accounts, read only, the bank says. The accounts are not crypto. Kaupr reports that Bitpanda is opening portfolios to assistants too.",
 "close": "That's all for issue number five. Every story is at nordiccrypto.no. Nothing here is investment advice.",
 "signoff": "I'm Anders Fjell. See you next week.",
}

TONIGHT = [
 ("NORWAY", "Binance says most stolen assets have been replaced", "replaced"),
 ("NORWAY", "The FBI blames North Korea for the hack", "North Korea"),
 ("SWEDEN", "Sweden looks at tokenised money", "tokenised"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "anchor", {"lower_third": True}),
 ("open_b", "tonight", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "The Binance hack, and a data-centre plot"}),
 ("s1", "story", {}), ("s2", "story", {}), ("s3", "story", {}), ("s4", "story", {}), ("s5", "story", {}),
 ("s6", "story", {}), ("s7", "story", {}), ("s8", "story", {}), ("s9", "story", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "Markets, tokenised money and a data breach"}),
 ("s10", "story", {}), ("s11", "story", {}), ("s12", "story", {}), ("s13", "story", {}),
 ("s14", "story", {}), ("s15", "story", {}), ("s16", "story", {}), ("s17", "story", {}),
 ("b_dk", "section", {"label": "DENMARK", "sub": "A bank opens a read-only connection"}),
 ("s18", "story", {}),
 ("close", "end", {"fade": False}),
 ("signoff", "anchor", {"lower_third": True, "last": True}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE #5"
TONIGHT_LABEL = "THIS WEEK"
END_GREETING = "SEE YOU NEXT WEEK"
BUMPER_LEN = {"bumper": 4.5, "section": 1.6, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "90%"
THUMB_KICKER = "NORWAY · ISSUE #5"
THUMB_HEAD = "Binance says most stolen assets have been replaced"
