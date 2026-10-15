"""
Scraper cho trang chinhsachonline.chinhphu.vn
Lĩnh vực: Tài chính – Ngân hàng – Công Thương (id=14)

Cách dùng:
    py scrape_qa_chinhphu.py
    py scrape_qa_chinhphu.py --pages 5      # Chỉ scrape 5 trang đầu
    py scrape_qa_chinhphu.py --from-page 3  # Bắt đầu từ trang 3
"""

import argparse
import hashlib
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

# Đảm bảo in tiếng Việt trên console Windows không bị UnicodeEncodeError và unbuffered
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
else:
    sys.stdout.reconfigure(line_buffering=True)
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
else:
    sys.stderr.reconfigure(line_buffering=True)

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://chinhsachonline.chinhphu.vn"


def get_category_url(page: int) -> str:
    """Trả về URL chính xác cho từng trang."""
    if page == 1:
        return f"{BASE_URL}/tai-chinh-ngan-hang-cong-thuong/t1/14.htm"
    return f"{BASE_URL}/tai-chinh-ngan-hang-cong-thuong/t1/14/trang-{page}.htm"

# Ghi vào cả hai thư mục: bản gốc trên D: và bản trong .hermes để Docker truy cập
OUTPUT_DIR = Path(r"D:\Antigravity\law-wiki-bidding-v2\raw\qa-chinhphu")
OUTPUT_DIR_HERMES = Path(r"C:\Users\Desktop\.hermes\law-wiki-bidding-v2\raw\qa-chinhphu")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

DELAY = 1.5  # giây delay giữa các request

# Bộ từ khóa lọc chuyên đề Đấu thầu & Mua sắm công
KEYWORDS_BIDDING = [
    "đấu thầu",
    "đấu giá",
    "chỉ định thầu",
    "chào hàng cạnh tranh",
    "mua sắm công",
    "mua sắm tập trung",
    "gói thầu",
    "hồ sơ mời thầu",
    "hsmt",
    "hồ sơ yêu cầu",
    "hsyk",
    "hồ sơ dự thầu",
    "hsdt",
    "hồ sơ đề xuất",
    "nhà thầu",
    "bên mời thầu",
    "bảo đảm dự thầu",
    "bảo lãnh dự thầu",
    "kết quả lựa chọn nhà thầu",
    "kqlcnt",
    "lựa chọn nhà thầu",
    "lựa chọn nhà đầu tư",
    "kế hoạch lựa chọn nhà thầu",
    "khlcnt",
    "luật đấu thầu",
    "nghị định 24/2024",
    "nghị định 115/2024",
    "thông tư 06/2024",
    "thông tư 07/2024",
    "mạng đấu thầu quốc gia",
    "chỉ định thầu rút gọn",
    "tư vấn đấu thầu",
    "tổ chuyên gia đấu thầu",
]


def matches_bidding_filter(text: str) -> tuple[bool, list[str]]:
    """Kiểm tra xem nội dung có chứa từ khóa liên quan đến đấu thầu không."""
    text_lower = text.lower()
    matched = [kw for kw in KEYWORDS_BIDDING if kw in text_lower]

    # Loại trừ trường hợp chỉ nói về "thuế nhà thầu" trong lĩnh vực thuế thông thường
    if set(matched).issubset({"nhà thầu"}):
        if "thuế nhà thầu" in text_lower or "khấu trừ và nộp thay thuế" in text_lower or "nộp thay thuế" in text_lower:
            # Kiểm tra xem có từ khóa đấu thầu thực sự nào khác không
            has_other = any(
                k in text_lower
                for k in ["đấu thầu", "gói thầu", "hsmt", "hsdt", "chỉ định thầu", "lựa chọn nhà thầu", "bên mời thầu"]
            )
            if not has_other:
                return (False, [])

    return (len(matched) > 0, matched)



def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


def sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_article_links(page: int, session: requests.Session) -> list:
    """Lấy danh sách link Q&A trên một trang danh sách."""
    url = get_category_url(page)
    print(f"  → Trang {page}: {url}")
    resp = session.get(url, headers=HEADERS, timeout=20)
    if resp.status_code == 404 or resp.status_code == 500:
        return []
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    for box in soup.select("div.box-item"):
        title_a = box.select_one("h3 a.question-title")
        if not title_a:
            continue
        title = title_a.get_text(strip=True)
        href = title_a.get("href", "")
        if not href:
            continue
        full_url = urljoin(BASE_URL, href)

        author_el = box.select_one("span.author")
        author = author_el.get_text(strip=True) if author_el else ""
        time_el = box.select_one("span.time")
        pub_time = time_el.get_text(strip=True) if time_el else ""

        items.append({"title": title, "url": full_url, "author": author, "date": pub_time})

    return items


