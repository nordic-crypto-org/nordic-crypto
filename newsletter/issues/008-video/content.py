"""On-screen and spoken content for Nordic Crypto #8 (16–22 Nov 2026).

Facts only from the editor-approved stories digest.py selects for this week.
Brand is Nordic Crypto. Presenter: the fictional anchor Anders Fjell (anchor-v1.jpg).
The sign-off card is "The Nordic Crypto team". Kaupr is named only as the source of its
own stories. Skatteetaten's figures are preliminary. ESMA's hearing is a consultation.
NBX has filed for a licence; it has not been granted. H100's Coinbase notice does not
launch an asset-management product. Realtid's sentence report is the paper's account;
the Justice Department text was not read for this report. H100's interim figures include
a one-off gain and have not been reviewed by the auditors. The Tenhult case is what the
police say; nobody has been arrested. The Huddlestock notice is a letter of intent.
The Optimizely sum is what Report URI said at one time. The K33 deal is conditional.
Lunar's transfer date is the bank's and Børsen's account. The ministers' letter has not
been published in full. Wagyu's claim about 1984 is unconfirmed.
Nothing on screen or in the narration says the programme is made with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "nb-NO-FinnNeural"  # male Norwegian Bokmål; English script, Norwegian accent
RATE = "+22%"
NUMBER = "8"
ISSUE = "Issue #8"
ISSUE_RIBBON = "ISSUE #8"
DATES = "16–22 November 2026"
DATES_SHORT = "16 Nov–22 Nov 2026"
BUG_LINE = "ISSUE #8 · 16 NOV–22 NOV 2026"
SITE = site_url.HOST
LANG = "en"
ANCHOR = "Anders Fjell"
ANCHOR_ROLE = "NORDIC CRYPTO"
ANCHOR_IMG = "anchor-v1.jpg"
# Kinds where Anders is on camera. The shared lip-sync step refuses a still for these.
ON_CAMERA = ("anchor", "tonight", "story", "end")
TITLE_CARD = "NORDIC CRYPTO #8"

STORIES = {
 "s1": dict(section="NORWAY", head="Skatteetaten: 89,600 people reported crypto holdings of 24.6 billion kroner",
            src="Skatteetaten (Norway) · 19 Nov", big="24.6BN", kicker="PRELIMINARY FIGURES · 2025", art="bars", logo="skatteetaten",
            news_id="a985949ee5e9"),
 "s2": dict(section="NORWAY", head="Finanstilsynet: ESMA invites a hearing on tokenised collateral",
            src="Finanstilsynet (Norway) · 18 Nov", big="ESMA", kicker="A CONSULTATION · NOT A NEW RULE", art="nodes", logo="finanstilsynet",
            news_id="038cf550661f"),
 "s3": dict(section="NORWAY", head="NBX has applied for a bank licence in Latvia. It is not granted",
            src="Kaupr (Norway) · 17 Nov", big="FILED", kicker="APPLICATION ONLY · KAUPR", art="globe", logo="kaupr",
            news_id="62e65a1a0595"),
 "s4": dict(section="NORWAY", head="H100 says it has a Coinbase Prime deal for its bitcoin",
            src="Finansavisen (Norway) · 16 Nov · may require a subscription", big="3,506", kicker="COMPANY NOTICE · NO NEW PRODUCT", art="bars", logo=None,
            news_id="57caa8eacf52"),
 "s5": dict(section="SWEDEN", head="Realtid: a six-year sentence in a US SIM-swap case",
            src="Realtid (Sweden) · 19 Nov", big="6 YRS", kicker="REALTID'S ACCOUNT · DOJ TEXT NOT READ", art="scan", logo="realtid",
            news_id="4b1832702295"),
 "s6": dict(section="SWEDEN", head="H100 says bitcoin per share rose 4.36 percent. Auditors have not reviewed it",
            src="Kaupr (Sweden) · 19 Nov", big="4.36%", kicker="ONE-OFF GAIN · NOT AUDITOR-REVIEWED", art="bars", logo="kaupr",
            news_id="f15fd3bf94dd"),
 "s7": dict(section="SWEDEN", head="Police: two people robbed of cryptocurrency in Tenhult",
            src="Omni (Sweden) · 18 Nov", big="CASE", kicker="POLICE SAY · NO ARREST", art="scan", logo=None,
            news_id="19c632406389"),
 "s8": dict(section="SWEDEN", head="Huddlestock and Firi sign a letter of intent, not a finished deal",
            src="Kaupr (Sweden) · 18 Nov", big="LOI", kicker="NOT A COMPLETED AGREEMENT · KAUPR", art="nodes", logo="kaupr",
            news_id="3c5e01e1f29b"),
 "s9": dict(section="SWEDEN", head="Malicious code via Optimizely reached about 178 organisations",
            src="Omni (Sweden) · 17 Nov", big="178", kicker="REPORT URI · ONE POINT IN TIME", art="scan", logo=None,
            news_id="69864861c878"),
 "s10": dict(section="SWEDEN", head="K33 agrees a conditional 13 million kronor deal",
            src="Kaupr (Sweden) · 16 Nov", big="13M", kicker="CONDITIONAL · KAUPR", art="bars", logo="kaupr",
            news_id="d41fe32b49d9"),
 "s11": dict(section="DENMARK", head="Lunar says it will sell its crypto customers and close Lunar Block",
            src="Børsen (Denmark) · 16 Nov · may require a subscription", big="CLOSE", kicker="BANK RELEASE · BØRSEN REPORTED IT", art="nodes", logo="borsen",
            news_id="ba1d824e5d76"),
 "s12": dict(section="FINLAND", head="Five ministers ask the EU to act on crypto used to evade sanctions",
            src="salkunrakentaja (Finland) · 16 Nov", big="EU", kicker="MINISTRY STATEMENT · LETTER NOT IN FULL", art="globe", logo=None,
            news_id="a475506ce16f"),
 "s13": dict(section="ICELAND", head="Icelandic host 1984 shut every service after an attack",
            src="Vísir (Iceland) · 20 Nov", big="SHUT", kicker="COMPANY SAYS · A CLAIM IS UNCONFIRMED", art="scan", logo=None,
            news_id="d8c5f2a584e6"),
}
END_DISCLOSURE = "Nothing here is investment advice."
TICKER = [
 "NORDIC CRYPTO · ISSUE #8 · " + DATES_SHORT.upper(),
 "Skatteetaten, preliminary: 89,600 people reported crypto holdings of NOK 24.6 billion for 2025",
 "ESMA invites a hearing on tokenised collateral. Finanstilsynet published the notice. It is a consultation",
 "NBX has applied for a Latvian banking licence. Filed, not granted. Kaupr reported the notice",
 "H100 says Coinbase Prime will custody, trade and finance its bitcoin. No asset-management product was launched",
 "Realtid: a six-year US sentence after a guilty plea in a Scattered Spider case. The DOJ text was not read here",
 "H100: bitcoin per share up 4.36 percent. The profit includes a one-off gain. Auditors have not reviewed it",
 "Swedish police: two people robbed of cryptocurrency in Tenhult. Nobody has been arrested",
 "Huddlestock and Firi: a letter of intent, not a completed agreement. Kaupr reported the notice",
 "Report URI: malicious code via Optimizely at about 178 organisations. About 7,040 dollars at one time",
 "K33 and Reverion: a conditional SEK 13 million agreement. It still needs a shareholder meeting",
 "Lunar says it is selling its crypto customers to Pluto.markets and closing Lunar Block. Børsen reported it",
 "Five foreign ministers ask the EU to act on crypto used to evade Russia sanctions. The letter is not published in full",
 "1984 ehf. shut every service after an attack, Vísir reports. A claim that a key leaked is unconfirmed",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good morning, I'm Anders Fjell, and this is Nordic Crypto.",
 "open_b": "This week: Skatteetaten says eighty-nine thousand six hundred people reported cryptocurrency holdings of twenty-four point six billion kroner. Realtid reports a six-year prison sentence in a United States SIM-swap case. And Lunar says it is selling its crypto customers and closing Lunar Block.",
 "s1": "According to preliminary figures from the Norwegian Tax Administration, Skatteetaten, for the twenty twenty-five income year, eighty-nine thousand six hundred people reported cryptocurrency holdings. The total reported value was twenty-four point six billion kroner. Skatteetaten says checks are being tightened. From twenty twenty-six, businesses that offer exchange and custody of cryptocurrency must report information to Skatteetaten.",
 "s2": "The European Securities and Markets Authority has published a call for evidence on tokenising collateral posted to central counterparties, Finanstilsynet said on the eighteenth of November. ESMA is inviting a public hearing on the seventh of January twenty twenty-seven, in Paris and online. Registration closes on the sixteenth of December twenty twenty-six, and written comments are due by the fifteenth of January twenty twenty-seven. This is a consultation, not a new rule.",
 "s3": "NBX has filed an application for a banking licence in Latvia for its wholly owned subsidiary, NBX Digital Asset Bank, in Riga, Kaupr reports, citing a stock exchange notice. The application is for a specialised credit institution. It has been filed, not granted. Latvijas Banka will ask for more information before the application counts as complete, and the European Central Bank grants the licence on the Latvian central bank's recommendation. NBX says operations could start at the earliest by the end of twenty twenty-seven, with twenty twenty-eight more likely.",
 "s4": "H100 Group has entered a partnership with Coinbase for institutional custody, trading and financing of its bitcoin, through Coinbase Prime and Deribit, according to a company notice on the sixteenth of November. Finansavisen reported the notice. The company says it holds about three thousand five hundred and six bitcoin. On its own price of sixty-four thousand six hundred dollars on the fifteenth of November, it valued those holdings at about two hundred and twenty-six million dollars. The notice describes a longer-term ambition to develop investor services. It does not say that an asset-management product has been launched.",
 "s5": "A twenty-four-year-old British man has been sentenced to six years in prison in the United States after pleading guilty to conspiracy to commit wire fraud and aggravated identity theft, as part of the group Scattered Spider, Realtid reported on the nineteenth of November. According to Realtid, the group used SMS phishing and SIM swapping, and cryptocurrency worth about one hundred and twenty million Swedish kronor was stolen. The paper, referring to the US Department of Justice, says at least twelve companies were affected, and that he is the fifth person sentenced in the US case. The official Justice Department text was not read for this report.",
 "s6": "In its interim report for the first nine months of twenty twenty-six, H100 Group says fully diluted bitcoin per share rose four point three six percent, Kaupr reports. Holdings went from about one thousand and fifty-one bitcoin to about three thousand four hundred and seventy-seven, after an acquisition and a loss of about thirty bitcoin in an active pool. Profit before tax was one hundred and forty-two point nine million kronor, including a one-off gain of one hundred and seventy-one million from that acquisition. Without that gain the result would have been negative. The report has not been reviewed by the company's auditors. The board has called a meeting on the seventh of December to seek authorisation for a share buyback. The company has not decided on a buyback.",
 "s7": "Swedish police were called to central Tenhult early on the eighteenth of November after two people were robbed of cryptocurrency in their home, according to a police summary for Jönköping County. Omni reported the summary. The police say the perpetrators assaulted one victim and, under threat, forced a transfer by computer, then bound the victims and left. Nobody has been arrested. The case is being investigated as aggravated robbery.",
 "s8": "Huddlestock Fintech has signed a letter of intent with the crypto exchange Firi for a tied-agent solution, Kaupr reports, citing a stock-exchange notice. It is a letter of intent, not a completed agreement, and it remains subject to further commercial, operational and regulatory assessment. As planned, Firi would become a tied agent under Huddlestock's licence. The release describes Firi as the largest crypto exchange in the Nordics, with about four hundred and thirty thousand retail customers.",
 "s9": "On the sixteenth of November, malicious JavaScript was served through Optimizely Web Experimentation to visitors of websites at about one hundred and seventy-eight organisations, including IKEA, according to Report URI and security researcher Scott Helme. Omni reported that account. The code swapped cryptocurrency wallet addresses and skimmed payment cards, among other things. Report URI said about seven thousand and forty dollars had reached the attackers' wallets by nineteen twenty-five UTC that day.",
 "s10": "K33 has entered a conditional agreement with Reverion Capital worth thirteen million Swedish kronor, Kaupr reports, citing a company notice. If it is completed, about twenty-six thousand K33 shareholders would receive Reverion shares worth five million kronor as a dividend in kind, and Reverion would issue an eight million kronor convertible loan to K33. The deal needs approval at an extraordinary general meeting, and either party may end it if the conditions are not met by the thirty-first of December twenty twenty-six.",
 "s11": "Lunar is selling its active crypto customer portfolio to the Danish platform Pluto dot markets, the bank said in a press release on the sixteenth of November. According to Børsen, Lunar is shutting down its crypto business, Lunar Block. Customers who hold crypto are to be transferred on the seventeenth of December twenty twenty-six.",
 "s12": "The foreign ministers of Finland, Denmark, Estonia, France and Lithuania are asking the European Union for stronger action against the use of crypto-assets to evade Russia sanctions, the Finnish Ministry for Foreign Affairs said on the sixteenth of November. They want the EU to target crypto networks that help sustain Russia's war economy, tighten enforcement, and close regulatory gaps. The letter itself has not been published in full. Salkunrakentaja reported the ministry.",
 "s13": "The Icelandic hosting company nineteen eighty-four temporarily shut down all of its services after a serious cyber attack, Vísir reported on the twentieth of November. The company said the systems were closed deliberately to stop the attack, and that it does not know whether any data were stolen. Wagyu, the issuer of the XMR1 token, claims that an issuing key stored on a deleted server there was leaked. That claim is unconfirmed.",
 "close": "That's all for issue number eight. Every story is at nordiccrypto.no. Nothing here is investment advice.",
 "signoff": "I'm Anders Fjell. See you next week.",
}

TONIGHT = [
 ("NORWAY", "Skatteetaten: 89,600 people reported crypto holdings", "Skatteetaten"),
 ("SWEDEN", "Realtid: a six-year sentence in a SIM-swap case", "Realtid"),
 ("DENMARK", "Lunar is closing Lunar Block", "Lunar"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "anchor", {"lower_third": True}),
 ("open_b", "tonight", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "A tax record, a hearing, and two notices"}),
 ("s1", "story", {}), ("s2", "story", {}), ("s3", "story", {}), ("s4", "story", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "A sentence, a robbery, and four notices"}),
 ("s5", "story", {}), ("s6", "story", {}), ("s7", "story", {}), ("s8", "story", {}), ("s9", "story", {}), ("s10", "story", {}),
 ("b_dk", "section", {"label": "DENMARK", "sub": "Lunar is closing its crypto business"}),
 ("s11", "story", {}),
 ("b_fi", "section", {"label": "FINLAND", "sub": "Ministers ask the EU to act"}),
 ("s12", "story", {}),
 ("b_is", "section", {"label": "ICELAND", "sub": "A host shuts every service"}),
 ("s13", "story", {}),
 ("close", "end", {"fade": False}),
 ("signoff", "anchor", {"lower_third": True, "last": True}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE #8"
TONIGHT_LABEL = "THIS WEEK"
END_GREETING = "SEE YOU NEXT WEEK"
BUMPER_LEN = {"bumper": 4.5, "section": 1.6, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "24.6BN"
THUMB_KICKER = "NORWAY · ISSUE #8"
THUMB_HEAD = "Skatteetaten: 89,600 people reported crypto holdings"
