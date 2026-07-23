---
name: dovui
description: "Kỹ năng đố vui/đố mẹo giúp giải trí, rèn luyện tư duy với kho câu đố đa dạng"
version: "1.0.0"
---

# Kỹ năng Đố Vui (dovui)

Kỹ năng này giúp người dùng chơi trò chơi đố vui/đố mẹo bằng tiếng Việt với kho 433 câu đố chất lượng từ AvaKids.

## Cách kích hoạt

1. **Bằng Slash Command:**
   - `/dovui` hoặc `/dovui play` - Bắt đầu trò chơi đố vui.

2. **Bằng Ngôn ngữ tự nhiên:**
   - Khi người dùng nói bất kỳ câu nào có ý định chơi đố vui, ví dụ: `"đố vui"`, `"chơi đố vui"`, `"hỏi đố vui đi"`, `"đố mẹo đi"`.

## Quy trình thực hiện của Agent

Khi được kích hoạt chơi đố vui:
1. Chạy lệnh python để lấy một câu đố ngẫu nhiên (tự động lọc các câu hỏi chưa được hỏi hoặc ít được hỏi nhất):
   ```bash
   py skills/creative/dovui/lib/dovui_tool.py random
   ```
2. Nhận kết quả JSON chứa câu hỏi (`question`) và đáp án (`answer`).
3. Đưa câu hỏi cho người dùng dưới dạng câu đố. **Không tiết lộ đáp án.**
4. Chờ người dùng phản hồi đáp án của họ.
5. Sau khi người dùng trả lời:
   - So sánh câu trả lời của người dùng với trường `answer`. Vì là câu đố mẹo/đân gian, hãy so sánh linh hoạt theo ngữ nghĩa và từ đồng nghĩa (không cần khớp chính xác 100% từng chữ).
   - Đưa ra phản hồi chúc mừng nếu đúng, hoặc giải thích đáp án đúng nếu người dùng trả lời sai/yêu cầu đầu hàng.
   - Gợi ý người dùng chơi tiếp câu tiếp theo bằng cách gõ "tiếp" hoặc `/dovui`.

## Quy tắc an toàn & Trải nghiệm
- Không bao giờ hiển thị đáp án cùng lúc với câu hỏi.
- Luôn giữ thái độ vui vẻ, dí dỏm phù hợp với trò chơi đố vui.
