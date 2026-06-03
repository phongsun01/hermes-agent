import { Zalo, LoginQRCallbackEventType, type API } from "zca-js";
import type { LoginQRCallbackEvent } from "zca-js";
import {
  saveCredentials,
  loadCredentials,
  deleteCredentials,
  hasCredentials,
  refreshCredentials,
} from "./credentials.js";
import sharp from "sharp";
import * as fs from "fs";

let apiInstance: API | null = null;
let currentUid: string | null = null;
/** [H2] Promise memoization to prevent concurrent login attempts */
let loginPromise: Promise<API> | null = null;

/** Cookie auto-save interval (default: 30 minutes) */
const COOKIE_SAVE_INTERVAL_MS = parseInt(
  process.env.ZALO_COOKIE_SAVE_INTERVAL_MS || "1800000",
  10
);

/** Session health check interval (default: 60 minutes) */
const SESSION_CHECK_INTERVAL_MS = parseInt(
  process.env.ZALO_SESSION_CHECK_INTERVAL_MS || "3600000",
  10
);

export type QrCallback = (event: LoginQRCallbackEvent) => unknown;

async function imageMetadataGetter(filePath: string) {
  const data = await fs.promises.readFile(filePath);
  const metadata = await sharp(data).metadata();
  return {
    height: metadata.height || 0,
    width: metadata.width || 0,
    size: metadata.size || data.length,
  };
}

export async function loginWithQR(callback?: QrCallback): Promise<API> {
  const zalo = new Zalo({ logging: false, imageMetadataGetter });
  const api = await zalo.loginQR(undefined, (event) => {
    if (event.type === LoginQRCallbackEventType.GotLoginInfo && event.data) {
      saveCredentials({
        imei: event.data.imei,
        cookie: event.data.cookie,
        userAgent: event.data.userAgent,
      });
    }
    callback?.(event);
  });
  apiInstance = api;
  try {
    const raw = await api.fetchAccountInfo();
    const info = (raw as any)?.profile ?? raw;
    currentUid = info?.userId ?? null;
  } catch {
    // non-critical
  }
  return api;
}

export async function loginWithCredentials(): Promise<API> {
  const creds = loadCredentials();
  if (!creds) {
    throw new Error("No saved credentials found. Login with QR first.");
  }
  const zalo = new Zalo({ logging: false, imageMetadataGetter });
  const api = await zalo.login({
    imei: creds.imei,
    cookie: creds.cookie as any,
    userAgent: creds.userAgent,
    language: creds.language,
  });
  apiInstance = api;
  try {
    const raw = await api.fetchAccountInfo();
    const info = (raw as any)?.profile ?? raw;
    currentUid = info?.userId ?? null;
  } catch {
    // non-critical
  }
  return api;
}

/**
 * Get the API singleton safely with race condition protection.
 * [H2] Uses promise memoization — concurrent callers wait for the same login attempt.
 */
export async function getApi(): Promise<API> {
  if (apiInstance) {
    return apiInstance;
  }
  if (!hasCredentials()) {
    throw new Error("Not authenticated. Login with QR first.");
  }
  // If a login is already in progress, wait for it
  if (loginPromise) {
    return loginPromise;
  }
  // Start login and memoize the promise
  loginPromise = loginWithCredentials().finally(() => {
    loginPromise = null;
  });
  return loginPromise;
}

export function getApiSync(): API | null {
  return apiInstance;
}

export function getCurrentUid(): string | null {
  return currentUid;
}

export function isAuthenticated(): boolean {
  return apiInstance !== null;
}

export function hasStoredCredentials(): boolean {
  return hasCredentials();
}

export async function logout(): Promise<void> {
  apiInstance = null;
  currentUid = null;
  loginPromise = null;
  deleteCredentials();
}

export async function ensureAuthenticated(): Promise<API> {
  return getApi();
}

// ─── Cookie Auto-Save ────────────────────────────────────────────────────────
// zca-js refreshes cookies internally during API calls. This interval timer
// periodically extracts the current CookieJar and saves it to disk so that
// a restarted worker can resume without requiring QR re-login.

let cookieSaveTimer: ReturnType<typeof setInterval> | null = null;

