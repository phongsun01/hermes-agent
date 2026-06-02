/**
 * Credential storage with security hardening.
 *
 * [H1] File permissions set to 0600 (owner read/write only).
 * Note: Full encryption is not implemented here to avoid key management complexity,
 * but file permissions prevent other users/processes from reading credentials.
 */
import { readFileSync, writeFileSync, unlinkSync, existsSync, chmodSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { homedir } from "node:os";
/**
 * Resolve the Hermes data directory.
 *
 * In Docker, HERMES_HOME=/opt/data is the mounted ~/.hermes volume.
 * On bare metal, HERMES_HOME is typically unset — fall back to ~/.hermes.
 */
function getHermesDataDir() {
    const hermesHome = process.env.HERMES_HOME;
    if (hermesHome) {
        return join(hermesHome, "data");
    }
    return join(homedir(), ".hermes", "data");
}
const DATA_DIR = getHermesDataDir();
const CREDENTIALS_PATH = join(DATA_DIR, "zaloclaw-credentials.json");
/**
 * Save credentials to disk with restrictive file permissions.
 * [H1] chmod 0600 — only the file owner can read/write.
 */
export function saveCredentials(data) {
    const dir = dirname(CREDENTIALS_PATH);
    if (!existsSync(dir)) {
        mkdirSync(dir, { recursive: true, mode: 0o700 });
    }
    writeFileSync(CREDENTIALS_PATH, JSON.stringify(data, null, 2), { encoding: "utf-8", mode: 0o600 });
    // Ensure permissions even if file existed with different mode
    try {
        chmodSync(CREDENTIALS_PATH, 0o600);
    }
    catch {
        // Non-critical — may fail on Windows
    }
}
export function loadCredentials() {
    if (!existsSync(CREDENTIALS_PATH)) {
        return null;
    }
    try {
        const raw = readFileSync(CREDENTIALS_PATH, "utf-8");
        return JSON.parse(raw);
    }
    catch {
        return null;
    }
}
export function deleteCredentials() {
    if (existsSync(CREDENTIALS_PATH)) {
        unlinkSync(CREDENTIALS_PATH);
    }
}
export function hasCredentials() {
    return existsSync(CREDENTIALS_PATH);
}
export function refreshCredentials(freshCookies) {
    const existing = loadCredentials();
    if (!existing)
        return;
    existing.cookie = freshCookies;
    saveCredentials(existing);
}
