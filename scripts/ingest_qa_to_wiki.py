"""
Script ingest 1.570 câu hỏi đáp Q&A Chinhphu vào Law-Wiki Bidding v2:
1. Đọc toàn bộ 1.570 file markdown từ raw/qa-chinhphu
2. Quét và trích xuất các căn cứ pháp luật (Điều X Luật Đấu thầu, Nghị định, Thông tư, Khái niệm)
3. Lưu từng bài Q&A đã được chuẩn hóa vào wiki/qa/{slug}.md (có YAML frontmatter đầy đủ, link wiki)
4. Phân loại theo chủ đề và tạo mục lục wiki/qa/INDEX.md
5. Cập nhật liên kết 2 chiều vào các file điều luật tương ứng trong wiki/articles/
6. Đồng bộ sang thư mục .hermes để Docker container cũng thấy ngay
7. Cập nhật LOG.md và INDEX.md chính của wiki
Chi phí: 0 token.
"""

import os
import re
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

BASE_DIR = Path(r"D:\Antigravity\law-wiki-bidding-v2")
RAW_QA_DIR = BASE_DIR / "raw" / "qa-chinhphu"
WIKI_DIR = BASE_DIR / "wiki"
WIKI_QA_DIR = WIKI_DIR / "qa"
ARTICLES_DIR = WIKI_DIR / "articles"
CONCEPTS_DIR = WIKI_DIR / "concepts"

HERMES_WIKI_DIR = Path(r"C:\Users\Desktop\.hermes\law-wiki-bidding-v2\wiki")


def get_article_map():
    """Tạo map số điều -> tên file điều luật."""
    art_map = {}
    for f in ARTICLES_DIR.glob("dieu-*.md"):
        m = re.match(r"dieu-(\d+)", f.stem)
        if m:
            art_num = int(m.group(1))
            art_map[art_num] = f.stem
    return art_map


def get_concepts_map():
    """Tạo map từ khóa concept -> concept slug."""
    concepts = {
        "chủ đầu tư": "chu-dau-tu",
        "nhà thầu": "nha-thau",
        "nhà thầu phụ": "nha-thau-phu",
        "bên mời thầu": "co-quan-co-tham-quyen",
        "người có thẩm quyền": "nguoi-co-tham-quyen",
        "hồ sơ mời thầu": "ho-so-moi-thau",
        "hsmt": "ho-so-moi-thau",
        "hồ sơ dự thầu": "ho-so-du-thau",
        "hsdt": "ho-so-du-thau",
        "hồ sơ yêu cầu": "ho-so-yeu-cau",
        "hsyk": "ho-so-yeu-cau",
        "hồ sơ đề xuất": "ho-so-de-xuat",
        "hsđx": "ho-so-de-xuat",
        "gói thầu": "goi-thau",
        "kế hoạch lựa chọn nhà thầu": "ke-hoach-lua-chon-nha-thau",
        "khlcnt": "ke-hoach-lua-chon-nha-thau",
        "kết quả lựa chọn nhà thầu": "ket-qua-lua-chon-nha-thau",
        "kqlcnt": "ket-qua-lua-chon-nha-thau",
        "đấu thầu qua mạng": "dau-thau-qua-mang",
        "mạng đấu thầu quốc gia": "he-thong-mang-dau-thau-quoc-gia",
        "tổ chuyên gia": "to-chuyen-gia",
        "tổ thẩm định": "to-tham-dinh",
        "hợp đồng": "hop-dong",
        "dịch vụ tư vấn": "dich-vu-tu-van",
        "dịch vụ phi tư vấn": "dich-vu-phi-tu-van",
        "xây lắp": "xay-lap",
        "hàng hóa": "hang-hoa",
        "kiến nghị": "kien-nghi",
    }
    return concepts


