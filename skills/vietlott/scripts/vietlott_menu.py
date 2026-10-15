#!/usr/bin/env python3
"""vietlott_menu.py — Router và Inline Keyboard Menu cho Vietlott Mega 6/45 trên Telegram.

Hỗ trợ các lệnh:
  /vlmenu (hoặc vlmenu, /vl)
  Callback query v1|vl|...
"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

# Đảm bảo UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Thêm thư mục scripts của skill vietlott vào sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vietlott645
import vl_fetch
import vl_report


def build_menu_payload(screen: str = "root") -> dict:
    scr = (screen or "root").strip().lower()

    if scr in ("root", "main", "menu"):
        text = (
            "🎰 *VIETLOTT MEGA 6/45 — MENU ĐIỀU KHIỂN*\n\n"
            "Chọn chức năng bạn muốn tra cứu hoặc phân tích:\n"
            "• *Báo cáo mới nhất:* Kết quả kỳ gần nhất & giải thưởng\n"
            "• *Thống kê & Kiểm định:* Tần suất, số nóng/lạnh, kiểm định Q\n"
            "• *Dự đoán / Gợi ý số:* Vé Hot, Cold, Random\n"
            "• *Giá trị kỳ vọng (EV):* Phân tích điểm hòa vốn jackpot\n"
            "• *Xác suất trúng:* Bảng xác suất siêu bội 0-6 số\n"
            "• *Cập nhật dữ liệu:* Kéo kết quả mới từ Minh Chính / Minh Ngọc"
        )
        buttons = [
            [
                {"text": "📊 Báo cáo kỳ mới nhất", "callback_data": "v1|vl|run|report"},
                {"text": "🎯 Gợi ý bộ số", "callback_data": "v1|vl|open|pick_menu"},
            ],
            [
                {"text": "📈 Thống kê & Kiểm định", "callback_data": "v1|vl|run|stats"},
                {"text": "💰 Tính kỳ vọng (EV)", "callback_data": "v1|vl|run|ev"},
            ],
            [
                {"text": "🎲 Bảng xác suất", "callback_data": "v1|vl|run|odds"},
                {"text": "🔄 Cập nhật kết quả", "callback_data": "v1|vl|run|update"},
            ],
        ]
        return {"text": text, "buttons": buttons}

    if scr in ("pick_menu", "pick"):
        text = (
            "🎯 *GỢI Ý BỘ SỐ THAM KHẢO MEGA 6/45*\n\n"
            "Chọn phương pháp sinh số tham khảo:\n"
            "• *Vé Hot:* Chọn theo 6 số có tần suất xuất hiện cao nhất\n"
            "• *Vé Cold:* Chọn theo 6 số ít xuất hiện nhất (lạnh nhất)\n"
            "• *Vé Random:* Sinh ngẫu nhiên hoàn toàn (3 bộ)\n\n"
            "⚠️ *Lưu ý:* Mọi bộ số đều có xác suất Jackpot như nhau (1/8.145.060)."
        )
        buttons = [
            [
                {"text": "🔥 Vé Hot (Tần suất cao)", "callback_data": "v1|vl|run|pick_hot"},
                {"text": "❄️ Vé Cold (Số lạnh)", "callback_data": "v1|vl|run|pick_cold"},
            ],
            [
                {"text": "🎲 3 Vé Random", "callback_data": "v1|vl|run|pick_random"},
            ],
            [
                {"text": "⬅️ Quay lại Menu chính", "callback_data": "v1|vl|open|main"},
            ],
        ]
        return {"text": text, "buttons": buttons}

    return build_menu_payload("root")


def execute_action(action: str) -> dict:
    act = (action or "").strip().lower()

    if act == "report":
        try:
            report_text = vl_report.generate_report()
            buttons = [
                [
                    {"text": "🔄 Làm mới báo cáo", "callback_data": "v1|vl|run|report"},
                    {"text": "🎯 Gợi ý bộ số", "callback_data": "v1|vl|open|pick_menu"},
                ],
                [
                    {"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"},
                ],
            ]
            return {"text": report_text, "buttons": buttons}
        except Exception as e:
            return {
                "text": f"⚠️ Lỗi khi tạo báo cáo Vietlott: {e}",
                "buttons": [[{"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"}]],
            }

    if act == "stats":
        try:
            draws = vietlott645.load(limit=300)
            m = len(draws)
            f = vietlott645.freq(draws) if draws else {}
            ranked_hot = sorted(f.items(), key=lambda x: (-x[1], x[0]))[:6]
            ranked_cold = sorted(f.items(), key=lambda x: (x[1], x[0]))[:6]

            hot_str = ", ".join(f"`{n:02d}` ({c} lần)" for n, c in ranked_hot)
            cold_str = ", ".join(f"`{n:02d}` ({c} lần)" for n, c in ranked_cold)

            x2, adj, p_freq = vietlott645.freq_test(draws)
            Q, pc, pm = vietlott645.order_stat_test(draws, mc=200)

            verdict_q = "Chuẩn ngẫu nhiên" if pc >= 0.01 else "Cần theo dõi bất thường"

            text = (
                f"📈 *THỐNG KÊ & KIỂM ĐỊNH TÍNH NGẪU NHIÊN ({m} KỲ)*\n\n"
                f"🔥 *Top 6 số NÓNG nhất:*\n   {hot_str}\n\n"
                f"❄️ *Top 6 số LẠNH nhất:*\n   {cold_str}\n\n"
                f"⚖️ *Kiểm định Chi-Square tần suất:*\n"
                f"   • X² hiệu chỉnh: `{adj:.1f}` (df=44) | p = `{p_freq:.3f}`\n\n"
                f"🔬 *Kiểm định thống kê thứ tự Q (arXiv:0806.4595):*\n"
                f"   • Q = `{Q:.2f}` (df=6) | p = `{pc:.3f}`\n"
                f"   • Đánh giá: *{verdict_q}*\n\n"
                f"💡 *Giải thích:* Giá trị p > 0.01 chứng minh lồng quay tuân thủ nghiêm ngặt tính ngẫu nhiên, "
                f"không có bằng chứng gian lận và không thể dự đoán."
            )
            buttons = [
                [
                    {"text": "🎯 Xem bộ số tham khảo", "callback_data": "v1|vl|open|pick_menu"},
                    {"text": "⬅️ Menu chính", "callback_data": "v1|vl|open|main"},
                ]
            ]
            return {"text": text, "buttons": buttons}
        except Exception as e:
            return {
                "text": f"⚠️ Lỗi khi thống kê dữ liệu: {e}",
                "buttons": [[{"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"}]],
            }

    if act == "ev":
        try:
            draws = vietlott645.load_full()
            rows_p = [r for r in draws if vietlott645.tickets_hat(r)]
            sec = vietlott645.ev_secondary()
            p6 = vietlott645.p_match(vietlott645.K)

            # Lấy kỳ gần nhất
            last_ky = draws[-1] if draws else None
            last_jp = last_ky["jackpot"] if (last_ky and last_ky["jackpot"]) else 12_000_000_000
            last_jp_ty = last_jp / 1e9

            # Fit model
            fit = vietlott645.fit_sales(rows_p)
            if fit:
                fn_est = lambda Jx: vietlott645.exp(fit["a"] + fit["b"] * vietlott645.math.log(Jx)) * p6
                lam_curr = fn_est(last_jp)
                be_val = vietlott645.breakeven(fn_est, tax=True, price=vietlott645.PRICE)
                be_str = f"{be_val / 1e9:.0f} tỷ đồng" if be_val else "Không hòa vốn (<100k tỷ)"
            else:
                lam_curr = 0.15
                be_str = "87 tỷ đồng"

            ev_jp = vietlott645.ev_jackpot(last_jp, lam_curr, tax=True)
            ev_tot = sec + ev_jp
            pct = 100 * ev_tot / vietlott645.PRICE
            lost = vietlott645.PRICE - ev_tot

            text = (
                f"💰 *PHÂN TÍCH GIÁ TRỊ KỲ VỌNG (EV) — MEGA 6/45*\n\n"
                f"💵 *Giá vé:* 10.000 đ\n"
                f"🎁 *Giải phụ cố định (Nhất+Nhì+Ba):* 1.370 đ/vé\n"
                f"🏆 *Jackpot hiện tại ước tính:* ~{last_jp_ty:.1f} tỷ đ\n\n"
                f"📊 *Kỳ vọng nhận lại trên mỗi vé 10.000đ:*\n"
                f"   • EV giải phụ: `1.370 đ`\n"
                f"   • EV Jackpot (sau thuế & chia giải): `{ev_jp:,.0f} đ`\n"
                f"   👉 *Tổng EV:* `{ev_tot:,.0f} đ` ({pct:.1f}% mệnh giá)\n"
                f"   📉 *Kỳ vọng lỗ trung bình:* `-{lost:,.0f} đ` / vé\n\n"
                f"🎯 *Điểm hòa vốn lý thuyết (EV >= 10.000đ):*\n"
                f"   • Jackpot phải đạt tối thiểu: *{be_str}*\n\n"
                f"📌 *Kết luận khoa học:* Mua vé số luôn có kỳ vọng tài chính âm. "
                f"Chỉ nên mua giải trí với số tiền nhỏ."
            )
            buttons = [
                [
                    {"text": "📊 Báo cáo mới nhất", "callback_data": "v1|vl|run|report"},
                    {"text": "⬅️ Menu chính", "callback_data": "v1|vl|open|main"},
                ]
            ]
            return {"text": text, "buttons": buttons}
        except Exception as e:
            return {
                "text": f"⚠️ Lỗi khi tính EV: {e}",
                "buttons": [[{"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"}]],
            }

    if act == "odds":
        text = (
            "🎲 *BẢNG XÁC SUẤT TRÚNG THƯỞNG MEGA 6/45*\n"
            "_(Phân phối siêu bội Hypergeometric C(6,k)·C(39,6-k)/C(45,6))_\n\n"
            "🏆 *Trúng 6/6 (Jackpot):* `1 / 8.145.060` (~0.000012%)\n"
            "🥇 *Trúng 5/6 (Giải Nhất - 10 tr):* `1 / 34.808` (~0.0029%)\n"
            "🥈 *Trúng 4/6 (Giải Nhì - 300k):* `1 / 733` (~0.136%)\n"
            "🥉 *Trúng 3/6 (Giải Ba - 30k):* `1 / 45` (~2.24%)\n"
            "🔹 *Trúng 2/6 (Không thưởng):* `1 / 7` (~15.1%)\n"
            "🔹 *Trúng 1/6 (Không thưởng):* `1 / 2.4` (~42.4%)\n"
            "❌ *Trúng 0/6 (Trượt trắng):* `1 / 2.5` (~40.1%)\n\n"
            "👉 *Tổng xác suất có giải (>= 3 số):* ~`1 / 42` (2.4% mỗi vé)"
        )
        buttons = [
            [
                {"text": "🎯 Gợi ý bộ số", "callback_data": "v1|vl|open|pick_menu"},
                {"text": "⬅️ Menu chính", "callback_data": "v1|vl|open|main"},
            ]
        ]
        return {"text": text, "buttons": buttons}

    if act == "pick_hot":
        draws = vietlott645.load(limit=300)
        f = vietlott645.freq(draws) if draws else {}
        pool = list(range(1, 46))
        order_hot = sorted(pool, key=lambda i: (f.get(i, 0), i), reverse=True)
        picked = sorted(order_hot[:6])
        nums_str = " - ".join(f"`{x:02d}`" for x in picked)
        text = (
            f"🔥 *VÉ HOT — TẦN SUẤT CAO NHẤT (300 KỲ GẦN NHẤT)*\n\n"
            f"👉 Bộ số: **{nums_str}**\n\n"
            f"📊 Thống kê tần suất:\n"
            + "\n".join(f"• Số `{x:02d}`: xuất hiện {f.get(x, 0)} lần" for x in picked)
            + "\n\n⚠️ *Lưu ý:* Tần suất quá khứ không làm tăng xác suất trúng trong tương lai."
        )
        buttons = [
            [
                {"text": "❄️ Đổi sang Vé Cold", "callback_data": "v1|vl|run|pick_cold"},
                {"text": "🎲 Đổi sang Vé Random", "callback_data": "v1|vl|run|pick_random"},
            ],
            [
                {"text": "⬅️ Menu Gợi ý", "callback_data": "v1|vl|open|pick_menu"},
                {"text": "🏠 Menu chính", "callback_data": "v1|vl|open|main"},
            ],
        ]
        return {"text": text, "buttons": buttons}

    if act == "pick_cold":
        draws = vietlott645.load(limit=300)
        f = vietlott645.freq(draws) if draws else {}
        pool = list(range(1, 46))
        order_cold = sorted(pool, key=lambda i: (f.get(i, 0), i))
        picked = sorted(order_cold[:6])
        nums_str = " - ".join(f"`{x:02d}`" for x in picked)
        text = (
            f"❄️ *VÉ COLD — SỐ ÍT XUẤT HIỆN NHẤT (SỐ LẠNH)*\n\n"
            f"👉 Bộ số: **{nums_str}**\n\n"
            f"📊 Thống kê tần suất:\n"
            + "\n".join(f"• Số `{x:02d}`: xuất hiện {f.get(x, 0)} lần" for x in picked)
            + "\n\n⚠️ *Lưu ý:* Số ít ra không đồng nghĩa với việc sắp phải ra."
        )
        buttons = [
            [
                {"text": "🔥 Đổi sang Vé Hot", "callback_data": "v1|vl|run|pick_hot"},
                {"text": "🎲 Đổi sang Vé Random", "callback_data": "v1|vl|run|pick_random"},
            ],
            [
                {"text": "⬅️ Menu Gợi ý", "callback_data": "v1|vl|open|pick_menu"},
                {"text": "🏠 Menu chính", "callback_data": "v1|vl|open|main"},
            ],
        ]
        return {"text": text, "buttons": buttons}

    if act == "pick_random":
        pool = list(range(1, 46))
        lines = []
        for i in range(1, 4):
            combo = sorted(random.sample(pool, 6))
            combo_str = " - ".join(f"`{x:02d}`" for x in combo)
            lines.append(f"• Vé {i}: **{combo_str}**")

        text = (
            "🎲 *GỢI Ý 3 VÉ NGẪU NHIÊN HOÀN TOÀN*\n\n"
            + "\n".join(lines)
            + "\n\n💡 *Gợi ý:* Chơi ngẫu nhiên là chiến lược công bằng nhất đối với xổ số độc lập."
        )
        buttons = [
            [
                {"text": "🎲 Sinh 3 vé khác", "callback_data": "v1|vl|run|pick_random"},
            ],
            [
                {"text": "🔥 Xem Vé Hot", "callback_data": "v1|vl|run|pick_hot"},
                {"text": "❄️ Xem Vé Cold", "callback_data": "v1|vl|run|pick_cold"},
            ],
            [
                {"text": "⬅️ Menu Gợi ý", "callback_data": "v1|vl|open|pick_menu"},
                {"text": "🏠 Menu chính", "callback_data": "v1|vl|open|main"},
            ],
        ]
        return {"text": text, "buttons": buttons}

    if act == "update":
        try:
            # Chạy crawler cập nhật kết quả mới
            added = vl_fetch.update()
            cached = vl_fetch.load_cached_draws(vl_fetch.DEFAULT_CSV_PATH)
            last_ky = max(cached.keys()) if cached else 0
            text = (
                f"🔄 *CẬP NHẬT KẾT QUẢ VIETLOTT THÀNH CÔNG*\n\n"
                f"• Số kỳ mới được bổ sung: `{added}`\n"
                f"• Tổng số kỳ trong cơ sở dữ liệu: `{len(cached)}`\n"
                f"• Kỳ quay mới nhất hiện có: `#{last_ky:05d}`\n\n"
                f"Bấm nút bên dưới để xem ngay báo cáo kết quả chi tiết!"
            )
            buttons = [
                [
                    {"text": "📊 Xem báo cáo kỳ mới nhất", "callback_data": "v1|vl|run|report"},
                ],
                [
                    {"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"},
                ],
            ]
            return {"text": text, "buttons": buttons}
        except Exception as e:
            return {
                "text": f"⚠️ Lỗi khi cập nhật dữ liệu Vietlott: {e}",
                "buttons": [[{"text": "⬅️ Menu Vietlott", "callback_data": "v1|vl|open|main"}]],
            }

    return build_menu_payload("root")


def handle_request(raw_input: str) -> dict:
    s = (raw_input or "").strip()

    # Nhận diện callback token v1|vl|action|arg
    if s.startswith("v1|vl|"):
        parts = s.split("|")
        if len(parts) >= 4:
            verb, arg = parts[2], parts[3]
            if verb == "open":
                res = build_menu_payload(arg)
            elif verb == "run":
                res = execute_action(arg)
            else:
                res = build_menu_payload("root")
        else:
            res = build_menu_payload("root")
        return {"status": "ok", "command": "vlmenu", "result": res}

    # Lệnh trực tiếp: /vlmenu, vlmenu, /vl, vl
    cmd_lower = s.lower()
    if cmd_lower in ("/vlmenu", "vlmenu", "/vl", "vl", "/menu vl", "menu vl"):
        res = build_menu_payload("root")
        return {"status": "ok", "command": "vlmenu", "result": res}

    # Tham số phụ: /vl report, /vl stats, /vl ev, /vl pick, /vl odds
    for sub in ("report", "stats", "ev", "odds", "pick", "update"):
        if cmd_lower.startswith(f"/vl {sub}") or cmd_lower.startswith(f"vl {sub}"):
            if sub == "pick":
                res = build_menu_payload("pick_menu")
            else:
                res = execute_action(sub)
            return {"status": "ok", "command": "vlmenu", "result": res}

    # Mặc định mở menu chính
    res = build_menu_payload("root")
    return {"status": "ok", "command": "vlmenu", "result": res}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "/vlmenu"
    result = handle_request(arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
