
import { createInterface } from "node:readline";
import { LoginQRCallbackEventType } from "zca-js";
import { loginWithQR, loginWithCredentials, getApi, getCurrentUid } from "./client.js";
import { hasCredentials } from "./credentials.js";
import { dispatch } from "./actions.js";
import { IPCRequest, IPCResponse, IPCEvent } from "./ipc.js";
import {
    parseAccessControlConfig,
    checkAccess,
    stripMentionPrefix,
    isMentioned,
    AccessDecision,
    getAccessControlStatus,
    setCachedUserInfo,
    setCachedGroupInfo,
    getCachedUserInfo,
    getCachedGroupInfo,
    clearAllCaches,
    type AccessControlConfig,
} from "./access-control.js";

class ZaloWorker {
    private api: any = null;
    private acConfig: AccessControlConfig = { ...parseAccessControlConfig({}) };

    async start() {
        console.error("🚀 Zalo Worker starting...");

        try {
            if (hasCredentials()) {
                console.error("⏳ Attempting to login with saved credentials...");
                try {
                    this.api = await loginWithCredentials();
                    console.error("✅ Logged in successfully with saved credentials!");
                } catch (err: any) {
                    console.error(`⚠️ Saved credentials expired: ${err.message}`);
                    console.error("🔑 Falling back to QR login...");
                    await this.qrLogin();
                }
            } else {
                console.error("🔑 No credentials found, please scan QR code.");
                await this.qrLogin();
            }

            // Load access control config from environment or file
            this.loadAccessControlConfig();

            // Start listener
            this.api.listener.on("message", (msg: any) => {
                const normalized = this.normalizeMessage(msg);
                this.handleIncomingMessage(normalized);
            });

            this.api.listener.start();
            console.error("👂 Listening for Zalo messages...");

            // Start IPC loop
            this.listenIPC();

        } catch (err: any) {
            console.error("❌ Fatal error during startup:", err.message);
            process.exit(1);
        }
    }

    private loadAccessControlConfig() {
        const raw = process.env.ZALO_ACCESS_CONTROL;
        if (raw) {
            try {
                const parsed = JSON.parse(raw);
                this.acConfig = parseAccessControlConfig(parsed);
                console.error("🔒 Access control config loaded from ZALO_ACCESS_CONTROL env");
            } catch (err: any) {
                console.error("⚠️ Failed to parse ZALO_ACCESS_CONTROL:", err.message);
            }
        } else {
            // Read individual env vars (set in .env)
            this.acConfig.dmPolicy = (process.env.ZALO_DM_POLICY || "open") as any;
            this.acConfig.groupPolicy = (process.env.ZALO_GROUP_POLICY || "open") as any;
            this.acConfig.requireMention = process.env.ZALO_REQUIRE_MENTION === "true";

            const parseIds = (val?: string) => new Set((val || "").split(",").map(s => s.trim()).filter(Boolean));
            this.acConfig.allowlistedUsers = parseIds(process.env.ZALO_ALLOWLISTED_USERS);
            this.acConfig.denylistedUsers = parseIds(process.env.ZALO_DENYLISTED_USERS);
            this.acConfig.allowlistedGroups = parseIds(process.env.ZALO_ALLOWLISTED_GROUPS);
            this.acConfig.denylistedGroups = parseIds(process.env.ZALO_DENYLISTED_GROUPS);

            if (process.env.ZALO_BOT_NAME) this.acConfig.botName = process.env.ZALO_BOT_NAME;

            const patternsRaw = process.env.ZALO_MENTION_PATTERNS;
            if (patternsRaw) {
                try {
                    const patterns: string[] = JSON.parse(patternsRaw);
                    this.acConfig.mentionPatterns = patterns.map(p => {
                        try { return new RegExp(p, "i"); } catch { return null; }
                    }).filter(Boolean) as RegExp[];
                } catch { /* ignore */ }
            }
        }

        // Set bot identity for mention detection
        if (!this.acConfig.botUserId) {
            const uid = getCurrentUid();
            if (uid) {
                this.acConfig.botUserId = uid;
            }
        }

        // Log access control status
        const status = getAccessControlStatus(this.acConfig);
        console.error(`🔒 AC Status: DM=${status.dmPolicy}, Group=${status.groupPolicy}, Mention=${status.requireMention}`);
    }

    private async qrLogin() {
        this.api = await loginWithQR(async (event: any) => {
            if (event.type === LoginQRCallbackEventType.QRCodeGenerated) {
                this.emit("qr_code", { qr_data: event.data });
            }
        });
        console.error("✅ QR Login successful!");
    }

