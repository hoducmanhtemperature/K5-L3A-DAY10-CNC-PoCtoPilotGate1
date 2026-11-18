# Team

## Thông tin nhóm

- Tên nhóm (`TenNhom`, không dấu, không khoảng trắng): `CNC`
- Lớp: `L3A`
- Repo của bàn: `K5-L3A-DAY10-CNC-PoCtoPilotGate1`
- Thẻ sự cố đã bốc (S1–S8): `S5`

## Thành viên

Họ tên đầy đủ và MSSV của **mọi** thành viên; thêm dòng nếu cần. Vai: Kỹ sư cổng · Sản phẩm và kinh doanh · Vận hành và pháp lý (README mục 3, phút 0–15).

| STT | Họ và tên | MSSV         | Vai | Trưởng nhóm |
| --: | --------- | ----         | --- | :---------: |
|   1 | Hồ Đức Mạnh | 2A202603609 | Kỹ sư cổng · Sản phẩm và kinh doanh · Vận hành và pháp lý (1 thành viên đảm nhiệm cả 3 vai) | YES |

Ghi `members` trong `submission/submission.json` theo dạng `"HoVaTen-MSSV"`, khớp bảng trên.

## Cá nhân

Mỗi thành viên tự viết một mục bên dưới (chép mẫu, đổi tiêu đề thành họ tên không dấu và MSSV, ví dụ `## NguyenVanAn-20241234`).

## HoDucManh-2A202603609

### Phần việc phụ trách

- **Vai trong bàn:** Đảm nhiệm cả 3 vai (Trưởng nhóm · Kỹ sư cổng · Sản phẩm và kinh doanh · Vận hành và pháp lý).
- **Câu trong đề & mục phiếu:**
  - **Khối 1 (Phiếu A `templates/form-a-criteria.md`, câu 1.1–1.6):** Xác định mục tiêu cấp hệ thống và mục tiêu theo góc nhìn của kế toán đối soát (`NV-OANH`) & trưởng ca CSKH (`NV-HANH`); thiết kế offline metric cho bước `file_carrier_fault` và telemetry production phát hiện xâm hại bên thứ ba; phân tích khoảng tin cậy bootstrap 95%; xây dựng và ký Bản tiêu chí chấp nhận (`config/acceptance_criteria.json`).
  - **Khối 2 (Phiếu B `templates/form-b-evaluation-gates.md`, câu 2.1–2.10, quyết định v1):** Chạy đánh giá baseline, dò trace và lập bảng soát lỗi cho `T-002@55`; lập bản đồ dữ liệu và phân tích drift sang `REFUND-v4` ngày `2026-12-01`; phân tích HAZOP vòng 1 trên `issue_refund` (kèm mở rộng ngoài kỹ thuật); điền checklist 9 nhóm việc go-live; thực hiện pre-mortem 4 lăng kính; viết cổng phòng ngừa trong `lab10/guards.py` và cấu hình `config/operating_gates.json`; viết 2 behavioral test `--adhoc`; viết Runbook phần 1–3 và kịch bản Giờ cao điểm; chốt cổng vòng 1 (`lab10.checkpoint`) và ra quyết định Gate 1 v1 (`Tiếp tục`).
  - **Khối 3 (Phiếu C `templates/form-c-incident.md`, câu 3.0–3.7, quyết định v2 trên thẻ `S5`):** Đo mốc `prepared` trên thẻ `S5` trước khi sửa; dò trace các ca hỏng (`S5-02`, `S5-20`, `S5-21`, `S5-50`, `S5-51`, `S5-70`), lập bảng soát lỗi, mở lại pre-mortem & bản đồ dữ liệu (`C1`, `C3.5`), viết HAZOP của thẻ (`C4`), đặc tả specification & giả định môi trường (`C5`), vẽ fault tree trước và sau khi sửa (`C6`, `C9`); nâng cấp `lab10/guards.py`, thu hẹp `business.pilot_scope` trong `config/operating_gates.json`, thêm chỉ số kinh doanh `worst_warehouse_cost_per_ticket_vnd` và `guard_intervention_rate` trong `lab10/monitors.py` (`C7`, `C8`); cập nhật Risk register (`C10`), checklist 9 nhóm & Runbook 4–5 (`C11`), viết quyết định Gate 1 v2 (`Thu hẹp`, `C12`) và gom bài nộp `submission/`.

### Đóng góp cụ thể

- Thiết lập và niêm phong `config/acceptance_criteria.json` cho bàn `K5-L3A-DAY10-CNC-PoCtoPilotGate1` trước lần chạy đánh giá đầu tiên (commit `b80d0fa`, hash `2b1d69bc`).
- Xây dựng hệ thống cổng phòng ngừa vòng 1 (`lab10/guards_round1.py`, hash `b9b03e30`) và nâng cấp ở vòng 2 (`lab10/guards.py`) xử lý trọn vẹn cả 3 vấn đề của CFO trong thẻ `S5`:
  1. `pre_guard`: Ghim chính sách hiệu lực theo ngày thực tế `ctx.as_of` (`H.effective_policy`), dùng `_trim_ticket_text` (`Verdict.rewrite`) cắt bỏ phần danh sách mã hàng dán kèm dài > 6.500 ký tự sau `\n---` để giữ `llm_cost_max = 765đ <= trần 1.500đ` mà vẫn giải quyết tự động được các đơn lẻ (`S5-70`, `S5-73`, `S5-76`).
  2. `write_gate("issue_refund")`: Đối chiếu trực tiếp sổ cái `world.ledger` để tính phần quyền lợi còn lại `true_amount = full_entitlement - already_paid`: chặn đứng 100% các ca hoàn trùng (`S5-02`, `S5-03`, `S5-05`, `S5-20`) và hoàn bù chính xác `12.000đ` phần còn thiếu cho đơn mới được CSKH hoàn tạm một phần (`S5-21`); kiểm tra `_valid_approval`, trần `300.000đ/khách/ngày` và ép `payer = "LOGIX"`.
  3. `write_gate("file_carrier_fault" & "notify_carrier")`: Chọn đúng kiện gây trễ `_select_target_parcel`, chỉ phạt khi có `delay_cause` hợp lệ, chặn phạt trùng `parcel_id`, giữ trần `2` lỗi tự động/hãng/ngày, và lọc bỏ mọi trường PII trước khi gửi thông báo cho hãng.
