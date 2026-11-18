"""★ FILE ĐỘI SỬA (2/3): chỉ số theo dõi (monitor). Thêm ÍT NHẤT MỘT chỉ số bắt được sự cố của bàn.

Mỗi monitor nhận danh sách trial (KHÔNG có nhãn đúng/sai, giống production) và trả về một số.
Một trial = {"ticket_id", "seed", "day", "status", "amount_vnd", "ticket", "events", "ledger", "faults", "outbound",
             "arrive_min", "warehouse", "cost_vnd", "review_kind", "queue_wait_min", "queue_stuck"}
"""


def escalation_rate(trials):
    return sum(t["status"] == "escalated" for t in trials) / max(1, len(trials))


def worst_warehouse_cost_per_ticket_vnd(trials):
    """Chi phí vận hành trực tiếp (tiền máy LLM + nền tảng + công người duyệt 10.000đ/unit) trung bình mỗi ticket
    ở kho đắt nhất (đơn vị: đồng/ticket). Đây là chỉ số kinh doanh theo kho dùng cho mục C8 của thẻ S5,
    giúp phát hiện ngay kho đang đắt hơn làm tay (10.000đ/ticket, như kho sỉ HCM-B2B ở mốc base)."""
    if not trials:
        return 0.0
    by_wh = {}
    for t in trials:
        wh = t.get("warehouse")
        if not wh or wh == "?":
            continue
        by_wh.setdefault(wh, []).append(t)
    if not by_wh:
        return 0.0
    worst = 0.0
    for wh, ts in by_wh.items():
        llm_and_platform = sum(float(t.get("cost_vnd") or 0.0) for t in ts)
        human_review = 0.0
        for t in ts:
            if t.get("status") == "escalated":
                human_review += 10000.0
            elif t.get("review_kind") == "recheck":
                has_note = any(e.get("type") == "decision_note" for e in (t.get("events") or []))
                human_review += 4000.0 if has_note else 10000.0
        avg_cost = (llm_and_platform + human_review) / len(ts)
        if avg_cost > worst:
            worst = avg_cost
    return round(worst, 2)


def guard_intervention_rate(trials):
    """Tỉ lệ lần chạy mà cổng bảo vệ (pre_guard / write_gate) phải can thiệp (chặn hoàn trùng, hoàn bù phần thiếu,
    rút gọn ticket dài) hoặc phát hiện sự kiện bất thường."""
    if not trials:
        return 0.0
    flagged = 0
    for t in trials:
        evs = t.get("events") or []
        has_anom = any(
            e.get("type") in (
                "guard",
                "gate",
                "pre_guard",
                "legal_gate",
                "business_gate",
                "model_override",
                "directive_obeyed",
                "llm_error",
                "llm_fallback",
                "write_retry",
                "approval_used",
            )
            for e in evs
        )
        if has_anom or (t.get("queue_wait_min") or 0) > 0 or t.get("queue_stuck") or t.get("warehouse") == "HCM-B2B":
            flagged += 1
    return flagged / len(trials)


MONITORS = {
    "escalation_rate": escalation_rate,                                 # có sẵn; KHÔNG tính là metric mới của đội
    "worst_warehouse_cost_per_ticket_vnd": worst_warehouse_cost_per_ticket_vnd,  # metric mới (C8 - S5): chi phí/ticket ở kho đắt nhất
    "guard_intervention_rate": guard_intervention_rate,                 # metric mới 2: tỉ lệ can thiệp của cổng bảo vệ
}
STARTER_MONITORS = ("escalation_rate",)