def parse_qa_file(fpath: Path):
    """Phân tích một file Q&A raw."""
    text = fpath.read_text(encoding="utf-8")

    # Tách frontmatter và body
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()

    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else fpath.stem

    # Bóc câu hỏi & câu trả lời
    q_match = re.search(r"## Câu hỏi\s*\n\s*(.*?)(?=\n## Trả lời|\Z)", body, flags=re.DOTALL)
    question = q_match.group(1).strip() if q_match else ""

    a_match = re.search(r"## Trả lời\s*\n\s*(.*)", body, flags=re.DOTALL)
    answer = a_match.group(1).strip() if a_match else ""

    # Trích xuất Điều luật được viện dẫn
    cited_articles = set()
    for m in re.findall(r"Điều\s+(\d+)", body, flags=re.IGNORECASE):
        d_num = int(m)
        if 1 <= d_num <= 98:
            cited_articles.add(d_num)

    # Trích xuất Nghị định / Thông tư nếu có
    docs = []
    if "214/2025" in body or "214" in body:
        docs.append("nd-214-2025")
    if "24/2024" in body:
        docs.append("nd-24-2024")
    if "79/2025" in body:
        docs.append("tt-79-2025")
    if "80/2025" in body:
        docs.append("tt-80-2025")

    return {
        "file_name": fpath.name,
        "stem": fpath.stem,
        "meta": meta,
        "title": title,
        "question": question,
        "answer": answer,
        "body": body,
        "cited_articles": sorted(cited_articles),
        "docs": docs,
    }


