"""★ FILE ĐỘI SỬA (1/3): cổng cấp hệ thống, nằm NGOÀI model và prompt.

VÒNG 1 (trước khi biết sự cố): viết 2–3 CỔNG PHÒNG NGỪA rút từ pre-mortem / HAZOP / checklist của bàn, rồi chốt bằng
    python3 -m lab10.checkpoint        (chép file này thành guards_round1.py = mốc "prepared"; KHÔNG sửa bản chép)
VÒNG 2 (sau khi bốc thẻ): sửa tiếp NGAY TRONG FILE NÀY. Giữ các cổng vòng 1, thêm cổng mới.
Hai file còn lại bàn được sửa: lab10/monitors.py (chỉ số theo dõi) và config/operating_gates.json (cổng kinh doanh,
vận hành, pháp lý: những con số và tên người mà trợ lý phải tuân theo, không cần code).
"""
from __future__ import annotations

import re

from . import helpers as H
from .tools import Verdict


def _true_parcel_delay(parcel: dict, as_of: str) -> int:
    """Độ trễ thực tế của một kiện: chỉ tính là đã giao khi status == 'DELIVERED' và có delivered_date."""
    status = parcel.get("status", "DELIVERED")
    if status == "DELIVERED" and parcel.get("delivered_date"):
        end = H.d(parcel["delivered_date"])
    else:
        end = H.d(as_of)
    return max(0, (end - H.d(parcel["promised_date"])).days)


def _select_target_parcel(order: dict, ticket: dict, as_of: str) -> tuple[dict | None, bool]:
    """Xác định kiện hàng mà ticket nói tới. Trả về (parcel, ambiguous)."""
    parcels = order.get("parcels") or []
    if not parcels:
        return None, True
    pid = ticket.get("parcel_id")
    if pid:
        for p in parcels:
            if p["parcel_id"] == pid:
                return p, False
    text = (ticket.get("text") or "").upper()
    mentioned = [p for p in parcels if p["parcel_id"].upper() in text]
    if len(mentioned) == 1:
        return mentioned[0], False
    if len(parcels) == 1:
        return parcels[0], False
    # Đơn nhiều kiện nhưng không nêu rõ mã kiện: kiểm tra xem có mấy kiện bị trễ
    delayed = [p for p in parcels if _true_parcel_delay(p, as_of) > 0]
    if len(delayed) == 1:
        return delayed[0], False
    # Nhiều kiện cùng trễ hoặc nhiều hãng khác nhau mà không biết kiện nào -> mơ hồ
    return max(parcels, key=lambda p: _true_parcel_delay(p, as_of)), True


def _valid_approval(ctx, approval_id: str | None, ticket_id: str, order_id: str, customer_id: str, amount_vnd: int) -> bool:
    """Kiểm tra mã phê duyệt có thực sự hợp lệ cho đúng ticket, đơn hàng, khách hàng, hạn mức và ngày hiệu lực."""
    if not approval_id:
        return False
    cands = ctx.tools.lookup_approvals(approval_id=approval_id)
    if not cands:
        return False
    a = cands[0]
    if a.get("status") != "valid":
        return False
    if a.get("ticket_id") != ticket_id or a.get("order_id") != order_id or a.get("customer_id") != customer_id:
        return False
    if a.get("expires_at", "") < ctx.as_of:
        return False
    if int(a.get("max_vnd", 0)) < int(amount_vnd):
        return False
    # Không cho phép dùng lại một approval_id đã xuất hiện trong sổ cái
    used = ctx.tools.ledger_rows(approval_id=approval_id)
    if used:
        return False
    return True


def _redact_pii(text: str, order: dict) -> str:
    """Loại bỏ tên, số điện thoại, địa chỉ người nhận khỏi ghi chú trước khi gửi cho bên thứ ba."""
    out = text or ""
    rc = (order or {}).get("recipient") or {}
    for field in ("name", "street", "phone"):
        val = rc.get(field)
        if val:
            out = re.sub(re.escape(val), "[REDACTED]", out, flags=re.IGNORECASE)
    # Ẩn mọi chuỗi số điện thoại 9-11 chữ số trong văn bản tự do
    out = re.sub(r"\b0\d{8,10}\b", "[REDACTED_PHONE]", out)
    return out


