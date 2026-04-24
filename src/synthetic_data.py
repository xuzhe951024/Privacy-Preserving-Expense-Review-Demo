from __future__ import annotations

import json
import random
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from src.ground_truth_schema import build_ground_truth_schema
from src.models import DetectedEntity, ExpenseSample
from src.policy import get_entity_policy
from src.report_writer import write_json, write_jsonl, write_markdown

PEOPLE = [
    ("John Miller", "+1-617-555-0142"),
    ("Ava Thompson", "+1-646-555-0131"),
    ("Marcus Reed", "+1-415-555-0186"),
    ("Priya Shah", "+1-312-555-0191"),
    ("Elena Garcia", "+1-206-555-0174"),
    ("Daniel Chen", "+1-408-555-0163"),
    ("Sarah Brooks", "+1-718-555-0152"),
    ("Noah Patel", "+1-202-555-0118"),
]

RESTAURANTS = [
    "Harbor Grill",
    "North Point Kitchen",
    "Slate & Fork",
    "Oakline Bistro",
]

HOTELS = [
    "Hilton Garden Inn",
    "Marriott Waterfront",
    "Motel 6 Downtown",
    "Embassy Suites Midtown",
]

AIRLINES = [
    "Delta Air Lines",
    "United Airlines",
    "JetBlue",
    "Alaska Airlines",
]

TRANSPORT = [
    "Uber Business",
    "Lyft Corporate",
    "Metro Black Car",
    "Airport Taxi Cooperative",
]

SOFTWARE_VENDORS = [
    "Atlassian",
    "Slack",
    "Notion",
    "Figma",
]

PROJECT_CODES = ["PC-ALPHA-204", "PC-NOVA-117", "PC-POLARIS-336", "PC-ORBIT-518"]
COST_CENTERS = ["CC-410", "CC-275", "CC-612", "CC-730"]
CLIENTS = ["Acme Retail", "Beacon Capital", "Northwind Energy", "Solstice Labs"]


class TemplateBuilder:
    def __init__(self) -> None:
        self._parts: list[tuple[str, str, dict[str, Any] | None]] = []

    def text(self, value: str) -> None:
        self._parts.append(("text", value, None))

    def entity(
        self,
        label: str,
        value: str,
        normalized_value: str | None = None,
        sensitivity_level: str = "high",
        expected_action: str | None = None,
    ) -> None:
        action = expected_action or get_entity_policy(label).get("action", "tokenize_encrypt")
        self._parts.append(
            (
                "entity",
                value,
                {
                    "label": label,
                    "normalized_value": normalized_value,
                    "sensitivity_level": sensitivity_level,
                    "expected_action": action,
                },
            )
        )

    def build(self) -> tuple[str, list[DetectedEntity]]:
        chunks: list[str] = []
        entities: list[DetectedEntity] = []
        cursor = 0
        entity_count = 0
        for kind, value, meta in self._parts:
            start = cursor
            chunks.append(value)
            cursor += len(value)
            if kind == "entity" and meta is not None:
                entity_count += 1
                entities.append(
                    DetectedEntity(
                        entity_id=f"e{entity_count}",
                        label=meta["label"],
                        text=value,
                        start=start,
                        end=cursor,
                        normalized_value=meta["normalized_value"],
                        sensitivity_level=meta["sensitivity_level"],
                        expected_action=meta["expected_action"],
                    )
                )
        return "".join(chunks), entities


def amount_text(value: float) -> str:
    return f"${value:,.2f}"


def amount_normalized(value: float) -> str:
    return f"{value:.2f}"


def cents_from_amount(value: float) -> int:
    return int(round(value * 100))


def epoch_days_from_date(value: date) -> int:
    return (value - date(1970, 1, 1)).days


def contact_email(name: str) -> str:
    local_part = name.lower().replace(" ", ".")
    return f"{local_part}@corp.example"


def next_sample_id(index: int) -> str:
    return f"exp_{index + 1:04d}"


def base_context(
    expense_type: str,
    policy_key: str | None,
    amount_total_cents: int | None,
    record_date: date,
    **extra: Any,
) -> dict[str, Any]:
    context = {
        "workflow_type": "expense_review",
        "expense_type": expense_type,
        "currency": "USD",
        "policy_key": policy_key,
        "receipt_attached": True,
        "requires_sum": False,
        "requires_cap_validation": bool(policy_key),
    }
    context.update(extra)
    return context


