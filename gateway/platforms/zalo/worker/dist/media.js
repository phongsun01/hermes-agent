import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import * as crypto from "node:crypto";
// ─── Constants ───────────────────────────────────────────────────────────────
const ZALO_MAX_MESSAGE_LENGTH = 2000;
const MEDIA_CACHE_TTL = 3600 * 1000; // 1 hour
const MEDIA_CACHE_DIR = path.join(os.tmpdir(), "zalo-media-cache");
// ─── Message Formatting ──────────────────────────────────────────────────────
/**
 * Convert Markdown-like text to Zalo styled text.
 * Zalo supports basic HTML-like tags: <b>, <i>, <u>, <s>, <a href="...">
 */
export function formatMarkdownToZalo(text) {
    let result = text;
    // Bold: **text** or __text__ → <b>text</b>
    result = result.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    result = result.replace(/__(.+?)__/g, "<b>$1</b>");
    // Italic: *text* or _text_ → <i>text</i>
    result = result.replace(/\*(.+?)\*/g, "<i>$1</i>");
    result = result.replace(/(?<!\w)_(.+?)_(?!\w)/g, "<i>$1</i>");
    // Strikethrough: ~~text~~ → <s>text</s>
    result = result.replace(/~~(.+?)~~/g, "<s>$1</s>");
    // Underline: ==text== → <u>text</u>
    result = result.replace(/==(.+?)==/g, "<u>$1</u>");
    // Inline code: `text` → <code>text</code> (monospace)
    result = result.replace(/`([^`]+)`/g, "<code>$1</code>");
    // Links: [text](url) → <a href="url">text</a>
    result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
    return result;
}
/**
 * Truncate message to Zalo's max length, preserving word boundaries.
 */
export function truncateMessage(text, maxLength = ZALO_MAX_MESSAGE_LENGTH) {
    if (text.length <= maxLength) {
        return { text, truncated: false };
    }
    // Try to break at word boundary
    let truncated = text.substring(0, maxLength);
    const lastSpace = truncated.lastIndexOf(" ");
    if (lastSpace > maxLength * 0.8) {
        truncated = truncated.substring(0, lastSpace);
    }
    return { text: truncated + "\n...(truncated)", truncated: true };
}
/**
 * Prepare message for sending: format + truncate.
 */
export function prepareMessage(text, options) {
    let result = text;
    if (options?.formatMarkdown !== false) {
        result = formatMarkdownToZalo(result);
    }
    return truncateMessage(result);
}
// ─── Media Cache ─────────────────────────────────────────────────────────────
/**
 * Ensure the media cache directory exists.
 */
function ensureCacheDir() {
    if (!fs.existsSync(MEDIA_CACHE_DIR)) {
        fs.mkdirSync(MEDIA_CACHE_DIR, { recursive: true });
    }
    return MEDIA_CACHE_DIR;
}
/**
 * Generate a cache key for a media URL.
 */
function cacheKey(url) {
    const hash = crypto.createHash("md5").update(url).digest("hex");
    return hash;
}
/**
 * Get the cache file path for a media URL.
 */
function getCachePath(url, ext = "bin") {
    const key = cacheKey(url);
    return path.join(ensureCacheDir(), `${key}.${ext}`);
}
/**
 * Get the metadata file path for a cached media item.
 */
function getMetaPath(url) {
    const key = cacheKey(url);
    return path.join(ensureCacheDir(), `${key}.meta.json`);
}
/**
 * Check if a URL is cached and still valid.
 */
export function isMediaCached(url) {
    const metaPath = getMetaPath(url);
    if (!fs.existsSync(metaPath))
        return false;
    try {
        const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
        const age = Date.now() - meta.cachedAt;
        if (age > MEDIA_CACHE_TTL) {
            // Expired, clean up
            try {
                fs.unlinkSync(getCachePath(url));
            }
            catch { }
            try {
                fs.unlinkSync(metaPath);
            }
            catch { }
            return false;
        }
        return fs.existsSync(getCachePath(url));
    }
    catch {
        return false;
    }
}
/**
 * Get the local path of a cached media file.
 */
export function getCachedMediaPath(url, ext = "bin") {
    if (!isMediaCached(url))
        return null;
    return getCachePath(url, ext);
}
/**
 * Download and cache media from a URL.
 */
export async function downloadAndCacheMedia(url, ext = "bin") {
    // Check cache first
    const cached = getCachedMediaPath(url, ext);
    if (cached)
        return cached;
    const cachePath = getCachePath(url, ext);
    const metaPath = getMetaPath(url);
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to download media: ${response.status} ${response.statusText}`);
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    fs.writeFileSync(cachePath, buffer);
    const meta = {
        url,
        cachedAt: Date.now(),
        size: buffer.length,
        contentType: response.headers.get("content-type") || undefined,
    };
    fs.writeFileSync(metaPath, JSON.stringify(meta));
    return cachePath;
}
/**
 * Clean up expired cache entries.
 */
