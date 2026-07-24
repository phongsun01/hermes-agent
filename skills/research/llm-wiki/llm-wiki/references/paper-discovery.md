# Paper Discovery via arXiv & Semantic Scholar

This reference covers searching academic papers on arXiv and enriching them with citation data from Semantic Scholar. Results feed into the wiki's ingestion pipeline — find papers, read abstracts, then ingest the important ones into `raw/papers/` and update wiki pages.

## Quick Reference

| Action | Command |
|--------|---------|
| Search papers (XML) | `curl "https://export.arxiv.org/api/query?search_query=all:QUERY&max_results=5"` |
| Get specific paper | `curl "https://export.arxiv.org/api/query?id_list=2402.03300"` |
| Read abstract | `web_extract(urls=["https://arxiv.org/abs/2402.03300"])` |
| Read PDF | `web_extract(urls=["https://arxiv.org/pdf/2402.03300"])` |
| Citations/refs (JSON) | `curl "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=title,citationCount"` |

## Helper Script

A Python script (`scripts/search_arxiv.py`) wraps the arXiv API with clean output, no dependencies:

```bash
# From the llm-wiki skill directory
python3 scripts/search_arxiv.py "GRPO reinforcement learning"
python3 scripts/search_arxiv.py "transformer attention" --max 10 --sort date
python3 scripts/search_arxiv.py --author "Yann LeCun" --max 5
python3 scripts/search_arxiv.py --category cs.AI --sort date
python3 scripts/search_arxiv.py --id 2402.03300
python3 scripts/search_arxiv.py --id 2402.03300,2401.12345
```

## arXiv Search Syntax

### Search prefixes
| Prefix | Searches | Example |
|--------|----------|---------|
| `all:` | All fields | `all:transformer+attention` |
| `ti:` | Title | `ti:large+language+models` |
| `au:` | Author | `au:vaswani` |
| `abs:` | Abstract | `abs:reinforcement+learning` |
| `cat:` | Category | `cat:cs.AI` |
| `co:` | Comment | `co:accepted+NeurIPS` |

### Boolean operators
```
# AND (default)
search_query=all:transformer+attention

# OR
search_query=all:GPT+OR+all:BERT

# AND NOT
search_query=all:language+model+ANDNOT+all:vision

# Exact phrase
search_query=ti:"chain+of+thought"

# Combined
search_query=au:hinton+AND+cat:cs.LG
```

### Sort and pagination
| Parameter | Options |
|-----------|---------|
| `sortBy` | `relevance`, `lastUpdatedDate`, `submittedDate` |
| `sortOrder` | `ascending`, `descending` |
| `start` | Result offset (0-based) |
| `max_results` | 1–30000 (default 10) |

```bash
# Latest 10 papers in cs.AI
curl -s "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10"
```

### Clean XML parsing (inline)
```bash
curl -s "https://export.arxiv.org/api/query?search_query=all:GRPO+reinforcement+learning&max_results=5&sortBy=submittedDate&sortOrder=descending" | python3 -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for i, entry in enumerate(root.findall('a:entry', ns)):
    title = entry.find('a:title', ns).text.strip().replace('\n', ' ')
    arxiv_id = entry.find('a:id', ns).text.strip().split('/abs/')[-1]
    published = entry.find('a:published', ns).text[:10]
    authors = ', '.join(a.find('a:name', ns).text for a in entry.findall('a:author', ns))
    summary = entry.find('a:summary', ns).text.strip()[:200]
    cats = ', '.join(c.get('term') for c in entry.findall('a:category', ns))
    print(f'{i+1}. [{arxiv_id}] {title}')
    print(f'   Authors: {authors} | Published: {published} | Categories: {cats}')
    print(f'   PDF: https://arxiv.org/pdf/{arxiv_id}')
    print()
"
```

## Semantic Scholar (Citations, Related Work)

arXiv doesn't provide citation data. Use Semantic Scholar API (free, no key for basic use).

### Get paper details + citations
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300?fields=title,authors,citationCount,referenceCount,influentialCitationCount,year,abstract" | python3 -m json.tool
```

### Who cited this paper?
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/citations?fields=title,authors,year,citationCount&limit=10"
```

### What does this paper cite?
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:2402.03300/references?fields=title,authors,year,citationCount&limit=20"
```

### Search papers (JSON output)
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=GRPO+reinforcement+learning&limit=5&fields=title,authors,year,citationCount,externalIds"
```

### Get recommendations
```bash
curl -s -X POST "https://api.semanticscholar.org/recommendations/v1/papers/" \
  -H "Content-Type: application/json" \
  -d '{"positivePaperIds": ["arXiv:2402.03300"], "negativePaperIds": []}'
```

### Author profile
```bash
curl -s "https://api.semanticscholar.org/graph/v1/author/search?query=Yann+LeCun&fields=name,hIndex,citationCount,paperCount"
```

### Useful fields
`title`, `authors`, `year`, `abstract`, `citationCount`, `referenceCount`, `influentialCitationCount`, `isOpenAccess`, `openAccessPdf`, `fieldsOfStudy`, `publicationVenue`, `externalIds`

## Complete Research Workflow

1. **Discover**: `python3 scripts/search_arxiv.py "your topic" --sort date --max 10`
2. **Assess impact**: `curl -s "https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=citationCount,influentialCitationCount"`
3. **Read abstract**: `web_extract(urls=["https://arxiv.org/abs/ID"])`
4. **Read full paper**: `web_extract(urls=["https://arxiv.org/pdf/ID"])`
5. **Find related work**: Semantic Scholar references endpoint
6. **Ingest into wiki**: Save to `raw/papers/` with proper frontmatter, update entity/concept pages

## Rate Limits

| API | Rate | Auth |
|-----|------|------|
| arXiv | ~1 req / 3 seconds | None |
| Semantic Scholar | 1 req / second | None (100/sec with API key) |

## Notes

- arXiv IDs: old format (`hep-th/0601001`) vs new (`2402.03300` — YYMM.XXXXX)
- PDF URL: `https://arxiv.org/pdf/{id}` — Abstract: `https://arxiv.org/abs/{id}`
- HTML (when available): `https://arxiv.org/html/{id}`
- For withdrawn papers, check `<summary>` for "withdrawn" or "retracted" before treating as valid
- Semantic Scholar returns JSON — pipe through `python3 -m json.tool` for readability
- The helper script at `scripts/search_arxiv.py` is Python stdlib-only, no dependencies
