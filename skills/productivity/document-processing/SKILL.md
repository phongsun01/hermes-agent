---
name: document-processing
description: "Create, extract, and edit office documents: PDF extraction & OCR, PowerPoint presentations, and Word documents."
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, PowerPoint, PPTX, Documents, OCR, Extraction, Office]
    category: productivity
---

# Document Processing — PDFs, PowerPoint, Word

Tools for working with office document formats. Covers PDF text extraction and OCR, PowerPoint creation/editing, and Word document parsing.

---

## PDF & Document Extraction

For **DOCX**: use `python-docx` (parses actual document structure, far better than OCR). For **PPTX**: see the PowerPoint section below.

This section covers **PDFs and scanned documents**.

### Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
```

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

### Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| Text-based PDF | ✅ | ✅ |
| Scanned PDF (OCR) | ❌ | ✅ (90+ languages) |
| Tables | ✅ (basic) | ✅ (high accuracy) |
| Equations / LaTeX | ❌ | ✅ |
| Markdown output | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| Install size | ~25MB | ~3-5GB (PyTorch + models) |
| Speed | Instant | ~1-14s/page (CPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

### pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

**Via helper script:**
```bash
python3 scripts/extract_pymupdf.py document.pdf              # Plain text
python3 scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python3 scripts/extract_pymupdf.py document.pdf --tables      # Tables
python3 scripts/extract_pymupdf.py document.pdf --metadata    # Metadata
python3 scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

### marker-pdf (high-quality OCR)

```bash
pip install marker-pdf
python3 scripts/extract_marker.py document.pdf                # Markdown
python3 scripts/extract_marker.py document.pdf --json         # JSON
python3 scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

### Split, Merge & Search

```python
import pymupdf

# Split
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")

# Search
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
```

### Quick PDF Edits (nano-pdf)

```bash
uv pip install nano-pdf
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results'"
```

### Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- marker-pdf downloads ~2.5GB of models on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)

---

## PowerPoint

Create, read, edit .pptx decks, slides, notes, templates.

### Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python -m markitdown presentation.pptx` |
| Edit or create from template | See `references/editing.md` |
| Create from scratch | See `references/pptxgenjs.md` |

### Reading Content

```bash
python -m markitdown presentation.pptx
```

> Note: `scripts/thumbnail.py` (generate visual slide overview) and `scripts/office/unpack.py` (unpack to raw XML) are community-contributed scripts. If missing, install via: `pip install markitdown[pptx]` for text extraction, or LibreOffice for PDF-based visual inspection (see Converting to Images below).

### Editing Workflow

See `references/editing.md` for full details.

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

### Creating from Scratch

See `references/pptxgenjs.md` for full details. Use when no template or reference presentation is available.

### Design Principles

**Don't create boring slides.** Consider:

**Color palettes:**
| Theme | Primary | Secondary | Accent |
|-------|---------|-----------|--------|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` |

**Typography:** Pick a font pairing with personality — Georgia + Calibri, Arial Black + Arial, etc.

**Layout:** Every slide needs a visual element (image, chart, icon, or shape). Text-only slides are forgettable.

**Avoid:**
- Plain bullets on white backgrounds
- Accent lines under titles (hallmark of AI-generated slides)
- Light text on light backgrounds (low contrast)
- Repeating the same layout across all slides
- Defaulting to blue — pick colors for the topic

### QA (Required)

Assume there are problems. Your job is to find them.

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

**Visual QA:** Convert slides to images, inspect with a subagent for fresh eyes:
```bash
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

### Converting to Images

```bash
# Convert PPTX to PDF, then to slide images
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

To re-render specific slides after fixes:

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

### Dependencies

- `pip install "markitdown[pptx]"` — text extraction
- `pip install Pillow` — thumbnail grids
- `npm install -g pptxgenjs` — creating from scratch
- LibreOffice (`soffice`) — PDF conversion (`soffice --headless --convert-to pdf`)
- Poppler (`pdftoppm`) — PDF to images
