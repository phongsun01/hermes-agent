

## Góp ý

### Các feature "Sẽ triển khai" — sắp xếp lại ưu tiên

**F23 (Auto-Tagging) nên lên ưu tiên cao hơn hiện tại.** Độ khó thấp, input đã sẵn có (trích yếu trong `vbden_state.json`), không cần LightRAG hay Playwright. Chỉ cần 1 LLM call khi scrape xong là có tag ngay. Kết quả này sẽ làm nền cho F24 (nhắc SLA theo loại VB) và F25 (semantic search). Nên làm F23 trước F16b.

**F24 (SLA Reminders) — cần làm rõ nguồn deadline.** F10 đã xác nhận server không lưu deadline cho VB đến (cột luôn empty). Vậy deadline lấy từ đâu? Nếu dùng AI đoán từ trích yếu ("báo cáo trước ngày 30/6") thì cần note rõ là estimated, không phải chính thức. Nếu để user tự set qua Zalo thì cần thêm command `/cc deadline <số> <ngày>`.

**F25 (Semantic Search) phụ thuộc F16b** — không thể làm trước khi LightRAG có corpus. Đây là dependency quan trọng chưa được ghi rõ trong checklist.

**F26 (Duyệt dự thảo tương tác qua Zalo)** là feature hay nhưng độ phức tạp cao hơn ghi. Zalo không có thread reply như Slack, nên "tương tác" sẽ phải dùng state machine (lưu draft đang chờ duyệt, nhận tin nhắn tiếp theo làm feedback). Cần thiết kế flow trước khi implement.

---

### Rủi ro kỹ thuật cần chú ý


**Session Playwright** — hiện tại không thấy đề cập cơ chế reuse session hay cookie persistence. Nếu mỗi lần cron chạy đều login mới thì sẽ tạo nhiều session đồng thời, có thể bị portal phát hiện và block. Nên lưu cookie jar và reuse nếu còn valid.

**`/cc end all` không có safeguard** — lệnh này kết thúc toàn bộ VB `new` một lúc, mỗi VB ~15s, nếu có 20 VB thì mất 5 phút và không thể undo. Nên thêm bước confirm: bot hỏi lại "Có X văn bản chưa xử lý, xác nhận kết thúc tất cả?" trước khi chạy.

---

### Một feature chưa có trong list, đáng cân nhắc

**F27 — Phát hiện VB cần trả lời vs VB chỉ để biết tự động.** Hiện tại F20 đã auto-finish VB "Thông báo/Để biết", nhưng logic đang dựa trên keyword cứng. Nếu kết hợp với F23 (AI tagging), có thể train prompt để phân loại chính xác hơn: VB nào cần soạn trả lời (→ trigger F9), VB nào chỉ cần đọc (→ auto-finish). Đây sẽ là bước đóng vòng lặp tự động hoàn toàn.