import { Zalo, LoginQRCallbackEventType } from "zca-js";
import { saveCredentials, loadCredentials, deleteCredentials, hasCredentials, } from "./credentials.js";
import sharp from "sharp";
import * as fs from "fs";
let apiInstance = null;
let currentUid = null;
/** [H2] Promise memoization to prevent concurrent login attempts */
let loginPromise = null;
async function imageMetadataGetter(filePath) {
    const data = await fs.promises.readFile(filePath);
    const metadata = await sharp(data).metadata();
    return {
        height: metadata.height || 0,
        width: metadata.width || 0,
        size: metadata.size || data.length,
    };
}
export async function loginWithQR(callback) {
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
        const info = raw?.profile ?? raw;
        currentUid = info?.userId ?? null;
    }
    catch {
        // non-critical
    }
    return api;
}
export async function loginWithCredentials() {
    const creds = loadCredentials();
    if (!creds) {
        throw new Error("No saved credentials found. Login with QR first.");
    }
    const zalo = new Zalo({ logging: false, imageMetadataGetter });
    const api = await zalo.login({
        imei: creds.imei,
        cookie: creds.cookie,
        userAgent: creds.userAgent,
        language: creds.language,
    });
    apiInstance = api;
    try {
        const raw = await api.fetchAccountInfo();
        const info = raw?.profile ?? raw;
        currentUid = info?.userId ?? null;
    }
    catch {
        // non-critical
    }
    return api;
}
/**
 * Get the API singleton safely with race condition protection.
 * [H2] Uses promise memoization — concurrent callers wait for the same login attempt.
 */
export async function getApi() {
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
export function getApiSync() {
    return apiInstance;
}
export function getCurrentUid() {
    return currentUid;
}
export function isAuthenticated() {
    return apiInstance !== null;
}
export function hasStoredCredentials() {
    return hasCredentials();
}
export async function logout() {
    apiInstance = null;
    currentUid = null;
    loginPromise = null;
    deleteCredentials();
}
export async function ensureAuthenticated() {
    return getApi();
}