def compare_policy_expectation(
    entity_id: str,
    policy_key: str,
    amount_cents: int,
    cap_cents: int | None,
) -> list[dict[str, Any]]:
    if cap_cents is None:
        return [
            {
                "op": "compare_policy_cap",
                "left_entity_id": entity_id,
                "right_policy_key": policy_key,
                "expected_result": "needs_human_review",
                "expected_delta_usd": None,
            }
        ]
    delta_cents = amount_cents - cap_cents
    if delta_cents > 0:
        expected_result = "exceeds"
    elif delta_cents == 0:
        expected_result = "within_cap"
    else:
        expected_result = "within_cap"
    return [
        {
            "op": "compare_policy_cap",
            "left_entity_id": entity_id,
            "right_policy_key": policy_key,
            "expected_result": expected_result,
            "expected_delta_usd": f"{abs(delta_cents) / 100:.2f}",
        }
    ]


def _pick_identity(rng: random.Random) -> tuple[str, str, str]:
    name, phone = rng.choice(PEOPLE)
    email = contact_email(name)
    return name, phone, email


def _pick_common_fields(rng: random.Random, sample_index: int) -> dict[str, str]:
    project_code = rng.choice(PROJECT_CODES)
    cost_center = rng.choice(COST_CENTERS)
    employee_digits = 4000 + (sample_index % 5000)
    invoice_suffix = 40 + sample_index
    return {
        "employee_id": f"E-{employee_digits:04d}",
        "project_code": project_code,
        "cost_center": cost_center,
        "invoice_id": f"INV-2026-{invoice_suffix:04d}",
        "card_last4": f"{(4800 + sample_index) % 10000:04d}",
    }


