"""On-screen and spoken content for Nordic Crypto #7 (9–15 Nov 2026).

Facts only from the editor-approved stories digest.py selects for this week.
Brand is Nordic Crypto. Presenter: the fictional anchor Anders Fjell (anchor-v1.jpg).
The sign-off card is "The Nordic Crypto team". Kaupr is named only as the source of its
own stories. A court authorisation is not a completed seizure, and an FBI attribution
stays the FBI's attribution. Flamman's company links stay the paper's findings.
Daniel Sonesson is charged and denies wrongdoing; that is not a conviction.
The 133 million dollar figure is Realtid's citation, which the bank has not confirmed.
The "fewer than one in six" share is what Yle reports the tax office says; it is not
confirmed in the authority's published notes. The Nationalbank paper is from April 2026.
Nothing on screen or in the narration says the programme is made with artificial intelligence.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import site_url
VOICE = "nb-NO-FinnNeural"  # male Norwegian Bokmål; English script, Norwegian accent
RATE = "+22%"
NUMBER = "7"
ISSUE = "Issue #7"
ISSUE_RIBBON = "ISSUE #7"
DATES = "9–15 November 2026"
DATES_SHORT = "9 Nov–15 Nov 2026"
BUG_LINE = "ISSUE #7 · 9 NOV–15 NOV 2026"
SITE = site_url.HOST
LANG = "en"
ANCHOR = "Anders Fjell"
ANCHOR_ROLE = "NORDIC CRYPTO"
ANCHOR_IMG = "anchor-v1.jpg"
# Kinds where Anders is on camera. The shared lip-sync step refuses a still for these.
ON_CAMERA = ("anchor", "tonight", "story", "end")
TITLE_CARD = "NORDIC CRYPTO #7"

STORIES = {
 "s1": dict(section="NORWAY", head="A US court has authorised seizure or freezing of more than 1.2 billion dollars",
            src="VG (Norway) · 13 Nov · may require a subscription", big="$1.2BN", kicker="DOJ STATEMENT · 12 NOVEMBER", art="bars", logo="vg",
            news_id="0eb8661e7db9"),
 "s2": dict(section="NORWAY", head="Axiology receives an expanded MiFID authorisation for tokenised funds",
            src="Kaupr (Norway) · 10 Nov", big="MIFID", kicker="THE COMPANY SAYS · KAUPR REPORTED IT", art="nodes", logo="kaupr",
            news_id="068db9ee437e"),
 "s3": dict(section="NORWAY", head="Norway will not treat crypto data centres as socially beneficial",
            src="Shifter (Norway) · 9 Nov · may require a subscription", big="2027", kicker="GOVERNMENT PRESS RELEASE · 9 NOV", art="scan", logo="shifter",
            news_id="be1f4058adbd"),
 "s4": dict(section="NORWAY", head="NBX and Aprikos Venture apply in Pakistan for Nayapaisa",
            src="Kaupr (Norway) · 9 Nov", big="NOC", kicker="NO CUSTOMERS UNTIL A LICENCE · KAUPR", art="globe", logo="kaupr",
            news_id="cc3ec8fc5a45"),
 "s5": dict(section="SWEDEN", head="Flamman reports payment links around the charged former Valuno chief",
            src="Flamman (Sweden) · 12 Nov · may require a subscription", big="CHARGE", kicker="NO CONVICTION · HE DENIES IT", art="scan", logo="flamman",
            news_id="a3c9ef21d13b"),
 "s6": dict(section="SWEDEN", head="Arkéa confirms a cyberattack. The bank has not confirmed the sum",
            src="Realtid (Sweden) · 9 Nov", big="ORDER", kicker="REALTID CITES ABOUT 133 MILLION", art="scan", logo="realtid",
            news_id="43033a5f3973"),
 "s7": dict(section="DENMARK", head="Børsen says uptake of the banks' crypto products is extremely limited",
            src="Børsen (Denmark) · 14 Nov · may require a subscription", big="LOW", kicker="APRIL PAPER · NOT A NEW SURVEY", art="bars", logo="borsen",
            news_id="4f78853ee799"),
 "s8": dict(section="FINLAND", head="Yle: fewer than one in six traders declare. The notes do not confirm it",
            src="Yle Uutiset (Finland) · 10 Nov", big="1 IN 6", kicker="YLE'S REPORT · NOT IN THE NOTES", art="scan", logo="yle",
            news_id="915342df6283"),
}
END_DISCLOSURE = "Nothing here is investment advice."
TICKER = [
 "NORDIC CRYPTO · ISSUE #7 · " + DATES_SHORT.upper(),
 "US Justice Department: a court has authorised seizure or freezing of more than 1.2 billion dollars stolen from Binance (VG)",
 "More than 2.7 billion dollars have already been frozen. The FBI attributes the theft to TraderTraitor (VG)",
 "Axiology says the Bank of Lithuania expanded its MiFID authorisation. Kaupr reported the company",
 "Norway: crypto data centres will not count as socially beneficial. Principles aimed for autumn 2027 (Shifter)",
 "NBX and Aprikos Venture have applied in Pakistan for Nayapaisa. No customers until a licence, Kaupr reports",
 "Flamman's own findings on payment links around Daniel Sonesson. He is charged and denies it. No conviction",
 "Crédit Mutuel Arkéa confirms a cyberattack. It has not confirmed Realtid's figure of about 133 million dollars",
 "Børsen: extremely limited interest in crypto products at Danske Bank and Nordea. The staff paper is from April",
 "Yle reports the Finnish tax office on declarations. That share is not in the authority's published notes",
 "All stories at " + SITE,
]

VO = {
 "open_a": "Good morning, I'm Anders Fjell, and this is Nordic Crypto.",
 "open_b": "This week: the US Justice Department says a court has authorised the seizure or freezing of more than one point two billion dollars stolen from Binance. The Norwegian government says data centres used for crypto will not count as socially beneficial. And Børsen reports extremely limited customer interest in crypto products at Danske Bank and Nordea.",
 "s1": "The US Department of Justice said on the twelfth of November that a court has authorised the seizure or freezing of more than one point two billion dollars in cryptocurrency stolen from Binance. More than two point seven billion dollars have already been frozen. The FBI attributes the theft to the group it calls TraderTraitor. That is the FBI's attribution. The same release also covers a separate scheme, FaceStealer, which is not a new Binance theft. VG reported the release.",
 "s2": "Lithuania's Axiology has received an expanded MiFID authorisation from the Bank of Lithuania, Kaupr reports, citing the company. The authorisation covers receiving, transmitting and executing client orders. Axiology says institutions can subscribe and redeem units in tokenised money-market funds through it. The firm already operates under the EU DLT Pilot Regime.",
 "s3": "The Norwegian government will start work on a licensing scheme for data centres. That is a press release on the ninth of November from the Ministry of Digitalisation and Public Governance and the Ministry of Energy, Shifter reports. The government said facilities used for crypto activity will not be treated as socially beneficial. It aims to present the main principles in the autumn of twenty twenty-seven. Statnett has separately paused new grid reservations for data centres.",
 "s4": "Norwegian Block Exchange and Aprikos Venture have signed a joint venture for a planned Pakistan exchange called Nayapaisa, Kaupr reports, citing the companies. They have applied to Pakistan's Virtual Assets Regulatory Authority for a No Objection Certificate. That application is a first step. The exchange will not serve customers until both the certificate and a licence are granted. The plan is deposits and withdrawals in Pakistani rupees through licensed Pakistani banks.",
 "s5": "According to Flamman's own investigation, companies and people around Valuno's former chief executive, Daniel Sonesson, have continued to operate in payments, including services used by online casinos. Those links are the paper's findings. Sweden's Economic Crime Authority has charged Sonesson with aggravated insider trading. He denies wrongdoing, according to Svenska Dagbladet. A charge is not a conviction.",
 "s6": "Crédit Mutuel Arkéa has confirmed a cyberattack through a service provider's platform, and said the funds may then have been converted into cryptocurrency. That is the bank's statement of the fourth of November, Realtid reports. Blockchain investigator ZachXBT first flagged large unauthorised withdrawals from crypto-exchange accounts. Realtid cites figures of about one hundred and thirty-three million dollars. The bank has not confirmed that amount. It said it could only validate the order of magnitude.",
 "s7": "Customer interest in crypto products at Danske Bank and Nordea has been extremely limited, Børsen reports, even though the banks have spoken of strong interest. A staff paper from Danmarks Nationalbank, dated the fifteenth of April twenty twenty-six, not a new November survey, found that household exposure to crypto in Denmark remains low. It noted that the two banks now offer crypto exchange-traded products. Danske Bank said on the eleventh of February that customers on its platform can invest in selected products that track bitcoin and ethereum.",
 "s8": "Yle reports that the Finnish tax office says fewer than one in six crypto traders in Finland declare their trades. That share has not been confirmed in the tax authority's published notes on the new reporting duty. From next year, the authority is due to receive data from Finnish and foreign crypto-asset service providers, according to Vero dot fi.",
 "close": "That's all for issue number seven. Every story is at nordiccrypto.no. Nothing here is investment advice.",
 "signoff": "I'm Anders Fjell. See you next week.",
}

TONIGHT = [
 ("NORWAY", "A US court order covers more than 1.2 billion dollars", "billion"),
 ("NORWAY", "Crypto data centres will not count as socially beneficial", "socially"),
 ("DENMARK", "Børsen: extremely limited interest at two banks", "Børsen"),
]

TIMELINE = [
 ("bumper", "bumper", {}),
 ("open_a", "anchor", {"lower_third": True}),
 ("open_b", "tonight", {}),
 ("b_no", "section", {"label": "NORWAY", "sub": "A court order, a licence, and two plans"}),
 ("s1", "story", {}), ("s2", "story", {}), ("s3", "story", {}), ("s4", "story", {}),
 ("b_se", "section", {"label": "SWEDEN", "sub": "A charge, a denial, and a bank statement"}),
 ("s5", "story", {}), ("s6", "story", {}),
 ("b_dk", "section", {"label": "DENMARK", "sub": "Extremely limited interest at two banks"}),
 ("s7", "story", {}),
 ("b_fi", "section", {"label": "FINLAND", "sub": "A share Yle reports, not in the notes"}),
 ("s8", "story", {}),
 ("close", "end", {"fade": False}),
 ("signoff", "anchor", {"lower_third": True, "last": True}),
]
SIGNOFF_CARD = "The Nordic Crypto team"
END_HEAD = "THAT'S ALL FOR ISSUE #7"
TONIGHT_LABEL = "THIS WEEK"
END_GREETING = "SEE YOU NEXT WEEK"
BUMPER_LEN = {"bumper": 4.5, "section": 1.6, "countries": 4.0}
THUMB_STORY = "s1"
THUMB_BIG = "$1.2BN"
THUMB_KICKER = "NORWAY · ISSUE #7"
THUMB_HEAD = "A US court order covers funds stolen from Binance"
