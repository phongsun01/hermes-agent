import { createInterface } from "node:readline";
import { LoginQRCallbackEventType } from "zca-js";
import { loginWithQR, loginWithCredentials, getCurrentUid } from "./client.js";
import { hasCredentials } from "./credentials.js";
import { dispatch } from "./actions.js";
import { parseAccessControlConfig, checkAccess, stripMentionPrefix, AccessDecision, getAccessControlStatus, setCachedUserInfo, setCachedGroupInfo, getCachedUserInfo, getCachedGroupInfo, clearAllCaches, } from "./access-control.js";
class ZaloWorker {
    api = null;
    acConfig = { ...parseAccessControlConfig({}) };
    async start() {
        console.error("🚀 Zalo Worker starting...");
        try {
            if (hasCredentials()) {
                console.error("⏳ Attempting to login with saved credentials...");
                this.api = await loginWithCredentials();
                console.error("✅ Logged in successfully!");
            }
            else {
                console.error("🔑 No credentials found, please scan QR code.");
                await this.qrLogin();
            }
            // Load access control config from environment or file
            this.loadAccessControlConfig();
            // Start listener
            this.api.listener.on("message", (msg) => {
                const normalized = this.normalizeMessage(msg);
                this.handleIncomingMessage(normalized);
            });
            this.api.listener.start();
            console.error("👂 Listening for Zalo messages...");
            // Start IPC loop
            this.listenIPC();
        }
        catch (err) {
            console.error("❌ Fatal error during startup:", err.message);
            process.exit(1);
        }
    }
    loadAccessControlConfig() {
        const raw = process.env.ZALO_ACCESS_CONTROL;
        if (raw) {
            try {
                const parsed = JSON.parse(raw);
                this.acConfig = parseAccessControlConfig(parsed);
                console.error("🔒 Access control config loaded from ZALO_ACCESS_CONTROL env");
            }
            catch (err) {
                console.error("⚠️ Failed to parse ZALO_ACCESS_CONTROL:", err.message);
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
    async qrLogin() {
        this.api = await loginWithQR(async (event) => {
            if (event.type === LoginQRCallbackEventType.QRCodeGenerated) {
                this.emit("qr_code", { qr_data: event.data });
            }
        });
        console.error("✅ QR Login successful!");
    }
    normalizeMessage(msg) {
        const from_id = msg.uidFrom ?? msg.fromId ?? msg.senderId ?? msg.userId ?? null;
        const chat_id = msg.threadId ?? msg.groupId ?? from_id;
        return {
            from_id: from_id !== null ? String(from_id) : null,
            from_name: msg.dName ?? msg.fromName ?? msg.senderName ?? null,
            chat_id: chat_id !== null ? String(chat_id) : null,
            text: msg.content ?? msg.message ?? msg.text ?? "",
            timestamp: msg.ts ?? Date.now(),
            is_group: !!msg.groupId,
            raw: msg
        };
    }
    handleIncomingMessage(normalized) {
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
    listenIPC() {
        const rl = createInterface({
            input: process.stdin,
            terminal: false
        });
        rl.on("line", async (line) => {
            if (!line.trim())
                return;
            try {
                const request = JSON.parse(line);
                const result = await this.handleMethod(request.method, request.params);
                this.respond(request.id, result);
            }
            catch (err) {
                // We need to find the ID to respond to even on error
                try {
                    const partialReq = JSON.parse(line);
                    this.respondError(partialReq.id, err.message);
                }
                catch {
                    console.error("❌ Broken IPC message:", line);
                }
            }
        });
    }
    async handleMethod(method, params) {
        if (method === "zalo_action") {
            return await dispatch(params);
        }
        // Access control methods
        if (method === "update_access_control") {
            this.acConfig = parseAccessControlConfig(params);
            if (!this.acConfig.botUserId) {
                const uid = getCurrentUid();
                if (uid)
                    this.acConfig.botUserId = uid;
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
    emit(type, payload) {
        const event = {
            type: "event",
            data: { type, payload }
        };
        console.log(JSON.stringify(event));
    }
    respond(id, result) {
        const response = { id, result };
        console.log(JSON.stringify(response));
    }
    respondError(id, error) {
        const response = { id, error };
        console.log(JSON.stringify(response));
    }
}
const worker = new ZaloWorker();
worker.start().catch(err => {
    console.error("💀 Worker crashed:", err);
    process.exit(1);
});
