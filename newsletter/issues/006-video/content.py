"""On-screen and spoken content for Nordic Crypto #6 (2–8 Nov 2026).

Facts only from the editor-approved stories digest.py selects for this week.
Brand is Nordic Crypto. Presenter: the fictional anchor Anders Fjell (anchor-v1.jpg).
The sign-off card is "The Nordic Crypto team". Kaupr is named only as the source of its
own stories. North Korea's denial stays North Korea's position. The Valuno charges are
charges, not a conviction. The Ulricehamn excerpt does not establish a charge or a conviction.
Nothing on screen or in the narration says the programme is made with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "en-GB-ThomasNeural"
RATE = "+22%"
NUMBER = "6"
ISSUE = "Issue #6"
ISSUE_RIBBON = "ISSUE #6"
DATES = "2–8 November 2026"
DATES_SHORT = "2 Nov–8 Nov 2026"
BUG_LINE = "ISSUE #6 · 2 NOV–8 NOV 2026"
SITE = site_url.HOST
LANG = "en"
ANCHOR = "Anders Fjell"
ANCHOR_ROLE = "NORDIC CRYPTO"
ANCHOR_IMG = "anchor-v1.jpg"
# Kinds where Anders is on camera. The shared lip-sync step refuses a still for these.
ON_CAMERA = ("anchor", "tonight", "story", "end")
TITLE_CARD = "NORDIC CRYPTO #6"

STORIES = {
 "s1": dict(section="NORWAY", head="Binance reports net outflows of about 3.64 billion dollars",
            src="E24 (Norway) · 2 Nov · may require a subscription", big="$3.64BN", kicker="BINANCE'S FIGURES · AFTER THE HACK", art="bars", logo="e24",
            news_id="4525f8afaf7b"),
 "s2": dict(section="NORWAY", head="North Korea rejects the FBI's attribution of the Binance hack",
            src="Aftenposten (Norway) · 2 Nov · may require a subscription", big="DENIAL", kicker="THEIR STATEMENT · NOT A FINDING", art="scan", logo="aftenposten",
            news_id="4e239c7ceaf9"),
 "s3": dict(section="NORWAY", head="Trading at Firi more than doubled the day after the hack",
            src="E24 (Norway) · 4 Nov · may require a subscription", big="2×", kicker="FIGURES FIRI SHARED WITH E24", art="bars", logo="e24",
            news_id="6a0bc0c01d46"),
 "s4": dict(section="NORWAY", head="Norges Bank sees no current need for a retail digital currency",
            src="Kaupr (Norway) · 5 Nov", big="READY", kicker="WANTS TO BE PREPARED", art="globe", logo="kaupr",
            news_id="ec86f5175ea7"),
 "s5": dict(section="NORWAY", head="Norges Bank official urges banks to plan for tokenisation",
            src="Kaupr (Norway) · 5 Nov", big="BANKS", kicker="CENTRAL BANK MONEY FOR SETTLEMENT", art="nodes", logo="kaupr",
            news_id="465eb25f04a6"),
 "s6": dict(section="NORWAY", head="NBX has raised at least 34 million kroner from LDA Capital",
            src="Kaupr (Norway) · 3 Nov", big="34M", kicker="KAUPR'S COUNT OF SHARE ISSUES", art="bars", logo="kaupr",
            news_id="ee816a083fda"),
 "s7": dict(section="NORWAY", head="Hyperliquid's founder wants US traders via regulated partners",
            src="Investornytt (Norway) · 3 Nov", big="$713M", kicker="REVENUE CITED FROM BLOOMBERG", art="globe",
            news_id="8b6d4ef4e175"),
 "s8": dict(section="SWEDEN", head="Safello reports a small third-quarter operating profit",
            src="Kaupr (Sweden) · 6 Nov", big="0.8M", kicker="SEK · FIGURES VIA KAUPR", art="bars", logo="kaupr",
            news_id="2432bee6d799"),
 "s9": dict(section="SWEDEN", head="Paper reports crypto transfers in a romance scam",
            src="Ulricehamns Tidning (Sweden) · 5 Nov · may require a subscription", big="1.5M", kicker="NO CHARGE ESTABLISHED IN THE EXCERPT", art="scan", logo="ulricehamns-tidning",
            news_id="baba2f9c8906"),
 "s10": dict(section="SWEDEN", head="Virtune lists an AI crypto index ETP in Stockholm and on Xetra",
            src="Kaupr (Sweden) · 4 Nov", big="ETP", kicker="LISTED 3 NOVEMBER · KAUPR", art="nodes", logo="kaupr",
            news_id="9248a4954c15"),
 "s11": dict(section="SWEDEN", head="Objections to tokenised shares rise to 56 companies",
            src="Kryptovalutaguiden (Sweden) · 3 Nov", big="56", kicker="TESLA AND SPACEX AMONG THEM", art="scan", logo="kryptovalutaguiden",
            news_id="e36f90afacd8"),
 "s12": dict(section="SWEDEN", head="Firi extends temporary lay-offs until March 2027",
            src="Kaupr (Sweden) · 3 Nov", big="2027", kicker="THE FIRM SAYS TRADING IS LOWER", art="bars", logo="kaupr",
            news_id="60bdd64f457a"),
 "s13": dict(section="SWEDEN", head="Two former Valuno executives charged with insider trading",
            src="Kaupr (Sweden) · 3 Nov", big="CHARGE", kicker="NO CONVICTION · ONE DENIES IT", art="scan", logo="kaupr",
            news_id="9ce6e4d42086"),
 "s14": dict(section="SWEDEN", head="Goobit signs a gold agreement for its planned platform",
            src="Kaupr (Sweden) · 2 Nov", big="GOLD", kicker="GOOBIT SAYS THE GOLD IS BACKED", art="globe", logo="kaupr",
            news_id="4e5e466813f0"),
 "s15": dict(section="DENMARK", head="Binance says hackers used a fake job interview",
            src="DR (Denmark) · 3 Nov", big="FAKE", kicker="BINANCE'S ACCOUNT · DR REPORTED IT", art="scan", logo="dr-penge",
            news_id="f47e76863444"),
}
END_DISCLOSURE = "Nothing here is investment advice."
TICKER = [
 "NORDIC CRYPTO · ISSUE #6 · " + DATES_SHORT.upper(),
 "Binance reports net outflows of about 3.64 billion dollars after withdrawals reopened (E24)",
 "North Korea rejects the FBI's attribution. That is their statement, not a new finding (Aftenposten)",
 "Firi trading more than doubled the day after the hack, the exchange told E24",
 "Norges Bank sees no current need for a retail digital currency, and wants to be ready (Kaupr)",
 "Norges Bank's Hægeland urges banks to prepare a tokenisation strategy (Kaupr)",
 "NBX has raised at least 34 million kroner from LDA Capital, by Kaupr's count",
 "Hyperliquid: 713 million dollars of revenue in 12 months, Investornytt reports, citing Bloomberg",
 "Safello reports a third-quarter operating profit of 0.8 million Swedish kronor (Kaupr)",
 "Ulricehamns Tidning reports crypto transfers in a romance scam. No charge is established in the excerpt",
 "Virtune listed an AI crypto index ETP on 3 November, Kaupr reports",
 "Objections to tokenised shares on OKXICE now include Tesla and SpaceX. The count is 56 (Kryptovalutaguiden)",
 "Firi says temporary lay-offs run until the end of March 2027 (Kaupr)",
 "Two former Valuno executives are charged with aggravated insider trading. No conviction (Kaupr)",
 "Goobit says Kvarn Metals will be the gold counterparty for Futureproof (Kaupr)",
 "Binance says the hack began with a fake job interview. DR reported the exchange's account",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good morning, I'm Anders Fjell, and this is Nordic Crypto.",
 "open_b": "This week: Binance reports net outflows of three point six four billion dollars. North Korea rejects the FBI's attribution. And Norges Bank says it wants to be ready if a digital currency is needed.",
 "s1": "Binance says customers withdrew a net of about three point six four billion dollars on the first of November, after withdrawals reopened. E24 reported the exchange's figures.",
 "s2": "North Korea rejects the FBI's statement that it was behind the Binance theft. Aftenposten reports a statement calling the claim an absurd fabrication. That is North Korea's position, not a new finding.",
 "s3": "At Norwegian exchange Firi, trading the day after the hack was more than double a typical day, according to figures the firm shared with E24. The chief executive says it is too early to call it a lasting shift.",
 "s4": "Norges Bank sees no current need for a retail digital currency, but wants to be ready if that changes. Torbjørn Hægeland told a conference, Kaupr reports. A digital euro would not by itself decide it, he said.",
 "s5": "The same official said banks should prepare a tokenisation strategy, and that important settlement should use central bank money. Kaupr reported the speech.",
 "s6": "Norwegian exchange NBX has raised at least thirty-four million kroner from LDA Capital since 2022, by Kaupr's count of the company's own announcements. The latest issue closed on the third of November.",
 "s7": "Investornytt reports that Hyperliquid took in seven hundred and thirteen million dollars over twelve months, citing Bloomberg Businessweek. Founder Jeff Yan wants to reach US traders through regulated partners.",
 "s8": "Safello reported a third-quarter operating profit of zero point eight million Swedish kronor, Kaupr reports from the company's figures. Revenue fell forty-one percent.",
 "s9": "Ulricehamns Tidning reports that one point five million Swedish kronor in crypto was transferred in a romance scam. The public excerpt does not establish that anyone has been charged or convicted.",
 "s10": "Virtune listed an AI crypto index ETP on the third of November, in Stockholm and on Xetra, Kaupr reports. Its sales chief called software agents a growth driver. That is the company's view.",
 "s11": "Tesla, SpaceX and others have objected to their shares being offered as tokens on OKXICE. Kryptovalutaguiden reported it. By CoinDesk's tally, the number of objections rose to fifty-six.",
 "s12": "Firi says the temporary lay-offs it announced in August will last until the end of March 2027. Chief executive Thuc Hoang told Kaupr that trading this year has been lower than planned.",
 "s13": "Sweden's Economic Crime Authority has charged two former Valuno executives with aggravated insider trading, Kaupr reports. No one has been convicted. The former chief executive denies wrongdoing, according to SvD.",
 "s14": "Goobit has signed an agreement with Kvarn Metals for gold in its planned Futureproof platform, the company told Kaupr. Goobit says the gold is backed one to one by physical gold.",
 "s15": "Binance says the attackers used a fake job interview in September, then misused an internal tool on an engineer's laptop. DR reported the exchange's account, and that Binance says most of the losses have been covered.",
 "close": "That's all for issue number six. Every story is at nordiccrypto.no. Nothing here is investment advice.",
 "signoff": "I'm Anders Fjell. See you next week.",
}

TONIGHT = [
 ("NORWAY", "Binance reports 3.64 billion dollars in net outflows", "outflows"),
 ("NORWAY", "North Korea rejects the FBI's attribution", "rejects"),
 ("NORWAY", "Norges Bank wants to be ready", "ready"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "anchor", {"lower_third": True}),
 ("open_b", "tonight", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "Outflows, a denial, and the central bank"}),
 ("s1", "story", {}), ("s2", "story", {}), ("s3", "story", {}), ("s4", "story", {}),
 ("s5", "story", {}), ("s6", "story", {}), ("s7", "story", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "Results, charges and a gold agreement"}),
 ("s8", "story", {}), ("s9", "story", {}), ("s10", "story", {}), ("s11", "story", {}),
 ("s12", "story", {}), ("s13", "story", {}), ("s14", "story", {}),
 ("b_dk", "section", {"label": "DENMARK", "sub": "Binance describes the path into the hack"}),
 ("s15", "story", {}),
 ("close", "end", {"fade": False}),
 ("signoff", "anchor", {"lower_third": True, "last": True}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE #6"
TONIGHT_LABEL = "THIS WEEK"
END_GREETING = "SEE YOU NEXT WEEK"
BUMPER_LEN = {"bumper": 4.5, "section": 1.6, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "$3.64BN"
THUMB_KICKER = "NORWAY · ISSUE #6"
THUMB_HEAD = "Binance reports net outflows after the hack"