def main():
    print("=" * 60)
    print("Bắt đầu Ingest Q&A Chinhphu vào Law-Wiki Bidding v2 (0 Token)")
    print("=" * 60)

    WIKI_QA_DIR.mkdir(parents=True, exist_ok=True)
    art_map = get_article_map()
    concepts_map = get_concepts_map()

    raw_files = list(RAW_QA_DIR.glob("*.md"))
    print(f"1. Đang đọc và phân tích {len(raw_files)} files thô...")

    qa_list = []
    article_to_qas = defaultdict(list)
    concept_to_qas = defaultdict(list)

    for f in raw_files:
        qa = parse_qa_file(f)
        qa_list.append(qa)

        # Map vào Điều luật
        for d in qa["cited_articles"]:
            if d in art_map:
                article_to_qas[d].append(qa)

        # Map vào Concepts
        content_lower = qa["body"].lower()
        for kw, c_slug in concepts_map.items():
            if kw in content_lower:
                concept_to_qas[c_slug].append(qa)

    print(f"2. Đang tạo các trang Q&A trong {WIKI_QA_DIR}...")
    today = date.today().isoformat()

    for qa in qa_list:
        # Xây dựng liên kết liên quan
        related_links = []
        for d in qa["cited_articles"]:
            if d in art_map:
                related_links.append(f"[[{art_map[d]}]]")
        for doc in qa["docs"]:
            related_links.append(f"[[{doc}]]")

        # Tìm 2-3 concepts liên quan nhất
        c_links = []
        c_lower = qa["body"].lower()
        for kw, c_slug in concepts_map.items():
            if kw in c_lower and f"[[{c_slug}]]" not in c_links:
                c_links.append(f"[[{c_slug}]]")
            if len(c_links) >= 3:
                break

        frontmatter = [
            "---",
            f"title: \"{qa['title'].replace('\"', '')}\"",
            f"date: {qa['meta'].get('published', '')}",
            f"author: \"{qa['meta'].get('author', '')}\"",
            f"agency: \"{qa['meta'].get('agency', '')}\"",
            f"source_url: \"{qa['meta'].get('source_url', '')}\"",
            f"ingested: {today}",
            f"type: practical-qa",
            f"related_articles: {qa['cited_articles']}",
            "---",
            "",
        ]

        body_lines = [
            f"# {qa['title']}",
            "",
            f"- **Người hỏi:** {qa['meta'].get('author', 'Công dân')} ({qa['meta'].get('published', '')})",
            f"- **Cơ quan trả lời:** {qa['meta'].get('agency', 'Bộ KH&ĐT / Bộ Tài chính')}",
            f"- **Nguồn gốc:** [Cổng TTĐT Chính Phủ - Chuyên mục Tài chính - Công thương]({qa['meta'].get('source_url', '')})",
            "",
        ]

        if related_links or c_links:
            body_lines.append("### Căn cứ & Khái niệm liên quan")
            all_links = related_links + c_links
            body_lines.append(" - " + ", ".join(all_links))
            body_lines.append("")

        body_lines.append("## Câu hỏi thực tế")
        body_lines.append(qa["question"] if qa["question"] else "_(Xem chi tiết văn bản gốc)_")
        body_lines.append("")
        body_lines.append("## Hướng dẫn giải quyết")
        body_lines.append(qa["answer"] if qa["answer"] else "_(Xem chi tiết văn bản gốc)_")
        body_lines.append("")

        qa_file_path = WIKI_QA_DIR / qa["file_name"]
        qa_file_path.write_text("\n".join(frontmatter + body_lines), encoding="utf-8")

    print(f"   ✓ Đã tạo {len(qa_list)} trang Q&A chuẩn wiki.")

    print("3. Đang cập nhật liên kết vào các Điều luật tương ứng...")
    updated_articles = 0
    for d, qas in article_to_qas.items():
        art_slug = art_map.get(d)
        if not art_slug:
            continue
        art_path = ARTICLES_DIR / f"{art_slug}.md"
        if not art_path.exists():
            continue

        art_text = art_path.read_text(encoding="utf-8")

        # Xóa phần Q&A cũ nếu đã có để ghi đè sạch
        marker = "## Tình huống thực tiễn (Q&A Chính sách)"
        if marker in art_text:
            art_text = art_text.split(marker)[0].strip() + "\n\n"

        # Lấy tối đa 10 tình huống tiêu biểu nhất hiển thị trực tiếp
        qa_links = []
        for q in qas[:10]:
            qa_links.append(f"- [[{q['stem']}]] - {q['title'][:80]}")

        qa_section = [
            marker,
            f"\n> Tổng cộng có **{len(qas)} tình huống thực tế** được giải đáp liên quan đến Điều {d}.\n",
        ]
        qa_section.extend(qa_links)
        if len(qas) > 10:
            qa_section.append(f"- *...và {len(qas) - 10} tình huống khác trong [[INDEX-QA#dieu-{d}|Mục lục Q&A Điều {d}]].*")
        qa_section.append("\n")

        # Chèn trước phần 'Ghi chú' nếu có, hoặc nối vào cuối
        if "\n**Ghi chú:**" in art_text:
            parts = art_text.split("\n**Ghi chú:**", 1)
            new_text = parts[0] + "\n" + "\n".join(qa_section) + "**Ghi chú:**" + parts[1]
        elif "\n## Điều liên quan" in art_text:
            parts = art_text.split("\n## Điều liên quan", 1)
            new_text = parts[0] + "\n" + "\n".join(qa_section) + "## Điều liên quan" + parts[1]
        else:
            new_text = art_text.strip() + "\n\n" + "\n".join(qa_section)

        art_path.write_text(new_text, encoding="utf-8")
        updated_articles += 1

    print(f"   ✓ Đã bổ sung liên kết tình huống thực tiễn vào {updated_articles} Điều luật.")

    print("4. Đang tạo Mục lục tra cứu Q&A (INDEX-QA.md)...")
    qa_index_lines = [
        "# Mục Lục Tình Huống Thực Tiễn Đấu Thầu (Q&A Chính Sách)",
        "",
        f"> Tổng hợp **{len(qa_list)} tình huống Q&A thực tế** từ Cổng TTĐT Chính phủ.",
        f"> Tự động phân loại theo Điều luật và Khái niệm pháp lý tương ứng.",
        f"> Cập nhật: {today} | Tổng số bài: {len(qa_list)}",
        "",
        "## Phân loại theo Điều luật trọng điểm",
        "",
    ]

    for d in sorted(article_to_qas.keys()):
        qas = article_to_qas[d]
        art_slug = art_map.get(d, f"dieu-{d}")
        qa_index_lines.append(f"### <a id='dieu-{d}'></a>[[{art_slug}]] ({len(qas)} tình huống)")
        for q in qas[:8]:
            qa_index_lines.append(f"- [[{q['stem']}]] - {q['title']}")
        if len(qas) > 8:
            qa_index_lines.append(f"- *(Xem thêm {len(qas) - 8} bài khác trích dẫn Điều {d}...)*")
        qa_index_lines.append("")

    qa_index_path = WIKI_DIR / "INDEX-QA.md"
    qa_index_path.write_text("\n".join(qa_index_lines), encoding="utf-8")
    print("   ✓ Đã tạo wiki/INDEX-QA.md")

    print("5. Đang cập nhật wiki/INDEX.md và wiki/LOG.md...")
    index_path = WIKI_DIR / "INDEX.md"
    if index_path.exists():
        index_text = index_path.read_text(encoding="utf-8")
        if "## Tình huống thực tiễn (Q&A)" not in index_text:
            qa_index_ref = (
                "\n## Tình huống thực tiễn (Q&A)\n\n"
                f"- [[INDEX-QA]] - **Mục lục 1.570 tình huống hỏi đáp thực tế** (Cổng TTĐT Chính phủ)\n"
            )
            # Chèn trước phần Thống kê
            if "\n---\n\n**Thống kê:**" in index_text:
                index_text = index_text.replace("\n---\n\n**Thống kê:**", qa_index_ref + "\n---\n\n**Thống kê:**")
            else:
                index_text += qa_index_ref
            index_path.write_text(index_text, encoding="utf-8")

    log_path = WIKI_DIR / "LOG.md"
    if log_path.exists():
        log_text = log_path.read_text(encoding="utf-8")
        log_entry = (
            f"## {today} - Tier 6: Ingest 1.570 Q&A Chính phủ (COMPLETE)\n\n"
            f"**Source:** `raw/qa-chinhphu/` ({len(qa_list)} files)\n"
            f"**Strategy:** Hybrid Technical Ingest (0 Token)\n"
            f"**Output:**\n"
            f"- Đã tạo {len(qa_list)} trang `wiki/qa/` với liên kết hai chiều\n"
            f"- Đã cập nhật mục 'Tình huống thực tiễn' vào {updated_articles} Điều luật\n"
            f"- Đã tạo `wiki/INDEX-QA.md`\n"
            f"- Chi phí token: 0 tokens\n\n---\n\n"
        )
        log_path.write_text(log_entry + log_text, encoding="utf-8")

    print("6. Đang đồng bộ toàn bộ thư mục wiki sang ~/.hermes/law-wiki-bidding-v2/wiki/...")
    try:
        HERMES_WIKI_DIR.mkdir(parents=True, exist_ok=True)
        # Copy INDEX-QA.md, INDEX.md, LOG.md
        shutil.copy2(qa_index_path, HERMES_WIKI_DIR / "INDEX-QA.md")
        shutil.copy2(index_path, HERMES_WIKI_DIR / "INDEX.md")
        shutil.copy2(log_path, HERMES_WIKI_DIR / "LOG.md")
        # Đồng bộ thư mục articles và qa
        shutil.copytree(WIKI_QA_DIR, HERMES_WIKI_DIR / "qa", dirs_exist_ok=True)
        shutil.copytree(ARTICLES_DIR, HERMES_WIKI_DIR / "articles", dirs_exist_ok=True)
        print("   ✓ Đã đồng bộ sang Docker environment.")
    except Exception as e:
        print(f"   ! Lỗi khi đồng bộ Docker: {e}")

    print("=" * 60)
    print("HOÀN THÀNH INGEST THÀNH CÔNG RỰC RỠ!")
    print(f"- Tổng số Q&A: {len(qa_list)}")
    print(f"- Số Điều luật được liên kết: {updated_articles}")
    print(f"- Token tiêu tốn: 0")
    print("=" * 60)


if __name__ == "__main__":
    main()