- Trong `config/operating_gates.json`: Thu hẹp `business.pilot_scope` sang `{"mode": "warehouse", "warehouses": ["HN", "HCM", "DN", "CT"], "percent": 100}` để cắt kho sỉ `HCM-B2B` (vốn luôn vượt hạn mức tự động 200.000đ làm tốn `11.326đ/ticket > 10.000đ` làm tay) về quy trình duyệt tay trực tiếp, đưa chi phí trung bình trên `S5` xuống `2.407đ/ticket`, tiết kiệm ròng `+136.673đ/ngày` và `ROI = 3.15`.
- Trong `lab10/monitors.py`: Thiết kế và cài đặt chỉ số kinh doanh `worst_warehouse_cost_per_ticket_vnd` (đo chi phí máy + công người trung bình mỗi ticket ở kho đắt nhất, sáng đèn ở `11.325,67đ` trên `S5 base` và giảm về `763,67đ` trên `S5 after`) cùng `guard_intervention_rate`.
- Ghi chú sử dụng AI (theo `RULES.md`): Sử dụng trợ lý AI để hỗ trợ tra cứu cấu trúc codebase, kiểm tra các nhánh điều kiện trong `lab10/guards.py` và rà soát định dạng bảng biểu trong các phiếu. Mọi ngưỡng tiêu chí, con số vận hành và quyết định Gate 1 đều bám sát dữ liệu `data/world.json` và `incidents/S5/`.

### Bằng chứng

- Commit ký tiêu chí: `b80d0fa` (`Sign acceptance criteria`, hash `2b1d69bcb9131673ecdd77cbb9c0aee624517794796c576675a013e9a746fc59`).
- Commit chốt cổng vòng 1 và quyết định v1: `6263ae0` (`LAB 10: chốt cổng vòng 1, quyết định v1`, hash checkpoint `b9b03e30`).
- Các mã lần chạy vòng 1 (trên bộ nền `base`):
  - Baseline (`base · base`): `R-base-before-20261118-233957-8ae809` (`pass_rate = 0.9909`, hỏng `T-002@55`).
  - Sau khi dựng cổng vòng 1 (`base · after`): `R-base-after-20261118-234048-14ec5e` (`pass_rate = 1.0`, `pass_k = 1.0`).
  - Bản chốt vòng 1 (`base · prepared`): `R-base-prepared-20261118-234138-14ec5e` (`pass_rate = 1.0`, `pass_k = 1.0`, chi phí `4.456đ/ticket`, `ROI = 1.24`).
- Các mã lần chạy vòng 2 (trên thẻ sự cố `S5`):
  - Tự kiểm tra bước 0 (trước khi sửa vòng 2): `R-S5-grade-20261119-000347-bbb482` (`base`: `R-S5-before-20261119-000348-bbb482` · `prepared`: `R-S5-prepared-20261119-000348-bbb482`).
  - Đánh giá sau khi sửa vòng 2: `R-S5-after-20261119-000653-82f33f` (`S5 · after`) và `R-base-after-20261119-000653-82f33f` (`base · after`).
  - Báo cáo tự kiểm tra cuối cùng (`PASS-VISIBLE`): `R-S5-grade-20261119-000654-82f33f` (ba mốc: `base` `R-S5-before-20261119-000654-82f33f` · `prepared` `R-S5-prepared-20261119-000654-82f33f` · `after` `R-S5-after-20261119-000654-82f33f`).
- Các mục đã điền đầy đủ: Phiếu A (`A1`–`A5`), Phiếu B (`B0`–`B8`), Phiếu C (`C0`–`C12`), `submission/submission.json`.

### Exit ticket

- **Một điều học được:** Qua sự cố `S5`, tôi học được rằng một trợ lý AI dù không còn lỗi mô hình (model trả lời đúng chính sách và chuyển người đúng quy định ở kho sỉ `HCM-B2B`) vẫn có thể làm dự án **lỗ nặng** nếu đưa nhầm phân khúc đơn hàng (như đơn B2B luôn vượt hạn mức tự động `200.000đ`) vào phạm vi tự động hoá, khiến công ty phải trả cả tiền máy LLM lẫn 100% công người duyệt (`11.326đ > 10.000đ` làm tay). Do đó, cổng phạm vi kinh doanh (`business.pilot_scope`), cổng tiền xử lý cắt gọn đầu vào (`Verdict.rewrite`) và cổng đối chiếu định lượng sổ cái (`full_entitlement - already_paid`) quan trọng không kém gì chất lượng của bản thân mô hình.
- **Một điều còn chưa chắc:** Trong vận hành thực tế tại 2 depot, khi nhân viên tổng đài CSKH đang trao đổi điện thoại và thao tác hoàn tiền một phần cho khách nhưng chưa kịp bấm lưu vào DB mà khách đã đồng thời nhắn tin lên Zalo/App cho trợ lý AI, cần thiết kế cơ chế khoá phân tán (distributed lock theo `order_id`) với thời gian giữ khoá bao lâu để vừa ngăn hoàn trùng vừa không làm nghẽn trải nghiệm của khách.