def scrape_article(item: dict, session: requests.Session):
    """Scrape nội dung câu hỏi + trả lời từ trang chi tiết."""
    url = item["url"]
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"    \u2717 L\u1ed7i: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # C\u00e2u h\u1ecfi (class th\u1ef1c t\u1ebf tr\u00ean trang)
    q_block = soup.select_one("div.detail__cquestion")
    question_text = q_block.get_text(separator="\n", strip=True) if q_block else ""

    # C\u00e2u tr\u1ea3 l\u1eddi
    a_block = soup.select_one("div.detail__rcontent")
    answer_text = ""
    agency = ""
    if a_block:
        # C\u01a1 quan tr\u1ea3 l\u1eddi n\u1eb1m trong th\u1ebb <i> d\u1ea7u ti\u00ean
        first_i = a_block.find("i")
        if first_i:
            agency = first_i.get_text(strip=True)
            # X\u00f3a th\u1ebb <i> tr\u01b0\u1edbc khi l\u1ea5y n\u1ed9i dung \u0111\u1ec3 tr\u00e1nh l\u1eb7p
            first_i.decompose()
        answer_text = a_block.get_text(separator="\n", strip=True)

    return {**item, "question": question_text, "answer": answer_text, "agency": agency}


def save_markdown(data: dict, out_dir: Path) -> Path:
    """Lưu Q&A thành file markdown chuẩn llm-wiki raw."""
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(data["title"])
    uid = sha256_short(data["url"])
    filepath = out_dir / f"{slug}-{uid}.md"

    # Chỉ bỏ qua khi file đã có nội dung (để có thể ghi lại những file trước scrape bị trống)
    if filepath.exists() and filepath.stat().st_size > 600:
        return filepath
    today = date.today().isoformat()
    sha = sha256_short(data.get("question", "") + data.get("answer", ""))

    content = (
        f"---\n"
        f"source_url: {data['url']}\n"
        f"ingested: {today}\n"
        f"sha256: {sha}\n"
        f"category: Tài chính – Ngân hàng – Công Thương\n"
        f"author: {data['author']}\n"
        f"published: {data['date']}\n"
        f"agency: {data.get('agency', '')}\n"
        f"---\n\n"
        f"# {data['title']}\n\n"
        f"**Người hỏi:** {data['author']}  \n"
        f"**Ngày:** {data['date']}  \n"
        f"**Cơ quan trả lời:** {data.get('agency', '')}  \n\n"
        f"## Câu hỏi\n\n"
        f"{data.get('question', '_(không lấy được nội dung)_')}\n\n"
        f"## Trả lời\n\n"
        f"{data.get('answer', '_(không lấy được nội dung)_')}\n"
    )
    filepath.write_text(content, encoding="utf-8")
    return filepath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=0, help="Số trang tối đa (0 = tất cả)")
    parser.add_argument("--from-page", type=int, default=1)
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Không lọc từ khóa (lưu toàn bộ tất cả bài viết)",
    )
    args = parser.parse_args()

    session = requests.Session()
    page = args.from_page
    saved = skipped = filtered_out = 0

    print("=" * 60)
    print("Scraper – Tài chính – Ngân hàng – Công Thương")
    print(f"Bộ lọc đấu thầu: {'TẮT' if args.no_filter else 'BẬT'}")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 60)

    while True:
        if args.pages > 0 and (page - args.from_page) >= args.pages:
            print(f"\nĐủ {args.pages} trang. Dừng.")
            break

        print(f"\n[Trang {page}]")
        try:
            items = get_article_links(page, session)
        except Exception as e:
            print(f"  ✗ {e}")
            break

        if not items:
            print("  Không còn bài. Kết thúc.")
            break

        print(f"  Tìm thấy {len(items)} Q&A")
        for i, item in enumerate(items, 1):
            title = item['title']
            print(f"  [{i}/{len(items)}] {title[:55]}...")

            # 1. Kiểm tra nhanh trên tiêu đề nếu có từ khóa
            title_match, title_kws = matches_bidding_filter(title)

            time.sleep(DELAY)
            article = scrape_article(item, session)
            if not article:
                skipped += 1
                continue

            # 2. Nếu chưa tắt lọc, kiểm tra nội dung toàn văn (tiêu đề + câu hỏi + câu trả lời)
            if not args.no_filter:
                full_text = f"{article['title']}\n{article.get('question', '')}\n{article.get('answer', '')}"
                is_match, matched_kws = matches_bidding_filter(full_text)
                if not is_match:
                    print(f"    ↳ ⊘ Bỏ qua (không liên quan đấu thầu)")
                    filtered_out += 1
                    continue
                else:
                    print(f"    ↳ ★ Khớp từ khóa: {', '.join(matched_kws[:3])}")

            p1 = save_markdown(article, OUTPUT_DIR)
            save_markdown(article, OUTPUT_DIR_HERMES)  # bản cho Docker
            saved += 1
            print(f"    ✓ {p1.name}")

        page += 1
        time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"Xong! Đã lưu: {saved}  |  Đã lọc bỏ: {filtered_out}  |  Lỗi: {skipped}")
    print(f"{'='*60}")



if __name__ == "__main__":
    main()
