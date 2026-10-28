"""SYNTHETIC threat-intel lists used by check_payment_destination.

The known-scam entries are invented for testing (all under .example or the fictional
@okdemo PSP). Link shorteners are real public services: a payment link hidden behind a
shortener is a risk signal on its own.
"""

KNOWN_SCAM_DOMAINS = frozenset(
    {
        "bijli-bill-refund.example",
        "kyc-update-portal.example",
        "electricity-office-pay.example",
        "vidyut-kyc.example",
        "gas-subsidy-refund.example",
    }
)

KNOWN_SCAM_VPAS = frozenset(
    {
        "electricityofficer@okdemo",
        "billupdate.refund@okdemo",
        "kyc.verify@okdemo",
    }
)

KNOWN_SCAM_PHONES = frozenset({"9876500001", "9876500002"})  # synthetic

URL_SHORTENERS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "is.gd",
        "cutt.ly",
        "rb.gy",
        "shorturl.at",
        "tiny.cc",
        "t.ly",
    }
)