export function cleanupCache() {
    if (!fs.existsSync(MEDIA_CACHE_DIR))
        return 0;
    let cleaned = 0;
    const files = fs.readdirSync(MEDIA_CACHE_DIR);
    for (const file of files) {
        if (!file.endsWith(".meta.json"))
            continue;
        const metaPath = path.join(MEDIA_CACHE_DIR, file);
        try {
            const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
            const age = Date.now() - meta.cachedAt;
            if (age > MEDIA_CACHE_TTL) {
                const baseName = file.replace(".meta.json", "");
                try {
                    fs.unlinkSync(path.join(MEDIA_CACHE_DIR, baseName));
                }
                catch { }
                fs.unlinkSync(metaPath);
                cleaned++;
            }
        }
        catch {
            // Invalid meta, clean up
            try {
                fs.unlinkSync(metaPath);
            }
            catch { }
        }
    }
    return cleaned;
}
/**
 * Clear all cached media.
 */
export function clearCache() {
    if (!fs.existsSync(MEDIA_CACHE_DIR))
        return;
    const files = fs.readdirSync(MEDIA_CACHE_DIR);
    for (const file of files) {
        try {
            fs.unlinkSync(path.join(MEDIA_CACHE_DIR, file));
        }
        catch { }
    }
}
// ─── Media Download Helpers ──────────────────────────────────────────────────
/**
 * Download a file from URL to a temporary location.
 * Returns the path and a cleanup function.
 */
export async function downloadToTemp(url, prefix = "zalo") {
    const tmpDir = os.tmpdir();
    const ext = path.extname(new URL(url).pathname) || ".bin";
    const tmpPath = path.join(tmpDir, `${prefix}-${Date.now()}${ext}`);
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to download: ${response.status} ${response.statusText}`);
    }
    const buffer = Buffer.from(await response.arrayBuffer());
    fs.writeFileSync(tmpPath, buffer);
    return {
        path: tmpPath,
        cleanup: () => { try {
            fs.unlinkSync(tmpPath);
        }
        catch { } }
    };
}
/**
 * Resolve a media source: if URL, download to temp; if local path, verify exists.
 * Returns the resolved path and a cleanup function.
 */
export async function resolveMediaSource(source, prefix = "zalo") {
    if (/^https?:\/\//i.test(source)) {
        return downloadToTemp(source, prefix);
    }
    // Local path
    if (!fs.existsSync(source)) {
        throw new Error(`File not found: ${source}`);
    }
    return { path: source, cleanup: () => { } };
}
// ─── Received Media Detection ────────────────────────────────────────────────
/**
 * Detect media type from a raw zca-js message.
 * Returns { type, url?, mimeType?, fileName? } or null if not media.
 */
export function detectReceivedMedia(raw) {
    // zca-js may include media info in various fields
    const msgType = raw?.type ?? raw?.msgType ?? raw?.data?.type;
    // Check for image attachments
    if (msgType === "image" || msgType === "photo") {
        return {
            type: "image",
            url: raw?.url ?? raw?.data?.url ?? raw?.thumbUrl ?? raw?.data?.thumbUrl,
            mimeType: raw?.mimeType ?? raw?.data?.mimeType,
            fileName: raw?.fileName ?? raw?.data?.fileName,
        };
    }
    // Check for file attachments
    if (msgType === "file" || msgType === "document") {
        return {
            type: "file",
            url: raw?.url ?? raw?.data?.url,
            mimeType: raw?.mimeType ?? raw?.data?.mimeType,
            fileName: raw?.fileName ?? raw?.data?.fileName,
        };
    }
    // Check for video
    if (msgType === "video") {
        return {
            type: "video",
            url: raw?.url ?? raw?.data?.url,
            mimeType: raw?.mimeType ?? raw?.data?.mimeType,
            fileName: raw?.fileName ?? raw?.data?.fileName,
        };
    }
    // Check for attachments array
    const attachments = raw?.attachments ?? raw?.data?.attachments;
    if (Array.isArray(attachments) && attachments.length > 0) {
        const first = attachments[0];
        if (typeof first === "object") {
            const attType = first.type ?? first.fileType ?? "file";
            return {
                type: attType,
                url: first.url ?? first.downloadUrl,
                mimeType: first.mimeType,
                fileName: first.fileName ?? first.name,
            };
        }
    }
    return null;
}
