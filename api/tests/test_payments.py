"""Sandbox pay: SAFE only, explicit confirmation, idempotent, every attempt audited."""

import json
import sqlite3

import pytest
from fakes import turn
from test_api_checks import GENUINE, SCAM, api, cite_all, post_text  # noqa: F401

from app.main import app
from app.payments import PaymentStore

KEY = {"Idempotency-Key": "key-0000-0001"}


def pay(client, check_id, headers=KEY, confirm=True):
    return client.post(f"/api/v1/checks/{check_id}/pay", json={"confirm": confirm}, headers=headers)


def safe_check(client, install):
    install(GENUINE, [cite_all("SAFE")])
    return post_text(client, GENUINE.input.text).json()["check_id"]


def audit():
    return app.state.payments.audit_rows()


def test_safe_check_pays_with_a_sandbox_receipt(api):  # noqa: F811
    client, install = api
    check_id = safe_check(client, install)
    r = pay(client, check_id)
    assert r.status_code == 200 and r.json()["replayed"] is False
    receipt = r.json()["receipt"]
    assert receipt["sandbox"] is True and receipt["status"] == "SANDBOX_SUCCESS"
    assert "no real money" in receipt["note"]
    assert receipt["receipt_id"].startswith("SBX-")
    assert receipt["amount"] == GENUINE.expected.extracted.amount
    assert receipt["biller_id"] == "DEMO00000MAH01"
    consumer = GENUINE.expected.extracted.consumer_number
    assert consumer not in json.dumps(receipt)
    assert receipt["consumer_masked"].endswith(consumer[-4:])
    rows = audit()
    assert [(a["action"], a["outcome"]) for a in rows] == [("pay", "sandbox_paid")]
    assert rows[0]["id"] == receipt["audit_id"] and consumer not in rows[0]["detail"]


def test_same_key_returns_the_same_receipt_and_never_pays_twice(api):  # noqa: F811
    client, install = api
    check_id = safe_check(client, install)
    first = pay(client, check_id).json()
    again = pay(client, check_id).json()
    assert again["replayed"] is True and again["receipt"] == first["receipt"]
    other_key = pay(client, check_id, {"Idempotency-Key": "key-0000-0002"}).json()
    assert other_key["replayed"] is True and other_key["receipt"] == first["receipt"]
    assert [a["outcome"] for a in audit()] == ["sandbox_paid", "replayed", "replayed"]


def test_a_key_cannot_be_reused_for_another_check(api):  # noqa: F811
    client, install = api
    assert pay(client, safe_check(client, install)).status_code == 200
    second = safe_check(client, install)
    r = pay(client, second)
    assert r.status_code == 409 and r.json()["error"] == "key_reused"
    assert audit()[-1]["outcome"] == "refused"


def test_scam_verdict_is_refused_and_audited(api):  # noqa: F811
    client, install = api
    install(SCAM, [cite_all("SCAM")])
    check_id = post_text(client, SCAM.input.text).json()["check_id"]
    r = pay(client, check_id)
    assert r.status_code == 409 and r.json()["error"] == "not_safe"
    rows = audit()
    assert [(a["outcome"], json.loads(a["detail"])["code"]) for a in rows] == [
        ("refused", "not_safe")
    ]


def test_waiting_and_forced_checks_are_refused(api):  # noqa: F811
    client, install = api
    install(GENUINE, [turn(("ask_user", {"field": "consumer_number", "question": "Number?"}))])
    check_id = post_text(client, GENUINE.input.text).json()["check_id"]
    assert pay(client, check_id).json()["error"] == "not_finished"  # waiting for the user
    client.post(f"/api/v1/checks/{check_id}/answer", json={"answer": ""})
    assert pay(client, check_id).json()["error"] == "not_safe"  # no answer: forced CAUTION


def test_confirmation_and_key_are_required(api):  # noqa: F811
    client, install = api
    check_id = safe_check(client, install)
    assert pay(client, check_id, confirm=False).json()["error"] == "confirmation_required"
    assert pay(client, check_id, headers={}).json()["error"] == "idempotency_key_required"
    assert [a["outcome"] for a in audit()] == ["refused", "refused"]
    assert pay(client, check_id).status_code == 200  # the refused attempts paid nothing


def test_unknown_check_is_404(api):  # noqa: F811
    client, install = api
    install(GENUINE, [])
    assert pay(client, "nope").status_code == 404


def test_the_database_refuses_changes_to_the_audit_log():
    store = PaymentStore(":memory:")
    build = lambda: {"receipt_id": "R", "biller_id": "B", "consumer_masked": "*", "amount": 1.0}  # noqa: E731
    store.pay("c1", "key-00000001", build)
    store.pay("c1", "key-00000001", build)
    with pytest.raises(sqlite3.IntegrityError):
        store._db.execute("UPDATE audit_log SET outcome = 'x'")
    with pytest.raises(sqlite3.IntegrityError):
        store._db.execute("DELETE FROM audit_log")
    rows = store.audit_rows()
    assert rows[0]["prev_hash"] == "genesis" and rows[1]["prev_hash"] == rows[0]["hash"]
