"""Duplicate detection and broker-state reconciliation.

Two independent questions, deliberately named for what they actually check
(the previous single ``already_sent()`` conflated them):

- ``broker_has_prior_execution()`` -- does the BROKER's own record (open
  positions, today's deal history) show this symbol/magic already traded?
  This alone is not sufficient: broker history can be briefly stale or
  unavailable right after a crash, which is exactly the gap the local ledger
  closes.
- ``execution_already_committed()`` -- the real pre-send gate. True if EITHER
  the local execution ledger shows this signal_id already reached
  ``SEND_REQUESTED`` or later, OR the broker itself shows prior execution.
  Either one alone blocks a re-send.

``reconcile_position()`` implements the four-stage lifecycle a submission must
pass through before it counts as a real success:

    ORDER_SEND_REQUESTED -> ORDER_SEND_RESPONSE_RECEIVED
                          -> BROKER_STATE_QUERIED
                          -> BROKER_POSITION_CONFIRMED

A retcode that looks like success is not accepted on its own -- only
independently re-querying the broker and finding the matching deal/position
counts. If the broker accepted the order but the expected position can't be
found, that is ``BROKER_RECONCILIATION_FAILED``: a hard stop, not a warning.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ledger import ExecutionLedger

TRADE_RETCODE_DONE = 10009


def broker_has_prior_execution(gateway, symbol: str, magic: int) -> tuple[bool, str]:
    """Broker-only evidence: any open position or today's deal on this
    symbol/magic. Necessary but not sufficient on its own -- see module
    docstring."""
    positions = gateway.positions() or []
    for p in positions:
        if p.get("symbol") == symbol and int(p.get("magic", -1)) == magic:
            return True, f"open position ticket={p.get('ticket')} already exists for {symbol}"

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = gateway.deals(start_of_day, now) or []
    for d in deals:
        if d.get("symbol") == symbol and int(d.get("magic", -1)) == magic:
            return True, f"deal ticket={d.get('ticket')} already exists today for {symbol}"

    return False, ""


def execution_already_committed(ledger: ExecutionLedger, gateway, signal_id: str,
                                symbol: str, magic: int) -> tuple[bool, str]:
    """The real pre-send gate: local ledger OR broker evidence, either blocks."""
    committed, reason = ledger.is_committed(signal_id)
    if committed:
        return True, reason
    return broker_has_prior_execution(gateway, symbol, magic)


def reconcile_position(gateway, ledger: ExecutionLedger, signal_id: str,
                       send_result: dict[str, Any]) -> dict[str, Any]:
    """Independently re-query the broker after order_send and confirm the
    position it claims to have created actually exists. Returns a dict with
    ``stage`` set to the last lifecycle stage reached.

    Never trusts ``send_result["retcode"]`` alone -- a DONE-looking retcode
    with no matching position on re-query is BROKER_RECONCILIATION_FAILED,
    not a success.
    """
    retcode = send_result.get("retcode")
    order_ticket = send_result.get("order")
    deal_ticket = send_result.get("deal")

    ledger.mark_send_response(
        signal_id, retcode=retcode, comment=send_result.get("comment"),
        order_ticket=order_ticket, requested_price=send_result.get("price"),
    )

    if retcode != TRADE_RETCODE_DONE:
        return {
            "stage": "ORDER_SEND_RESPONSE_RECEIVED",
            "outcome": "SEND_REJECTED",
            "retcode": retcode,
            "comment": send_result.get("comment"),
        }

    # BROKER_STATE_QUERIED -- independently re-fetch, don't trust send_result alone.
    positions = gateway.positions() or []
    matching_position = next(
        (p for p in positions if int(p.get("ticket", -1)) == int(order_ticket or -1)
         or (deal_ticket and int(p.get("identifier", -1)) == int(deal_ticket))),
        None,
    )

    if matching_position is None:
        # Two legitimate non-position outcomes before this counts as a failure:
        # (1) a PENDING order (LIMIT/STOP) was accepted and is resting, unfilled,
        #     in the broker's own order book -- this is the NORMAL outcome for
        #     a LIMIT entry_type, which both the real strategy and this test
        #     harness use. Found live 2026-08-25: the first real order_send
        #     test was mis-reported as RECONCILIATION_FAILED because this
        #     check didn't exist yet.
        # (2) the position already closed instantly (rare, but possible for a
        #     tiny test order near a stop) -- deal history still proves it happened.
        orders = gateway.orders() or []
        matching_order = next(
            (o for o in orders if int(o.get("ticket", -1)) == int(order_ticket or -1)),
            None,
        )
        if matching_order is not None:
            ledger.mark_pending_order_confirmed(
                signal_id, order_ticket=matching_order.get("ticket"),
                requested_price=matching_order.get("price_open"),
                sl=matching_order.get("sl"), tp=matching_order.get("tp"),
            )
            return {
                "stage": "BROKER_STATE_QUERIED",
                "outcome": "PENDING_ORDER_CONFIRMED",
                "order": dict(matching_order),
            }

        now = datetime.now(timezone.utc)
        deals = gateway.deals(now.replace(hour=0, minute=0, second=0, microsecond=0), now) or []
        matching_deal = next(
            (d for d in deals if deal_ticket and int(d.get("ticket", -1)) == int(deal_ticket)),
            None,
        )
        if matching_deal is None:
            ledger.mark_reconciliation_failed(
                signal_id,
                f"order_send retcode=DONE (order={order_ticket}, deal={deal_ticket}) but no "
                f"matching open position, pending order, or today's deal found on re-query",
            )
            return {
                "stage": "BROKER_STATE_QUERIED",
                "outcome": "BROKER_RECONCILIATION_FAILED",
                "order_ticket": order_ticket,
                "deal_ticket": deal_ticket,
            }
        ledger.mark_position_confirmed(
            signal_id, deal_ticket=matching_deal.get("ticket"), position_ticket=None,
            filled_volume=matching_deal.get("volume"), fill_price=matching_deal.get("price"),
        )
        return {
            "stage": "BROKER_POSITION_CONFIRMED",
            "outcome": "CONFIRMED_VIA_DEAL_HISTORY",
            "deal": dict(matching_deal),
        }

    ledger.mark_position_confirmed(
        signal_id,
        deal_ticket=deal_ticket,
        position_ticket=matching_position.get("ticket"),
        filled_volume=matching_position.get("volume"),
        fill_price=matching_position.get("price_open"),
    )
    return {
        "stage": "BROKER_POSITION_CONFIRMED",
        "outcome": "CONFIRMED",
        "position": dict(matching_position),
    }