def build_client_dinner(sample_index: int, rng: random.Random, amount: float | None = None) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    vendor = rng.choice(RESTAURANTS)
    client = rng.choice(CLIENTS)
    expense_date = date(2026, 4, 10) + timedelta(days=sample_index % 12)
    chosen_amount = amount if amount is not None else rng.choice([430.00, 450.00, 482.15, 512.40])

    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" submitted a client dinner expense on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(". Employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(". Vendor ")
    builder.entity("VENDOR", vendor, normalized_value=vendor, sensitivity_level="medium")
    builder.text(" charged ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(" to corporate card ending ")
    builder.entity("CARD_LAST4", common["card_last4"], normalized_value=common["card_last4"])
    builder.text(". Receipt note: dinner with ")
    builder.text(client)
    builder.text(" for project ")
    builder.entity("PROJECT_CODE", common["project_code"], normalized_value=common["project_code"])
    builder.text(", cost center ")
    builder.entity("COST_CENTER", common["cost_center"], normalized_value=common["cost_center"])
    builder.text(", invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(". Follow-up contact: ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(" or ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    amount_entity = next(entity for entity in entities if entity.label == "AMOUNT")
    amount_cents = cents_from_amount(chosen_amount)
    expected_decision = "needs_manager_approval" if amount_cents > 45_000 else "auto_approve"
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation(amount_entity.entity_id or "e1", "meal_cap_usd", amount_cents, 45_000),
        expected_final_decision=expected_decision,
        expected_missing_items=[],
        edge_case_tags=["single_amount", "client_dinner"] + (["over_cap"] if amount_cents > 45_000 else ["within_cap"]),
        workflow_context=base_context("client_dinner", "meal_cap_usd", amount_cents, expense_date, client_name=client),
    )


def build_hotel_booking(sample_index: int, rng: random.Random, vendor: str | None = None) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    hotel = vendor or rng.choice(HOTELS)
    expense_date = date(2026, 4, 1) + timedelta(days=sample_index % 18)
    chosen_amount = rng.choice([612.40, 640.00, 701.25])
    note = "client workshop stay"

    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" booked hotel ")
    builder.entity("VENDOR", hotel, normalized_value=hotel, sensitivity_level="medium")
    builder.text(" on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(" for ")
    builder.text(note)
    builder.text(". Booking amount ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(", employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(", project ")
    builder.entity("PROJECT_CODE", common["project_code"], normalized_value=common["project_code"])
    builder.text(", cost center ")
    builder.entity("COST_CENTER", common["cost_center"], normalized_value=common["cost_center"])
    builder.text(", card ending ")
    builder.entity("CARD_LAST4", common["card_last4"], normalized_value=common["card_last4"])
    builder.text(". Contact ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(" or ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    amount_entity = next(entity for entity in entities if entity.label == "AMOUNT")
    amount_cents = cents_from_amount(chosen_amount)
    expected_decision = "needs_manager_approval" if amount_cents > 65_000 else "auto_approve"
    tags = ["hotel_booking", "single_amount"]
    if "Motel 6" in hotel:
        tags.append("vendor_contains_number")
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation(amount_entity.entity_id or "e1", "hotel_cap_usd", amount_cents, 65_000),
        expected_final_decision=expected_decision,
        expected_missing_items=[],
        edge_case_tags=tags,
        workflow_context=base_context("hotel_booking", "hotel_cap_usd", amount_cents, expense_date),
    )


def build_airfare(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    airline = rng.choice(AIRLINES)
    expense_date = date(2026, 3, 28) + timedelta(days=sample_index % 15)
    chosen_amount = rng.choice([820.00, 1150.35, 1388.70])

    builder = TemplateBuilder()
    builder.text("Traveler ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" filed airfare for ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(". Carrier ")
    builder.entity("VENDOR", airline, normalized_value=airline, sensitivity_level="medium")
    builder.text(". Ticket cost ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(". Employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(", project ")
    builder.entity("PROJECT_CODE", common["project_code"], normalized_value=common["project_code"])
    builder.text(", cost center ")
    builder.entity("COST_CENTER", common["cost_center"], normalized_value=common["cost_center"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    amount_entity = next(entity for entity in entities if entity.label == "AMOUNT")
    amount_cents = cents_from_amount(chosen_amount)
    expected_decision = "needs_manager_approval" if amount_cents > 125_000 else "auto_approve"
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation(amount_entity.entity_id or "e1", "airfare_cap_usd", amount_cents, 125_000),
        expected_final_decision=expected_decision,
        expected_missing_items=[],
        edge_case_tags=["airfare", "single_amount"],
        workflow_context=base_context("airfare", "airfare_cap_usd", amount_cents, expense_date),
    )


def build_taxi(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    vendor = rng.choice(TRANSPORT)
    expense_date = date(2026, 4, 2) + timedelta(days=sample_index % 16)
    chosen_amount = rng.choice([28.55, 54.20, 119.90])

    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" recorded a rideshare expense of ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(" on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(" with ")
    builder.entity("VENDOR", vendor, normalized_value=vendor, sensitivity_level="medium")
    builder.text(". Employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(", card ending ")
    builder.entity("CARD_LAST4", common["card_last4"], normalized_value=common["card_last4"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    amount_entity = next(entity for entity in entities if entity.label == "AMOUNT")
    amount_cents = cents_from_amount(chosen_amount)
    expected_decision = "needs_manager_approval" if amount_cents > 12_000 else "auto_approve"
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation(amount_entity.entity_id or "e1", "taxi_cap_usd", amount_cents, 12_000),
        expected_final_decision=expected_decision,
        expected_missing_items=[],
        edge_case_tags=["taxi_rideshare", "single_amount"],
        workflow_context=base_context("taxi_rideshare", "taxi_cap_usd", amount_cents, expense_date),
    )


def build_team_offsite(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    vendor = rng.choice(RESTAURANTS)
    expense_date = date(2026, 4, 5) + timedelta(days=sample_index % 10)
    meal_amount = 420.00
    tip_amount = 21.00
    tax_amount = 31.15
    total_cents = cents_from_amount(meal_amount + tip_amount + tax_amount)

    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" submitted a team offsite meal summary: meal ")
    builder.entity("AMOUNT", amount_text(meal_amount), normalized_value=amount_normalized(meal_amount))
    builder.text(", tip ")
    builder.entity("AMOUNT", amount_text(tip_amount), normalized_value=amount_normalized(tip_amount))
    builder.text(", tax ")
    builder.entity("AMOUNT", amount_text(tax_amount), normalized_value=amount_normalized(tax_amount))
    builder.text(" on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(" at vendor ")
    builder.entity("VENDOR", vendor, normalized_value=vendor, sensitivity_level="medium")
    builder.text(". Invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(", project ")
    builder.entity("PROJECT_CODE", common["project_code"], normalized_value=common["project_code"])
    builder.text(", cost center ")
    builder.entity("COST_CENTER", common["cost_center"], normalized_value=common["cost_center"])
    builder.text(", employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    first_amount = next(entity for entity in entities if entity.label == "AMOUNT")
    expected_result = "exceeds" if total_cents > 45_000 else "within_cap"
    delta_cents = abs(total_cents - 45_000)
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=[
            {"op": "sum", "left_entity_ids": ["e2", "e3", "e4"], "expected_result": str(total_cents)},
            {
                "op": "compare_policy_cap",
                "left_entity_id": first_amount.entity_id or "e2",
                "right_policy_key": "meal_cap_usd",
                "expected_result": expected_result,
                "expected_delta_usd": f"{delta_cents / 100:.2f}",
            },
        ],
        expected_final_decision="needs_manager_approval" if total_cents > 45_000 else "auto_approve",
        expected_missing_items=[],
        edge_case_tags=["multiple_amounts", "team_offsite"],
        workflow_context=base_context(
            "team_offsite",
            "meal_cap_usd",
            total_cents,
            expense_date,
            requires_sum=True,
            amount_handles_expected=3,
        ),
    )


def build_software_subscription(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    vendor = rng.choice(SOFTWARE_VENDORS)
    expense_date = date(2026, 4, 8) + timedelta(days=sample_index % 8)
    chosen_amount = rng.choice([980.00, 1_250.00, 1_520.00])

    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" requested reimbursement for a software subscription from ")
    builder.entity("VENDOR", vendor, normalized_value=vendor, sensitivity_level="medium")
    builder.text(" dated ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(". Subscription amount ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(", invoice ")
    builder.entity("INVOICE_ID", common["invoice_id"], normalized_value=common["invoice_id"])
    builder.text(", project ")
    builder.entity("PROJECT_CODE", common["project_code"], normalized_value=common["project_code"])
    builder.text(", cost center ")
    builder.entity("COST_CENTER", common["cost_center"], normalized_value=common["cost_center"])
    builder.text(", employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()

    amount_entity = next(entity for entity in entities if entity.label == "AMOUNT")
    amount_cents = cents_from_amount(chosen_amount)
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation(
            amount_entity.entity_id or "e1",
            "software_subscription_cap_usd",
            amount_cents,
            120_000,
        ),
        expected_final_decision="needs_manager_approval" if amount_cents > 120_000 else "auto_approve",
        expected_missing_items=[],
        edge_case_tags=["software_subscription", "single_amount"],
        workflow_context=base_context("software_subscription", "software_subscription_cap_usd", amount_cents, expense_date),
    )


def build_duplicate_invoice(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    base_sample = build_client_dinner(sample_index, rng, amount=362.15)
    updated_text = f"{base_sample.raw_text} Finance note: duplicate invoice suspected for the same vendor and invoice ID."
    return replace(
        base_sample,
        raw_text=updated_text,
        expected_policy_ops=[],
        expected_final_decision="needs_human_review",
        edge_case_tags=base_sample.edge_case_tags + ["duplicate_invoice"],
        workflow_context={**base_sample.workflow_context, "duplicate_invoice": True},
    )


def build_missing_receipt(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    base_sample = build_taxi(sample_index, rng)
    updated_text = f"{base_sample.raw_text} Receipt attachment missing and the note says the expense might belong to a shared ride."
    return replace(
        base_sample,
        raw_text=updated_text,
        expected_final_decision="needs_employee_followup",
        expected_missing_items=["receipt"],
        edge_case_tags=base_sample.edge_case_tags + ["missing_receipt", "ambiguous_note"],
        workflow_context={**base_sample.workflow_context, "receipt_attached": False, "note_is_ambiguous": True},
    )


def build_markdown_email(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    base_sample = build_client_dinner(sample_index, rng, amount=430.00)
    email = next(entity.text for entity in base_sample.entities if entity.label == "EMAIL")
    raw_text = f"{base_sample.raw_text}\n- reviewer contact: {email}"
    entities = list(base_sample.entities)
    entities.append(
        DetectedEntity(
            label="EMAIL",
            text=email,
            start=raw_text.index(email),
            end=raw_text.index(email) + len(email),
            entity_id=f"e{len(entities) + 1}",
            normalized_value=email,
        )
    )
    return replace(base_sample, raw_text=raw_text, entities=entities, edge_case_tags=base_sample.edge_case_tags + ["markdown_email"])


def build_json_input(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    chosen_amount = 482.15
    payload = {
        "employee": person,
        "employee_id": common["employee_id"],
        "amount": amount_text(chosen_amount),
        "invoice_id": common["invoice_id"],
        "project_code": common["project_code"],
        "email": email,
        "phone": phone,
    }
    raw_text = json.dumps(payload, sort_keys=True)
    labels = {
        "employee": "PERSON",
        "employee_id": "EMPLOYEE_ID",
        "amount": "AMOUNT",
        "invoice_id": "INVOICE_ID",
        "project_code": "PROJECT_CODE",
        "email": "EMAIL",
        "phone": "PHONE_NUMBER",
    }
    entities: list[DetectedEntity] = []
    for key, value in payload.items():
        start = raw_text.index(value)
        end = start + len(value)
        normalized_value = value
        if labels[key] == "AMOUNT":
            normalized_value = amount_normalized(chosen_amount)
        if labels[key] == "PHONE_NUMBER":
            normalized_value = "".join(filter(str.isdigit, phone))
        entities.append(
            DetectedEntity(
                entity_id=f"e{len(entities) + 1}",
                label=labels[key],
                text=value,
                start=start,
                end=end,
                normalized_value=normalized_value,
                expected_action=get_entity_policy(labels[key]).get("action", "tokenize_encrypt"),
            )
        )
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation("e3", "meal_cap_usd", cents_from_amount(chosen_amount), 45_000),
        expected_final_decision="needs_manager_approval",
        expected_missing_items=[],
        edge_case_tags=["json_input", "single_amount"],
        workflow_context=base_context("client_dinner", "meal_cap_usd", cents_from_amount(chosen_amount), date(2026, 4, 21)),
    )


def build_malformed_amount(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    malformed_amount = "$48O.15"
    expense_date = date(2026, 4, 21)
    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" submitted an expense note with malformed amount ")
    builder.text(malformed_amount)
    builder.text(" on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(". Employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=[],
        expected_final_decision="needs_human_review",
        expected_missing_items=[],
        edge_case_tags=["malformed_amount"],
        workflow_context=base_context("ambiguous_note", None, None, expense_date, malformed_amount=True),
    )


def build_missing_policy_cap(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    base_sample = build_software_subscription(sample_index, rng)
    return replace(
        base_sample,
        expected_policy_ops=[
            {
                "op": "compare_policy_cap",
                "left_entity_id": "e4",
                "right_policy_key": "unknown_policy_key",
                "expected_result": "needs_human_review",
                "expected_delta_usd": None,
            }
        ],
        expected_final_decision="needs_human_review",
        edge_case_tags=base_sample.edge_case_tags + ["missing_policy_cap"],
        workflow_context={**base_sample.workflow_context, "policy_key": "unknown_policy_key", "requires_cap_validation": True},
    )


def build_amount_date_adjacent(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    vendor = rng.choice(RESTAURANTS)
    expense_date = date(2026, 4, 21)
    chosen_amount = 450.00
    builder = TemplateBuilder()
    builder.text("Employee ")
    builder.entity("PERSON", person, normalized_value=person)
    builder.text(" logged ")
    builder.entity("AMOUNT", amount_text(chosen_amount), normalized_value=amount_normalized(chosen_amount))
    builder.text(" on ")
    builder.entity("DATE", expense_date.isoformat(), normalized_value=str(epoch_days_from_date(expense_date)))
    builder.text(" at ")
    builder.entity("VENDOR", vendor, normalized_value=vendor, sensitivity_level="medium")
    builder.text(". Employee ID ")
    builder.entity("EMPLOYEE_ID", common["employee_id"], normalized_value=common["employee_id"])
    builder.text(", card ending ")
    builder.entity("CARD_LAST4", common["card_last4"], normalized_value=common["card_last4"])
    builder.text(", email ")
    builder.entity("EMAIL", email, normalized_value=email)
    builder.text(", phone ")
    builder.entity("PHONE_NUMBER", phone, normalized_value="".join(filter(str.isdigit, phone)))
    builder.text(".")
    raw_text, entities = builder.build()
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=compare_policy_expectation("e2", "meal_cap_usd", cents_from_amount(chosen_amount), 45_000),
        expected_final_decision="auto_approve",
        expected_missing_items=[],
        edge_case_tags=["amount_date_adjacent"],
        workflow_context=base_context("client_dinner", "meal_cap_usd", cents_from_amount(chosen_amount), expense_date),
    )


def build_long_text_chunking(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    base_sample = build_hotel_booking(sample_index, rng)
    long_note = " ".join(["Additional context about the customer workshop."] * 80)
    return replace(
        base_sample,
        raw_text=f"{base_sample.raw_text} {long_note}",
        edge_case_tags=base_sample.edge_case_tags + ["long_text_chunking"],
        workflow_context={**base_sample.workflow_context, "long_text": True},
    )


def build_overlapping_entities(sample_index: int, rng: random.Random) -> ExpenseSample:
    sample_id = next_sample_id(sample_index)
    person, phone, _email = _pick_identity(rng)
    common = _pick_common_fields(rng, sample_index)
    email = contact_email(person)
    expense_date = date(2026, 4, 20)
    raw_text = (
        f"Reviewer contact is {email}. Employee {person} referenced invoice {common['invoice_id']} on "
        f"{expense_date.isoformat()}."
    )
    email_start = raw_text.index(email)
    person_start = raw_text.index(person, email_start + len(email))
    invoice_start = raw_text.index(common["invoice_id"])
    date_start = raw_text.index(expense_date.isoformat())
    entities = [
        DetectedEntity("EMAIL", email, email_start, email_start + len(email), entity_id="e1", normalized_value=email),
        DetectedEntity("PERSON", person, person_start, person_start + len(person), entity_id="e2", normalized_value=person),
        DetectedEntity(
            "INVOICE_ID",
            common["invoice_id"],
            invoice_start,
            invoice_start + len(common["invoice_id"]),
            entity_id="e3",
            normalized_value=common["invoice_id"],
        ),
        DetectedEntity(
            "DATE",
            expense_date.isoformat(),
            date_start,
            date_start + len(expense_date.isoformat()),
            entity_id="e4",
            normalized_value=str(epoch_days_from_date(expense_date)),
        ),
        DetectedEntity(
            "PHONE_NUMBER",
            phone,
            len(raw_text),
            len(raw_text),
            entity_id="e5",
            normalized_value="".join(filter(str.isdigit, phone)),
        ),
    ]
    entities = [entity for entity in entities if entity.start != entity.end]
    return ExpenseSample(
        sample_id=sample_id,
        raw_text=raw_text,
        entities=entities,
        expected_policy_ops=[],
        expected_final_decision="needs_human_review",
        expected_missing_items=[],
        edge_case_tags=["overlapping_entities"],
        workflow_context=base_context("review_contact", None, None, expense_date),
    )


EDGE_CASE_BUILDERS: dict[str, Callable[[int, random.Random], ExpenseSample]] = {
    "multiple_amounts": build_team_offsite,
    "amount_date_adjacent": build_amount_date_adjacent,
    "id_looks_like_amount": build_client_dinner,
    "card_last4_vs_employee_id": build_client_dinner,
    "vendor_contains_number": lambda index, rng: build_hotel_booking(index, rng, vendor="Motel 6 Downtown"),
    "markdown_email": build_markdown_email,
    "json_input": build_json_input,
    "malformed_amount": build_malformed_amount,
    "missing_policy_cap": build_missing_policy_cap,
    "long_text_chunking": build_long_text_chunking,
    "overlapping_entities": build_overlapping_entities,
    "minimal_context_utility_loss": build_missing_receipt,
}


DEFAULT_SCENARIO_BUILDERS: list[Callable[[int, random.Random], ExpenseSample]] = [
    build_client_dinner,
    build_hotel_booking,
    build_airfare,
    build_taxi,
    build_team_offsite,
    build_software_subscription,
    build_duplicate_invoice,
    build_missing_receipt,
]


def build_named_edge_case(case_name: str, sample_index: int = 0, seed: int = 42) -> ExpenseSample:
    rng = random.Random(seed + sample_index)
    return EDGE_CASE_BUILDERS[case_name](sample_index, rng)


def generate_samples(n: int, seed: int) -> list[ExpenseSample]:
    rng = random.Random(seed)
    samples: list[ExpenseSample] = []
    edge_builders = list(EDGE_CASE_BUILDERS.values())
    for index in range(n):
        if index < len(edge_builders):
            sample = edge_builders[index](index, rng)
        else:
            builder = DEFAULT_SCENARIO_BUILDERS[index % len(DEFAULT_SCENARIO_BUILDERS)]
            sample = builder(index, rng)
        for entity in sample.entities:
            assert sample.raw_text[entity.start:entity.end] == entity.text
        samples.append(sample)
    return samples


def build_edge_case_matrix() -> list[dict[str, str]]:
    return [
        {"edge_case": "multiple_amounts", "example": "meal + tip + tax", "expected_behavior": "Recognize multiple AMOUNT entities and validate the combined total."},
        {"edge_case": "amount_date_adjacent", "example": "$450.00 on 2026-04-21", "expected_behavior": "Keep AMOUNT and DATE boundaries separate."},
        {"edge_case": "id_looks_like_amount", "example": "INV-2026-0048", "expected_behavior": "Do not misclassify invoice IDs as AMOUNT."},
        {"edge_case": "card_last4_vs_employee_id", "example": "card ending 4812, E-4812", "expected_behavior": "Keep CARD_LAST4 and EMPLOYEE_ID labels distinct."},
        {"edge_case": "vendor_contains_number", "example": "Motel 6", "expected_behavior": "Do not classify the number in the vendor name as AMOUNT or ID."},
        {"edge_case": "markdown_email", "example": "Markdown bullet input", "expected_behavior": "Preserve correct span indexes in formatted text."},
        {"edge_case": "json_input", "example": "JSON string payload", "expected_behavior": "Protect values without corrupting the structure."},
        {"edge_case": "malformed_amount", "example": "$48O.15", "expected_behavior": "Return needs_human_review for ambiguous numeric strings."},
        {"edge_case": "missing_policy_cap", "example": "Unknown policy key", "expected_behavior": "Return needs_human_review when policy metadata is incomplete."},
        {"edge_case": "model_unavailable", "example": "GLiNER load failure", "expected_behavior": "Rule fallback remains available and the degraded state is reported."},
        {"edge_case": "long_text_chunking", "example": "Very long note body", "expected_behavior": "Preserve offsets or degrade safely."},
        {"edge_case": "overlapping_entities", "example": "john.miller@corp.example", "expected_behavior": "EMAIL wins over a nested PERSON candidate."},
        {"edge_case": "minimal_context_utility_loss", "example": "Sparse sanitized context", "expected_behavior": "Mark utility loss and route to human review when needed."},
    ]


def save_dataset(
    samples: list[ExpenseSample],
    dataset_path: str | Path,
    truth_path: str | Path,
    artifacts_dir: str | Path,
) -> None:
    dataset_records = [sample.raw_record() for sample in samples]
    truth_records = [sample.truth_record() for sample in samples]
    write_jsonl(dataset_path, dataset_records)
    write_jsonl(truth_path, truth_records)
    write_json(Path(artifacts_dir) / "ground_truth_schema.json", build_ground_truth_schema())
    preview_dataset = "\n".join(json.dumps(record, sort_keys=False) for record in dataset_records[:10])
    preview_truth = "\n".join(json.dumps(record, sort_keys=False) for record in truth_records[:10])
    write_jsonl(Path(artifacts_dir).parent / "01_data" / "synthetic_sample_10.jsonl", dataset_records[:10])
    write_jsonl(Path(artifacts_dir).parent / "01_data" / "ground_truth_sample_10.jsonl", truth_records[:10])
    write_markdown(
        Path(artifacts_dir).parent / "01_data" / "dataset_preview.md",
        "\n".join(
            [
                "# Dataset Preview",
                "",
                f"- Total samples: {len(samples)}",
                f"- Includes edge-case coverage: {', '.join(sorted({tag for sample in samples for tag in sample.edge_case_tags})[:12])}",
                "",
                "## Sample raw records",
                "",
                "```json",
                preview_dataset,
                "```",
                "",
                "## Sample ground truth records",
                "",
                "```json",
                preview_truth,
                "```",
            ]
        ),
    )