export function startCookieAutoSave(): void {
  stopCookieAutoSave();
  cookieSaveTimer = setInterval(() => {
    if (!apiInstance) return;
    try {
      const jar = apiInstance.getCookie();
      if (jar) {
        refreshCredentials(jar);
      }
    } catch (err: any) {
      console.error(`[CookieAutoSave] Failed to save cookies: ${err.message}`);
    }
  }, COOKIE_SAVE_INTERVAL_MS);
  console.error(
    `[CookieAutoSave] Enabled (interval: ${COOKIE_SAVE_INTERVAL_MS / 1000}s)`
  );
}

export function stopCookieAutoSave(): void {
  if (cookieSaveTimer) {
    clearInterval(cookieSaveTimer);
    cookieSaveTimer = null;
  }
}

// ─── Session Health Monitor ──────────────────────────────────────────────────
// Periodically checks if the session is still valid by reading the cached
// user ID from the API context (local, no network request). If getOwnId()
// returns null or throws an auth-related error, the session is considered
// degraded. Emits an event so the Python adapter can alert the user and
// trigger QR re-login.

let sessionCheckTimer: ReturnType<typeof setInterval> | null = null;
let consecutiveAuthFailures = 0;
const MAX_CONSECUTIVE_FAILURES = 3;

export type SessionHealthCallback = (
  status: "healthy" | "expiring" | "expired"
) => void;

let healthCallback: SessionHealthCallback | null = null;

export function setSessionHealthCallback(cb: SessionHealthCallback): void {
  healthCallback = cb;
}

export function startSessionHealthMonitor(): void {
  stopSessionHealthMonitor();
  consecutiveAuthFailures = 0;

  sessionCheckTimer = setInterval(async () => {
    if (!apiInstance) return;

    try {
      // Lightweight health check — getOwnId is fast and requires valid session
      const uid = apiInstance.getOwnId();
      if (uid) {
        consecutiveAuthFailures = 0;
        healthCallback?.("healthy");
      } else {
        handleSessionDegradation();
      }
    } catch (err: any) {
      const msg = (err.message || "").toLowerCase();
      // Check for auth-related errors
      if (
        msg.includes("auth") ||
        msg.includes("unauthorized") ||
        msg.includes("forbidden") ||
        msg.includes("401") ||
        msg.includes("403") ||
        msg.includes("token") ||
        msg.includes("session") ||
        msg.includes("cookie")
      ) {
        handleSessionDegradation();
      } else {
        // Non-auth error — likely transient network issue
        console.error(
          `[SessionHealth] Non-auth error during check: ${err.message}`
        );
      }
    }
  }, SESSION_CHECK_INTERVAL_MS);

  console.error(
    `[SessionHealth] Monitor enabled (interval: ${SESSION_CHECK_INTERVAL_MS / 1000}s)`
  );
}

function handleSessionDegradation(): void {
  consecutiveAuthFailures++;
  console.error(
    `[SessionHealth] Auth failure ${consecutiveAuthFailures}/${MAX_CONSECUTIVE_FAILURES}`
  );

  if (consecutiveAuthFailures >= MAX_CONSECUTIVE_FAILURES) {
    console.error("[SessionHealth] Session EXPIRED — QR re-login required");
    healthCallback?.("expired");
    consecutiveAuthFailures = 0; // Reset to avoid repeated alerts
  } else if (consecutiveAuthFailures >= 2) {
    console.error("[SessionHealth] Session EXPIRING — cookies may be stale");
    healthCallback?.("expiring");
  }
}

export function stopSessionHealthMonitor(): void {
  if (sessionCheckTimer) {
    clearInterval(sessionCheckTimer);
    sessionCheckTimer = null;
  }
  consecutiveAuthFailures = 0;
}

export function getSessionHealthStatus(): {
  healthy: boolean;
  consecutiveFailures: number;
  cookieSaveActive: boolean;
  sessionMonitorActive: boolean;
} {
  return {
    healthy: consecutiveAuthFailures === 0,
    consecutiveFailures: consecutiveAuthFailures,
    cookieSaveActive: cookieSaveTimer !== null,
    sessionMonitorActive: sessionCheckTimer !== null,
  };
}
