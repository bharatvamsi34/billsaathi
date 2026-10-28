from datetime import date

from fastapi.testclient import TestClient

from app.bbps_mock import MOCK_NOTICE, bills, service
from app.bbps_mock.registry import BILLERS
from app.main import app
from app.schemas import BillerCategory


def test_registry_has_eight_fictional_billers_across_six_categories():
    assert len(BILLERS) == 8
    assert len({b.biller_id for b in BILLERS}) == 8
    assert {b.category for b in BILLERS} == {
        BillerCategory.ELECTRICITY,
        BillerCategory.WATER,
        BillerCategory.GAS,
        BillerCategory.MOBILE_POSTPAID,
        BillerCategory.DTH,
        BillerCategory.BROADBAND,
    }
    for b in BILLERS:
        assert all(d.endswith(".example") for d in b.official_domains)
        assert all(v.endswith("@demobank") for v in b.official_vpas)
        assert all(p.startswith("1800") for p in b.official_phones)


def test_every_consumer_has_valid_number_current_bill_and_six_month_history():
    for b in BILLERS:
        consumers = service.consumers(b.biller_id)
        assert len(consumers) == bills.CONSUMERS_PER_BILLER
        for c in consumers:
            assert b.valid_consumer(c), (b.biller_id, c)
            history = service.bill_history(b.biller_id, c)
            current = service.current_bill(b.biller_id, c)
            assert len(history) == 6
            assert current not in history
            assert all(h.bill_date < current.bill_date for h in history)
            assert current.due_date > current.bill_date


def test_spike_bill_from_day1_spike_is_unchanged():
    bill = service.current_bill("DEMO00000MAH01", "DP-4410-882761")
    assert bill.amount == 1240.00
    assert bill.bill_date == date(2026, 10, 12)
    assert bill.due_date == date(2026, 11, 5)
    assert bill.bill_number == "DPB/2026/10/558213"


def test_spike_consumers_are_far_above_their_history():
    for biller_id, factor in bills.SPIKE_FACTORS.items():
        consumer = service.consumers(biller_id)[0]
        usual = sorted(h.amount for h in service.bill_history(biller_id, consumer))[2:4]
        assert service.current_bill(biller_id, consumer).amount > 2 * max(usual), factor


def test_generation_is_deterministic():
    assert bills._generate() == bills.BILLS


def test_consumer_lookup_ignores_spaces_and_dashes():
    assert service.current_bill("DEMO00000MAH01", " dp 4410 882761 ") is not None
    assert service.current_bill("DEMO00000MAH01", "DP-0000-000000") is None
    assert service.current_bill("NOPE", "DP-4410-882761") is None


def test_router_is_labelled_mock_and_serves_bills():
    client = TestClient(app)
    r = client.get("/api/v1/bbps-mock/billers")
    assert r.status_code == 200
    assert r.headers["X-Mock"] == MOCK_NOTICE
    assert len(r.json()["billers"]) == 8
    r = client.get("/api/v1/bbps-mock/bills/DEMO00000MAH01/DP-4410-882761")
    assert r.json()["amount"] == 1240.0
    assert (
        len(
            client.get("/api/v1/bbps-mock/bills/DEMO00000MAH01/DP-4410-882761/history").json()[
                "bills"
            ]
        )
        == 6
    )
    assert client.get("/api/v1/bbps-mock/bills/DEMO00000MAH01/DP-0000-000000").status_code == 404
    assert client.get("/api/v1/bbps-mock/billers/NOPE").status_code == 404