    private normalizeMessage(msg: any) {
        // zca-js wraps message data inside msg.data — unwrap if needed
        const inner = msg.data && typeof msg.data === 'object' ? msg.data : msg;
        const from_id = inner.uidFrom ?? inner.fromId ?? inner.senderId ?? inner.userId ?? null;
        const chat_id = msg.threadId ?? inner.threadId ?? inner.groupId ?? from_id;
        return {
            from_id: from_id !== null ? String(from_id) : null,
            from_name: inner.dName ?? inner.fromName ?? inner.senderName ?? null,
            chat_id: chat_id !== null ? String(chat_id) : null,
            text: inner.content ?? inner.message ?? inner.text ?? "",
            timestamp: inner.ts ?? Date.now(),
            is_group: !!inner.groupId,
            raw: msg
        };
    }

    private handleIncomingMessage(normalized: any) {
        const ctx = {
            fromId: normalized.from_id ?? "unknown",
            chatId: normalized.chat_id ?? "unknown",
            isGroup: normalized.is_group,
            text: normalized.text ?? "",
        };

        const result = checkAccess(ctx, this.acConfig);

        if (result.decision === AccessDecision.DENY) {
            console.error(`[AC] DENIED ${ctx.fromId} in ${ctx.isGroup ? "group" : "DM"} ${ctx.chatId}: ${result.reason}`);
            return;
        }

        if (result.decision === AccessDecision.IGNORE) {
            console.error(`[AC] IGNORED ${ctx.fromId} in group ${ctx.chatId}: ${result.reason}`);
            return;
        }

        // Strip mention prefix before sending to Hermes
        const cleanText = stripMentionPrefix(normalized.text, this.acConfig);
        if (cleanText !== normalized.text) {
            normalized.text = cleanText;
        }

        this.emit("message", normalized);
    }

    private listenIPC() {
        const rl = createInterface({
            input: process.stdin,
            terminal: false
        });

        rl.on("line", async (line) => {
            if (!line.trim()) return;
            try {
                const request: IPCRequest = JSON.parse(line);
                const result = await this.handleMethod(request.method, request.params);
                this.respond(request.id, result);
            } catch (err: any) {
                // We need to find the ID to respond to even on error
                try {
                    const partialReq = JSON.parse(line);
                    this.respondError(partialReq.id, err.message);
                } catch {
                    console.error("❌ Broken IPC message:", line);
                }
            }
        });
    }

    private async handleMethod(method: string, params: any) {
        if (method === "zalo_action") {
            return await dispatch(params);
        }

        // Access control methods
        if (method === "update_access_control") {
            this.acConfig = parseAccessControlConfig(params);
            if (!this.acConfig.botUserId) {
                const uid = getCurrentUid();
                if (uid) this.acConfig.botUserId = uid;
            }
            return getAccessControlStatus(this.acConfig);
        }

        if (method === "get_access_control_status") {
            return getAccessControlStatus(this.acConfig);
        }

        if (method === "clear_access_control_caches") {
            clearAllCaches();
            return { cleared: true };
        }

        if (method === "check_access") {
            return checkAccess(params, this.acConfig);
        }

        // Cache management
        if (method === "cache_user_info") {
            setCachedUserInfo(params.userId, params.data);
            return { cached: true };
        }

        if (method === "cache_group_info") {
            setCachedGroupInfo(params.groupId, params.data);
            return { cached: true };
        }

        if (method === "get_cached_user_info") {
            return getCachedUserInfo(params.userId);
        }

        if (method === "get_cached_group_info") {
            return getCachedGroupInfo(params.groupId);
        }
        
        // Internal methods
        switch (method) {
            case "ping":
                return "pong";
            case "get_me":
                return await this.api.getUserInfo([this.api.getOwnId()]);
            default:
                throw new Error(`Unknown method: ${method}`);
        }
    }

    private emit(type: string, payload: any) {
        const event: IPCEvent = {
            type: "event",
            data: { type, payload }
        };
        console.log(JSON.stringify(event));
    }

    private respond(id: string, result: any) {
        const response: IPCResponse = { id, result };
        console.log(JSON.stringify(response));
    }

    private respondError(id: string, error: string) {
        const response: IPCResponse = { id, error };
        console.log(JSON.stringify(response));
    }
}

const worker = new ZaloWorker();
worker.start().catch(err => {
    console.error("💀 Worker crashed:", err);
    process.exit(1);
});
