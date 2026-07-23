---
name: law-bidding-wiki-v2
description: Query luật đấu thầu từ law-wiki-bidding-v2. Trả lời câu hỏi dựa trên wiki đã xây dựng.
---

# Law Wiki Bidding — Hermes Skill

Query knowledge base về luật đấu thầu Việt Nam từ wiki đã xây dựng tại `d:\Antigravity\law-wiki-bidding-v2`.

## Cách dùng

```
/law-bidding-wiki-v2 "câu hỏi về luật đấu thầu"
```

Hoặc chat tự nhiên:
```
"Hỏi law-wiki: thủ tục đấu thầu rút gọn là gì?"
"Tra law-wiki: điều kiện áp dụng chỉ định thầu"
```

## Quy trình

1. Đọc `d:\Antigravity\law-wiki-bidding-v2\wiki\INDEX.md` → tìm trang liên quan
2. Đọc các trang wiki liên quan (articles, chapters, concepts)
3. Tổng hợp câu trả lời với citations `[[trang-wiki]]`
4. Trả lời bằng tiếng Việt, trích dẫn điều luật theo format: **điểm → khoản → Điều**

## Citation Format (BẮT BUỘC)

**Thứ tự trích dẫn:** điểm → khoản → Điều

| Cấp độ | Format | Ví dụ |
|--------|--------|-------|
| Chỉ Điều | `Điều [số]` | `Điều 23` |
| Điều + khoản | `khoản [số] Điều [số]` | `khoản 2 Điều 23` |
| Điều + khoản + điểm | `điểm [chữ] khoản [số] Điều [số]` | `điểm b khoản 2 Điều 23` |

**SAI (không dùng):**
- ❌ "Điều 23 khoản 2 điểm b" (thứ tự ngược)
- ❌ "Điều 23.2.b" (dấu chấm)
- ❌ "Điều 23, khoản 2, điểm b" (dấu phẩy thừa)

**ĐÚNG:**
- ✅ "điểm b khoản 2 Điều 23 Luật Đấu thầu 2023"
- ✅ "khoản 1 Điều 15"
- ✅ "Điều 10"

## Quy tắc

- **WIKI_ROOT = `d:\Antigravity\law-wiki-bidding-v2`**
- Trả lời DỰA TRÊN WIKI, không dùng kiến thức bên ngoài
- **CITATION FORMAT (BẮT BUỘC):**
  - Luôn trích dẫn theo thứ tự: **điểm → khoản → Điều**
  - Format: `điểm [chữ cái] khoản [số] Điều [số]`
  - Ví dụ: `điểm b khoản 5 Điều 10`, `khoản 2 Điều 23`, `Điều 15`
  - Không viết: "Điều 10 khoản 5 điểm b" (SAI)
  - Không viết: "Điều 10.5.b" (SAI)
  - Luôn ghi rõ "Luật Đấu thầu 2023" sau lần trích dẫn đầu tiên
- Nếu wiki thiếu thông tin → nói rõ
- Format: markdown, bảng so sánh, bullet points

## Cấu trúc wiki

```
d:\Antigravity\law-wiki-bidding-v2\wiki\
├── INDEX.md              ← Mục lục chính
├── LOG.md                ← Lịch sử thay đổi
├── articles/             ← Bài viết phân tích
├── chapters/             ← Các chương luật
├── concepts/             ← Khái niệm pháp lý
├── laws/                 ← Văn bản luật
├── procedures/           ← Quy trình thủ tục
└── syntheses/            ← Tổng hợp so sánh

```

## Ví dụ

**Input:**
```
/law-bidding-wiki-v2 "Điều kiện áp dụng hình thức chỉ định thầu?"
```

**Output:**
```markdown
# Điều kiện áp dụng chỉ định thầu

Theo [[chapters/chuong-2-hinh-thuc-phuong-thuc]], chỉ định thầu áp dụng khi:

1. **Trường hợp khẩn cấp** (khoản 1 Điều 23 Luật Đấu thầu 2023)
   - Thiên tai, dịch bệnh, sự cố (điểm a khoản 1 Điều 23)
   - Không đủ thời gian tổ chức đấu thầu (điểm b khoản 1 Điều 23)

2. **Gói thầu đặc thù** (khoản 2 Điều 23)
   - Chỉ có 1 nhà thầu đủ năng lực (điểm a khoản 2 Điều 23)
   - Bảo mật quốc gia (điểm c khoản 2 Điều 23)

3. **Giá trị nhỏ** (khoản 3 Điều 23)
   - Dưới ngưỡng quy định tại điểm a khoản 3 Điều 23

**Nguồn:** [[laws/luat-dau-thau-2023]], [[concepts/chi-dinh-thau]]
```

## Xử lý lỗi

- Nếu INDEX.md không tồn tại → báo "Wiki chưa được xây dựng"
- Nếu không tìm thấy thông tin → "Wiki chưa có nội dung về [topic]"
- Nếu câu hỏi không rõ → hỏi lại user
