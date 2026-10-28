"""MOCK biller registry: 8 fictional billers and their official payment channels."""

import re

from pydantic import BaseModel, ConfigDict

from app.schemas import BillerCategory


class Biller(BaseModel):
    model_config = ConfigDict(frozen=True)

    biller_id: str
    name: str
    aliases: tuple[str, ...]
    category: BillerCategory
    state: str
    official_domains: tuple[str, ...]
    official_vpas: tuple[str, ...]
    official_phones: tuple[str, ...]  # digits only (toll-free)
    sms_sender_ids: tuple[str, ...]
    consumer_pattern: str  # regex for a valid consumer number
    bill_languages: tuple[str, ...]  # ISO 639-1, main language first

    def valid_consumer(self, consumer_number: str) -> bool:
        return re.fullmatch(self.consumer_pattern, consumer_number) is not None


BILLERS: tuple[Biller, ...] = (
    Biller(
        biller_id="DEMO00000MAH01",
        name="Demo Power Distribution Co. Ltd",
        aliases=("Demo Power", "DemoPower", "DPDCL", "डेमो पावर"),
        category=BillerCategory.ELECTRICITY,
        state="Maharashtra",
        official_domains=("demopower.example",),
        official_vpas=("demopower.bill@demobank",),
        official_phones=("18000001001",),
        sms_sender_ids=("VK-DEMOPW", "AD-DEMOPW"),
        consumer_pattern=r"DP-\d{4}-\d{6}",
        bill_languages=("en", "hi"),
    ),
    Biller(
        biller_id="SVSL00000TEL01",
        name="Sample Vidyut Seva Ltd",
        aliases=("Sample Vidyut", "SVSL", "శాంపిల్ విద్యుత్ సేవ"),
        category=BillerCategory.ELECTRICITY,
        state="Telangana",
        official_domains=("samplevidyut.example",),
        official_vpas=("samplevidyut@demobank",),
        official_phones=("18000001002",),
        sms_sender_ids=("VM-SVSLTD",),
        consumer_pattern=r"SVS\d{9}",
        bill_languages=("te", "en"),
    ),
    Biller(
        biller_id="EBNL00000UTP01",
        name="Example Bijli Nigam Ltd",
        aliases=("Example Bijli", "EBNL", "एग्ज़ाम्पल बिजली निगम"),
        category=BillerCategory.ELECTRICITY,
        state="Uttar Pradesh",
        official_domains=("examplebijli.example",),
        official_vpas=("examplebijli.pay@demobank",),
        official_phones=("18000001003",),
        sms_sender_ids=("VK-EBNLTD",),
        consumer_pattern=r"\d{10}",
        bill_languages=("hi", "en"),
    ),
    Biller(
        biller_id="EJBD00000DEL01",
        name="Example Jal Board",
        aliases=("Example Jal", "EJB", "एग्ज़ाम्पल जल बोर्ड"),
        category=BillerCategory.WATER,
        state="Delhi",
        official_domains=("examplejal.example",),
        official_vpas=("examplejal@demobank",),
        official_phones=("18000001004",),
        sms_sender_ids=("VK-EXMJAL",),
        consumer_pattern=r"EJB\d{8}",
        bill_languages=("en", "hi"),
    ),
    Biller(
        biller_id="DGAS00000GUJ01",
        name="DemoGas Ltd",
        aliases=("DemoGas", "Demo Gas"),
        category=BillerCategory.GAS,
        state="Gujarat",
        official_domains=("demogas.example",),
        official_vpas=("demogas.bill@demobank",),
        official_phones=("18000001005",),
        sms_sender_ids=("VK-DMOGAS",),
        consumer_pattern=r"BP\d{8}",
        bill_languages=("en",),
    ),
    Biller(
        biller_id="DMOB00000NAT01",
        name="Demo Mobile Postpaid",
        aliases=("Demo Mobile", "DemoMobile"),
        category=BillerCategory.MOBILE_POSTPAID,
        state="All India",
        official_domains=("demomobile.example",),
        official_vpas=("demomobile@demobank",),
        official_phones=("18000001006",),
        sms_sender_ids=("VM-DEMOMB",),
        consumer_pattern=r"DM\d{9}",
        bill_languages=("en",),
    ),
    Biller(
        biller_id="SKYD00000NAT01",
        name="SkyDemo DTH",
        aliases=("SkyDemo", "Sky Demo"),
        category=BillerCategory.DTH,
        state="All India",
        official_domains=("skydemo.example",),
        official_vpas=("skydemo.recharge@demobank",),
        official_phones=("18000001007",),
        sms_sender_ids=("VM-SKYDMO",),
        consumer_pattern=r"SD\d{9}",
        bill_languages=("en",),
    ),
    Biller(
        biller_id="FIBR00000KAR01",
        name="FiberDemo Broadband",
        aliases=("FiberDemo", "Fiber Demo"),
        category=BillerCategory.BROADBAND,
        state="Karnataka",
        official_domains=("fiberdemo.example",),
        official_vpas=("fiberdemo@demobank",),
        official_phones=("18000001008",),
        sms_sender_ids=("VM-FIBRDM",),
        consumer_pattern=r"FD\d{8}",
        bill_languages=("en",),
    ),
)

BY_ID: dict[str, Biller] = {b.biller_id: b for b in BILLERS}
