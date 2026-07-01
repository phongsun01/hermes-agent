---
name: xs
description: "Xem và thống kê kết quả xổ số miền Bắc (XSMB) hàng ngày và phân tích lô tô lịch sử"
---

# Hướng dẫn Kỹ năng Xổ số Miền Bắc (XSMB)

Kỹ năng này giúp người dùng xem kết quả xổ số miền Bắc và thực hiện thống kê tần suất lô tô hoặc soi cầu bằng mô phỏng Pascal & Monte Carlo dựa trên dữ liệu lịch sử trong database SQLite.

## Các lệnh hỗ trợ ban đầu:
1. `/xs homnay` hoặc `/xs`: Xem kết quả xổ số miền Bắc mới nhất (ngày hôm nay).
2. `/xs <date>`: Xem kết quả xổ số miền Bắc của ngày cụ thể.
3. `/xs lo <số ngày>`: Thống kê tần suất xuất hiện lô tô đơn giản dựa theo lịch sử `N` ngày trước đó (ví dụ: `/xs lo 30`).
4. `/xs soilo <số ngày>`: Soi cầu kết hợp thuật toán Pascal & mô phỏng Monte Carlo dựa theo lịch sử `N` ngày (mặc định là 30 ngày nếu để trống).

---

## Hướng dẫn xử lý cho Agent (LLM):

### 1. Phân tích tham số ngày (<date>)
Khi người dùng nhập ngày, hãy tự động nhận diện và chuẩn hóa ngày đó về định dạng `dd-mm-yyyy` trước khi truyền vào tool `get_xsmb`:
*   *Hôm nay/homnay* -> Không truyền tham số `date` (hoặc truyền ngày hôm nay dạng `dd-mm-yyyy`).
*   *Hôm qua/homqua* -> Ngày hôm qua dạng `dd-mm-yyyy`.
*   *15-06-2026*, *15/06/2026*, *15062026* -> `15-06-2026`.
*   *15/6/2026*, *15/6* (nếu khuyết năm, hãy tự điền năm hiện tại 2026) -> `15-06-2026`.

**Hành động:** Gọi công cụ `get_xsmb(date="ngày_đã_chuẩn_hóa")`.

---

### 2. Xử lý lệnh thống kê lô tô thường (`/xs lo <số ngày>`)
Khi nhận lệnh `/xs lo <số ngày>` (ví dụ: `/xs lo 30`):
1. **Lấy dữ liệu:** Gọi công cụ `get_xsmb(limit_days=số_ngày)`.
2. **Tính toán tần suất:** Trích xuất 2 số cuối (lô) của tất cả các giải từ GDB đến G7 trong danh sách kết quả trả về. Đếm số lần xuất hiện của mỗi cặp số từ `00` đến `99`.
3. **Tổng hợp kết quả:**
   * Tìm top 5 cặp số xuất hiện **nhiều nhất** (kèm số lần xuất hiện).
   * Tìm top 5 cặp số xuất hiện **ít nhất** hoặc chưa từng xuất hiện trong khoảng thời gian đó.
   * Thống kê xem đầu số nào (0 đến 9) xuất hiện nhiều nhất/ít nhất.
4. **Trình bày:** Hiển thị kết quả dưới dạng một báo cáo phân tích ngắn gọn, trực quan, dễ hiểu gửi lại cho người dùng trên Zalo.

---

### 3. Xử lý lệnh soi cầu Pascal & Monte Carlo (`/xs soilo <số ngày>`)
Khi nhận lệnh `/xs soilo <số ngày>`:
1. **Phân tích tham số:** 
   * Nếu người dùng truyền số ngày (ví dụ: `/xs soilo 50`), sử dụng tham số `last_days=50`.
   * Nếu người dùng để trống số ngày hoặc ghi chung chung (ví dụ: `/xs soilo`), sử dụng giá trị mặc định `last_days=30`.
2. **Kích hoạt công cụ:** Gọi công cụ `predict_xsmb(last_days=số_ngày)`.
3. **Xử lý phản hồi:** Nhận kết quả từ công cụ và hiển thị cho người dùng kết quả của thuật toán Pascal từ kỳ quay gần nhất cùng danh sách Top 10 con số tiềm năng được mô phỏng bởi thuật toán Monte Carlo kèm theo tỷ lệ phần trăm cụ thể.
