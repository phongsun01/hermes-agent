import { createInterface } from "node:readline";
import { LoginQRCallbackEventType } from "zca-js";
import { loginWithQR, loginWithCredentials } from "./client.js";
import { hasCredentials } from "./credentials.js";
import { dispatch } from "./actions.js";
class ZaloWorker {
    api = null;
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
            // Start listener
            this.api.listener.on("message", (msg) => {
                this.emit("message", this.normalizeMessage(msg));
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
