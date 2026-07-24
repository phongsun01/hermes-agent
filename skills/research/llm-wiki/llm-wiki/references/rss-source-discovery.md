# RSS/Atom Source Discovery for the Wiki

This reference covers using `blogwatcher-cli` to automatically discover new content from blogs, news sites, and RSS/Atom feeds. Results feed directly into the wiki's ingestion pipeline — scan new articles, then ingest the interesting ones into `raw/` and update wiki pages.

## Installation

```bash
# Go (recommended for most platforms)
go install github.com/JulienTant/blogwatcher-cli/cmd/blogwatcher-cli@latest

# Homebrew
brew install JulienTant/tap/blogwatcher-cli

# Binary (Linux amd64)
curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_linux_amd64.tar.gz | tar xz -C /usr/local/bin blogwatcher-cli

# Binary (macOS Apple Silicon)
curl -sL https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_darwin_arm64.tar.gz | tar xz -C /usr/local/bin blogwatcher-cli
```

## Quick Setup

```bash
# Add a blog (auto-discovers RSS/Atom feed)
blogwatcher-cli add "My Blog" https://example.com

# Add with explicit feed URL
blogwatcher-cli add "My Blog" https://example.com --feed-url https://example.com/feed.xml

# Bulk import from OPML (Feedly, Inoreader, etc.)
blogwatcher-cli import subscriptions.opml

# List tracked blogs
blogwatcher-cli blogs
```

## Common Operations

### Scan for new articles
```bash
# Scan all blogs
blogwatcher-cli scan

# Scan one blog
blogwatcher-cli scan "My Blog"
```

### Read new articles
```bash
# List unread articles
blogwatcher-cli articles

# List all articles
blogwatcher-cli articles --all

# Filter by blog or category
blogwatcher-cli articles --blog "My Blog"
blogwatcher-cli articles --category "Engineering"

# Mark article read (by number)
blogwatcher-cli read 1
blogwatcher-cli read-all
```

### Environment variables
| Variable | Description |
|---|---|
| `BLOGWATCHER_DB` | Path to SQLite database (default: `~/.blogwatcher-cli/blogwatcher-cli.db`) |
| `BLOGWATCHER_WORKERS` | Concurrent scan workers (default: 8) |

## Integration with the Wiki

**Workflow for agent-driven ingestion:**

1. Scan: `blogwatcher-cli scan` — check what's new
2. Read: `blogwatcher-cli articles` — list new articles with titles and URLs
3. Extract: Use `web_extract` on interesting article URLs
4. Ingest: Save to `raw/articles/<topic-slug>.md` following wiki conventions
5. Update: Process into existing or new wiki pages as per the Ingest section of SKILL.md

**Workflow for cron-driven automatic discovery:**

Schedule a cron job that runs `blogwatcher-cli scan && blogwatcher-cli articles` and delivers new articles as a notification. The user reviews the batch and asks the agent to ingest specific ones.

```bash
# Check for new content in a cron script
#!/bin/bash
blogwatcher-cli scan --silent
unread=$(blogwatcher-cli articles --all 2>/dev/null | head -20)
if [ -n "$unread" ]; then
    echo "New blog articles:"
    echo "$unread"
fi
```

## Docker

```bash
# With persistent volume
docker run --rm \
  -v blogwatcher-cli:/data \
  -e BLOGWATCHER_DB=/data/blogwatcher-cli.db \
  ghcr.io/julientant/blogwatcher-cli scan
```

## Notes

- Auto-discovers RSS/Atom feeds from blog homepages
- Falls back to HTML scraping with `--scrape-selector` if RSS unavailable
- Database at `~/.blogwatcher-cli/blogwatcher-cli.db` (override with `BLOGWATCHER_DB`)
- Use `blogwatcher-cli <command> --help` for all flags