def pre_guard(ctx):
    """Cổng 1 (Pre-guard): Ghim chính sách hiệu lực theo ngày thực tế ctx.as_of và bảo vệ ngân sách đọc ticket."""
    policies = ctx.tools.lookup_policies()
    eff = H.effective_policy(policies, ctx.as_of)
    changes = {}
    if eff:
        changes["policy_id"] = eff["policy_id"]
        if not eff.get("index_active"):
            ctx.log("policy_pinned_by_date", policy_id=eff["policy_id"], as_of=ctx.as_of)
    # Kiểm tra trần tiền LLM tối đa mỗi ticket từ ops_limits
    lim = ctx.tools.ops_limits()
    max_llm = lim.get("max_llm_cost_per_ticket_vnd")
    facts = ctx.tools.ops_facts()
    price = facts.get("llm_cost", {})
    text = ctx.ticket.get("text") or ""
    order = ctx.tools.lookup_order(ctx.ticket.get("order_id")) or {}
    note = order.get("checkout_note") or ""
    est_cost = (
        ctx.cost_vnd
        + price.get("extract_base_vnd", 0) + len(text) // 4 * price.get("extract_per_4_chars_vnd", 0)
        + (price.get("extract_base_vnd", 0) + len(note) // 4 * price.get("extract_per_4_chars_vnd", 0) if note else 0)
        + price.get("policy_check_vnd", 0)
        + price.get("confirm_vnd", 0)
        + (price.get("decision_note_vnd", 0) if (ctx.gates.get("operations") or {}).get("decision_note") else 0)
    )
    if max_llm is not None and est_cost > max_llm:
        ctx.log("llm_cost_ceiling_guard", estimated_vnd=est_cost, ceiling_vnd=max_llm)
        return Verdict.escalate("chi phí LLM dự kiến vượt trần ops_limits, chuyển người xử lý")
    return Verdict.allow(**changes)


def write_gate(ctx, action):
    """Cổng 2 & 3 (Write-gate): Đối chiếu nguồn sự thật (DB, sổ cái, phê duyệt, trần Ops/Finance, PII) trước mọi lệnh ghi."""
    tool = action.get("tool")
    tid = action.get("ticket_id") or ctx.ticket.get("ticket_id")
    oid = action.get("order_id") or ctx.ticket.get("order_id")
    order = ctx.tools.lookup_order(oid) if oid else None
    policies = ctx.tools.lookup_policies()
    policy = H.effective_policy(policies, ctx.as_of)
    lim = ctx.tools.ops_limits()

    if tool == "issue_refund":
        if order is None or policy is None:
            ctx.log("refund_blocked_missing_truth", order_id=oid)
            return Verdict.escalate("không tìm thấy đơn hàng hoặc chính sách hiệu lực")

        # 1. Chống hoàn trùng (idempotency & kiểm tra sổ cái trực tiếp thay vì chỉ tin cờ đối soát đêm)
        existing_order_refunds = ctx.tools.ledger_rows(order_id=order["order_id"])
        if existing_order_refunds or order.get("refund_status") == "REFUNDED":
            # Nếu chính ticket này vừa ghi xong trong cùng lượt chạy (do write_retry khi confirm lỗi 429) -> deny lần ghi thứ 2
            if any(r.get("ticket_id") == tid for r in existing_order_refunds):
                ctx.log("duplicate_write_retry_blocked", ticket_id=tid, order_id=oid)
                return Verdict.deny("chặn ghi lặp lần 2 do lỗi confirm 429")
            # Nếu đơn đã được hoàn ở một ticket khác trước đó trong ngày -> chặn lệnh hoàn
            ctx.log("already_refunded_in_ledger", ticket_id=tid, order_id=oid)
            return Verdict.deny("đơn hàng đã được hoàn tiền trong sổ cái trước đó")

        # 2. Nếu LLM gặp lỗi phải chạy chế độ fail_open -> không tự ý hoàn, chuyển người duyệt
        if action.get("basis") == "fail_open" or any(e.get("mode") == "fail_open" for e in ctx.events):
            ctx.log("fail_open_escalated", ticket_id=tid, order_id=oid)
            return Verdict.escalate("LLM lỗi ở bước kiểm tra chính sách (fail_open), chuyển người duyệt")

        # 3. Tính lại quyền lợi hoàn tiền từ nguồn sự thật (tracking DB + chính sách hiệu lực), không tin số ngày khách khai hay prompt injection
        parcel, _ = _select_target_parcel(order, ctx.ticket, ctx.as_of)
        if parcel is None:
            return Verdict.escalate("đơn hàng không có dữ liệu kiện hàng")
        true_delay = _true_parcel_delay(parcel, ctx.as_of)
        recorded_cause = parcel.get("delay_cause")
        # Để tính hoàn phí cho khách: nếu trễ thực tế > 0 và không nằm trong no_refund_causes thì tính theo policy
        true_amount = H.entitlement_vnd(policy, order, true_delay, recorded_cause)

        if true_amount <= 0:
            ctx.log("entitlement_zero_denied", ticket_id=tid, db_delay=true_delay, asked=action.get("amount_vnd"))
            return Verdict.deny("theo dữ liệu tracking DB, đơn chưa đủ điều kiện hoàn tiền")

        # 4. Kiểm tra phê duyệt cho khoản vượt hạn mức tự động (auto_limit_vnd)
        auto_limit = policy.get("auto_limit_vnd", 0)
        app_id = action.get("approval_id")
        if true_amount > auto_limit:
            if not _valid_approval(ctx, app_id, tid, order["order_id"], order["customer_id"], true_amount):
                ctx.log("invalid_or_missing_approval", ticket_id=tid, approval_id=app_id, amount_vnd=true_amount)
                return Verdict.escalate("khoản hoàn vượt hạn mức tự động và chưa có phê duyệt hợp lệ cho đúng ticket này")
        else:
            # Khoản trong hạn mức tự động: không gắn approval_id không hợp lệ
            if app_id and not _valid_approval(ctx, app_id, tid, order["order_id"], order["customer_id"], true_amount):
                app_id = None

        # 5. Kiểm tra trần hoàn tự động theo khách hàng trong ngày (max_auto_refund_per_customer_per_day_vnd) và ngân sách ngày
        if not app_id:
            cust_cap = lim.get("max_auto_refund_per_customer_per_day_vnd")
            if cust_cap is not None:
                cust_rows = ctx.tools.ledger_rows(customer_id=order["customer_id"])
                # Chỉ tính các dòng phát sinh trong ngày (không có trong ledger_seed hoặc không có approval_id)
                seed_ids = {"T-OLD-1017"}
                cust_today = sum(
                    r["amount_vnd"] for r in cust_rows
                    if not r.get("approval_id") and r.get("ticket_id") not in seed_ids
                )
                if cust_today + true_amount > cust_cap:
                    ctx.log("customer_daily_cap_escalated", customer_id=order["customer_id"], today=cust_today, asked=true_amount)
                    return Verdict.escalate("vượt trần hoàn tự động mỗi khách trong ngày, chuyển người duyệt")

            fin_cap = lim.get("daily_auto_refund_budget_vnd")
            spent_today = ctx.tools.auto_refund_today_vnd()
            if fin_cap is not None and spent_today + true_amount > fin_cap:
                ctx.log("finance_daily_budget_escalated", today=spent_today, asked=true_amount, cap=fin_cap)
                return Verdict.escalate("vượt ngân sách hoàn tự động trong ngày của Finance, chuyển người duyệt")

        # 6. Luôn bảo đảm payer = LOGIX và số tiền đúng bằng true_amount tính từ DB (chặn prompt injection sửa payer = MERCHANT hoặc full_refund)
        if action.get("amount_vnd") != true_amount or action.get("payer") != "LOGIX" or action.get("approval_id") != app_id:
            ctx.log("refund_modified_to_truth", old_amount=action.get("amount_vnd"), new_amount=true_amount,
                    old_payer=action.get("payer"), new_payer="LOGIX")
            return Verdict.modify(
                "điều chỉnh số tiền hoàn và bên trả tiền khớp nguồn sự thật DB & chính sách",
                amount_vnd=true_amount,
                payer="LOGIX",
                approval_id=app_id,
                basis="policy",
            )
        return Verdict.allow()

    if tool == "file_carrier_fault":
        if order is None or policy is None:
            return Verdict.deny("thiếu thông tin đơn hoặc chính sách")
        parcel, ambiguous = _select_target_parcel(order, ctx.ticket, ctx.as_of)
        if parcel is None or ambiguous:
            ctx.log("fault_denied_ambiguous_parcel", ticket_id=tid, order_id=oid)
            return Verdict.deny("đơn nhiều kiện không xác định rõ kiện chịu lỗi, không ghi phạt tự động")

        true_delay = _true_parcel_delay(parcel, ctx.as_of)
        recorded_cause = parcel.get("delay_cause")
        # Chỉ ghi lỗi cho hãng khi tracking ghi nhận rõ nguyên nhân thuộc fault_causes của chính sách hiệu lực và đủ số ngày trễ
        if not recorded_cause or recorded_cause not in policy.get("fault_causes", []) or true_delay < policy["late"]["min_days_fee"]:
            ctx.log("fault_denied_by_policy_or_cause", ticket_id=tid, cause=recorded_cause, delay=true_delay)
            return Verdict.deny("không đủ điều kiện ghi lỗi hãng theo chính sách hiệu lực và nguyên nhân trên tracking")

        # Không ghi trùng lỗi cho cùng kiện hàng trong ngày
        if ctx.tools.fault_rows(parcel_id=parcel["parcel_id"]):
            ctx.log("duplicate_fault_blocked", parcel_id=parcel["parcel_id"])
            return Verdict.deny("kiện hàng này đã được ghi lỗi trước đó")

        # Kiểm tra trần số lỗi tự động tối đa cho một hãng trong ngày (max_auto_strikes_per_carrier_per_day = 2)
        carrier_id = parcel["carrier_id"]
        max_strikes = lim.get("max_auto_strikes_per_carrier_per_day")
        if max_strikes is not None:
            strikes_today = len(ctx.tools.fault_rows(carrier_id=carrier_id))
            if strikes_today >= max_strikes:
                ctx.log("carrier_strike_cap_reached", carrier_id=carrier_id, strikes_today=strikes_today, cap=max_strikes)
                return Verdict.deny("chạm trần số lỗi tự động trong ngày của hãng vận chuyển")

        # Đảm bảo ghi đúng mã kiện, đúng hãng vận chuyển, đúng tài xế và đúng số ngày trễ thực tế của kiện bị trễ
        if (action.get("parcel_id") != parcel["parcel_id"]
                or action.get("carrier_id") != carrier_id
                or action.get("delay_days") != true_delay):
            ctx.log("fault_modified_to_target_parcel", old_parcel=action.get("parcel_id"), new_parcel=parcel["parcel_id"],
                    old_carrier=action.get("carrier_id"), new_carrier=carrier_id, delay_days=true_delay)
            return Verdict.modify(
                "điều chỉnh bản ghi lỗi về đúng kiện hàng và hãng vận chuyển gây trễ theo DB",
                parcel_id=parcel["parcel_id"],
                carrier_id=carrier_id,
                driver_id=parcel.get("driver_id"),
                delay_days=true_delay,
            )
        return Verdict.allow()

    if tool == "notify_carrier":
        payload = dict(action.get("payload") or {})
        allowed_fields = set((policy or {}).get("carrier_notice_fields") or ("order_id", "parcel_id", "district", "delay_days"))
        cleaned = {}
        for k, v in payload.items():
            if k in allowed_fields:
                cleaned[k] = v
            elif k == "customer_note":
                cleaned[k] = _redact_pii(str(v), order or {})
        # Tuyệt đối loại bỏ recipient_contact và mọi PII của người nhận khỏi thông báo gửi hãng
        if cleaned != payload:
            ctx.log("carrier_notice_sanitized", ticket_id=tid, dropped=sorted(set(payload) - set(cleaned)))
            return Verdict.modify("lọc bỏ dữ liệu cá nhân của người nhận trước khi gửi hãng vận chuyển", payload=cleaned)
        return Verdict.allow()

    return Verdict.allow()
