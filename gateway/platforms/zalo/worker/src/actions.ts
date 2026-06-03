import { 
    ThreadType, 
    Reactions,
    Urgency,
    MuteAction,
    MuteDuration,
    UpdateSettingsType,
    AutoReplyScope
} from "zca-js";
import { getApi, getCurrentUid } from "./client.js";
import * as nodeFs from "node:fs";
import * as nodePath from "node:path";
import * as nodeOs from "node:os";
import * as nodeCrypto from "node:crypto";
import {
    getCachedUserInfo,
    setCachedUserInfo,
    getCachedGroupInfo,
    setCachedGroupInfo,
} from "./access-control.js";
import {
    resolveMediaSource,
    prepareMessage,
    downloadAndCacheMedia,
    isMediaCached,
    getCachedMediaPath,
    detectReceivedMedia,
} from "./media.js";

// â”€â”€â”€ Result helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function ok(data: any) {
    return { success: true, data };
}

// â”€â”€â”€ Nameâ†’ID resolvers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function resolveUserId(nameOrId: string): Promise<string> {
    if (/^\d+$/.test(nameOrId)) return nameOrId;
    const api = await getApi();
    const friends = await api.getAllFriends();
    const list = Array.isArray(friends) ? friends : [];
    const q = nameOrId.toLowerCase();
    const hit = list.find(
        (f: any) =>
            (f.displayName ?? "").toLowerCase() === q ||
            (f.zaloName ?? "").toLowerCase() === q,
    );
    if (hit) return String(hit.userId);
    throw new Error(`User not found: "${nameOrId}"`);
}

export async function resolveGroupId(nameOrId: string): Promise<string> {
    if (/^\d+$/.test(nameOrId)) return nameOrId;
    const api = await getApi();
    const resp = await api.getAllGroups();
    const ids = Object.keys(resp?.gridVerMap ?? {});
    if (ids.length === 0) throw new Error("No groups found");
    const info = await api.getGroupInfo(ids);
    const map = info?.gridInfoMap ?? {};
    const q = nameOrId.toLowerCase();
    const hit = Object.entries(map).find(
        ([, g]: [string, any]) => (g.name ?? "").toLowerCase() === q,
    );
    if (hit) return hit[0];
    throw new Error(`Group not found: "${nameOrId}"`);
}

export function extractMemberIds(groupInfo: any): string[] {
    const ids: string[] = groupInfo?.memberIds ?? [];
    if (ids.length > 0) return ids;
    const verList: string[] = groupInfo?.memVerList ?? [];
    return verList.map((e: string) => e.split("_")[0]).filter(Boolean);
}

// â”€â”€â”€ Reaction icon resolver â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const REACTION_MAP: Record<string, Reactions> = {
    heart: Reactions.HEART, love: Reactions.HEART,
    like: Reactions.LIKE, thumbsup: Reactions.LIKE,
    haha: Reactions.HAHA, laugh: Reactions.HAHA,
    wow: Reactions.WOW, surprised: Reactions.WOW,
    cry: Reactions.CRY, sad: Reactions.CRY,
    angry: Reactions.ANGRY,
    none: Reactions.NONE,
    "ðŸ‘": Reactions.LIKE, "â¤ï¸": Reactions.HEART, "ðŸ˜†": Reactions.HAHA,
    "ðŸ˜®": Reactions.WOW, "ðŸ˜¢": Reactions.CRY, "ðŸ˜ ": Reactions.ANGRY,
};

function resolveReaction(raw: string): Reactions {
    return REACTION_MAP[raw.toLowerCase()] ?? (raw as Reactions);
}

// â”€â”€â”€ Markdown â†’ Zalo styles (from zaloclaw send.ts) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function markdownToZaloStyles(text: string): { text: string; styles: any[] } {
    const styles: any[] = [];
    let result = "";
    let pos = 0;

    const allMatches: Array<{ index: number; fullLen: number; contentLen: number; markerLen: number; st: string }> = [];

    const patterns = [
        { re: /\*\*(.+?)\*\*/g, st: "b", markerLen: 2 },
        { re: /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, st: "i", markerLen: 1 },
        { re: /__(.+?)__/g, st: "u", markerLen: 2 },
        { re: /~~(.+?)~~/g, st: "s", markerLen: 2 },
    ];

    for (const pat of patterns) {
        let m: RegExpExecArray | null;
        pat.re.lastIndex = 0;
        while ((m = pat.re.exec(text)) !== null) {
            allMatches.push({
                index: m.index,
                fullLen: m[0].length,
                contentLen: m[1].length,
                markerLen: pat.markerLen,
                st: pat.st,
            });
        }
    }

    allMatches.sort((a, b) => a.index - b.index);

    const filtered: typeof allMatches = [];
    let lastEnd = 0;
    for (const match of allMatches) {
        if (match.index >= lastEnd) {
            filtered.push(match);
            lastEnd = match.index + match.fullLen;
        }
    }

    for (const match of filtered) {
        result += text.slice(pos, match.index);
        const contentStart = result.length;
        const content = text.slice(match.index + match.markerLen, match.index + match.fullLen - match.markerLen);
        result += content;
        styles.push({ start: contentStart, len: content.length, st: match.st });
        pos = match.index + match.fullLen;
    }

    result += text.slice(pos);

    return { text: result, styles };
}

// â”€â”€â”€ Safe fetch helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function safeFetch(url: string, maxSizeBytes: number = 50 * 1024 * 1024): Promise<{ buffer: Buffer }> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Failed to fetch ${url}: ${response.status}`);
    const buffer = Buffer.from(await response.arrayBuffer());
    if (buffer.length > maxSizeBytes) throw new Error(`File too large: ${buffer.length} > ${maxSizeBytes}`);
    return { buffer };
}

// â”€â”€â”€ Dispatch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export async function dispatch(p: any): Promise<any> {
    const api = await getApi();

    switch (p.action) {
        // â”€â”€ 1. send â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send": {
            if (!p.threadId || !p.message) throw new Error("threadId and message required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            let msg = p.message;
            let styles: any[] | undefined;
            const converted = markdownToZaloStyles(msg);
            msg = converted.text;
            styles = converted.styles;
            const content: any = { msg };
            if (styles && styles.length > 0) content.styles = styles;
            if (p.urgency !== undefined) content.urgency = p.urgency as Urgency;
            if (p.messageTtl !== undefined) content.ttl = p.messageTtl;
            const res = await api.sendMessage(content, p.threadId, type);
            return ok({ msgId: res?.message?.msgId, stylesApplied: styles?.length ?? 0 });
        }

        // â”€â”€ 2. send-styled â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-styled": {
            if (!p.threadId || !p.message) throw new Error("threadId and message required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            let msg = p.message;
            let styles = p.styles;
            if (!styles || styles.length === 0) {
                const converted = markdownToZaloStyles(msg);
                msg = converted.text;
                styles = converted.styles;
            }
            const content: any = { msg };
            if (styles && styles.length > 0) content.styles = styles;
            if (p.urgency !== undefined) content.urgency = p.urgency as Urgency;
            if (p.messageTtl !== undefined) content.ttl = p.messageTtl;
            const res = await api.sendMessage(content, p.threadId, type);
            return ok({ msgId: res?.message?.msgId, stylesApplied: styles?.length ?? 0 });
        }

        // â”€â”€ 3. send-link â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-link": {
            if (!p.threadId || !p.url) throw new Error("threadId and url required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.sendLink({ link: p.url }, p.threadId, type);
            return ok({ msgId: res?.msgId });
        }

        // â”€â”€ 4. send-image â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-image": {
            if (!p.threadId) throw new Error("threadId required");
            const source = p.url || p.filePath || p.localPath;
            if (!source) throw new Error("url, filePath, or localPath required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;

            const { path: resolvedPath, cleanup } = await resolveMediaSource(source, "zalo-img");

            try {
                const caption = p.message ? prepareMessage(p.message).text : "";
                const res = await api.sendMessage(
                    { msg: caption, attachments: [resolvedPath] },
                    p.threadId, type
                );
                return ok({ msgId: res?.message?.msgId });
            } finally {
                cleanup();
            }
        }

        // â”€â”€ 5. send-file â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-file": {
            if (!p.threadId) throw new Error("threadId required");
            const source = p.filePath || p.url || p.localPath;
            if (!source) throw new Error("filePath, url, or localPath required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;

            const { path: resolvedPath, cleanup } = await resolveMediaSource(source, "zalo-file");

            try {
                const caption = p.message ? prepareMessage(p.message).text : "";
                const res = await api.sendMessage(
                    { msg: caption, attachments: [resolvedPath] },
                    p.threadId, type
                );
                return ok({ msgId: res?.message?.msgId, fileName: nodePath.basename(resolvedPath), attachment: res?.attachment });
            } finally {
                cleanup();
            }
        }

        // â”€â”€ 6. send-video â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-video": {
            if (!p.threadId || !p.url) throw new Error("threadId and url required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.sendVideo(
                { videoUrl: p.url, thumbnailUrl: p.thumbnailUrl ?? p.url },
                p.threadId, type
            );
            return ok({ result: res });
        }

        // â”€â”€ 7. send-voice â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-voice": {
            if (!p.threadId) throw new Error("threadId required");
            const voiceUrl = p.voiceUrl || p.url;
            if (!voiceUrl) throw new Error("voiceUrl or url required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.sendVoice({ voiceUrl }, p.threadId, type);
            return ok({ result: res });
        }

        // â”€â”€ 8. send-sticker â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-sticker": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            if (p.stickerId && p.stickerCateId) {
                const detail = { id: p.stickerId, cateId: p.stickerCateId, type: 3 };
                await api.sendSticker(detail as any, p.threadId, type);
                return ok({ stickerId: p.stickerId });
            }
            if (p.keyword) {
                const ids = await api.getStickers(p.keyword);
                if (!ids || ids.length === 0) return ok({ error: true, message: "No stickers found" });
                const details = await api.getStickersDetail(ids[0]);
                if (!details || details.length === 0) return ok({ error: true, message: "Sticker detail unavailable" });
                await api.sendSticker(details[0], p.threadId, type);
                return ok({ sticker: details[0] });
            }
            throw new Error("stickerId+stickerCateId or keyword required");
        }

        // â”€â”€ 9. send-card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-card": {
            if (!p.threadId || !p.userId) throw new Error("threadId and userId required");
            const uid = await resolveUserId(p.userId);
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.sendCard({ userId: uid }, p.threadId, type);
            return ok({ result: res });
        }

        // â”€â”€ 10. send-bank-card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-bank-card": {
            if (!p.threadId || !p.binBank || !p.numAccBank || !p.nameAccBank)
                throw new Error("threadId, binBank, numAccBank, nameAccBank required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.sendBankCard(
                { binBank: p.binBank, numAccBank: p.numAccBank, nameAccBank: p.nameAccBank },
                p.threadId, type
            );
            return ok({ result: res });
        }

        // â”€â”€ 11. send-typing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-typing": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            await api.sendTypingEvent(p.threadId, type);
            return ok({ message: "Typing indicator sent" });
        }

        // â”€â”€ 12. send-to-stranger â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "send-to-stranger": {
            if (!p.userId || !p.message) throw new Error("userId and message required");
            const res = await api.sendMessage({ msg: p.message }, p.userId, ThreadType.User);
            return ok({
                msgId: res?.message?.msgId,
                note: "May not be received if stranger doesn't accept messages",
            });
        }

        // â”€â”€ 13. forward-message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "forward-message": {
            if (!p.msgId || !p.threadIds?.length) throw new Error("msgId and threadIds required");
            const payload: any = { message: p.message || "" };
            if (p.messageTtl !== undefined) payload.ttl = p.messageTtl;
            const res = await api.forwardMessage(payload, p.threadIds);
            return ok({ success: res?.success, failed: res?.fail });
        }

        // â”€â”€ 14. delete-message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "delete-message": {
            if (!p.msgId || !p.threadId) throw new Error("msgId and threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const cliMsgId = p.cliMsgId || p.msgId;
            const uidFrom = getCurrentUid() ?? "";
            const res = await api.deleteMessage(
                { data: { msgId: p.msgId, cliMsgId, uidFrom }, threadId: p.threadId, type },
                Boolean(p.onlyMe),
            );
            return ok({ result: res });
        }

        // â”€â”€ 15. undo-message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "undo-message": {
            if (!p.msgId) throw new Error("msgId required");
            const undoCliMsgId = p.cliMsgId || p.msgId;
            const res = await (api as any).undo({ msgId: p.msgId, cliMsgId: undoCliMsgId });
            return ok({ result: res });
        }

        // â”€â”€ 16. add-reaction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "add-reaction": {
            if (!p.msgId || !p.icon || !p.threadId)
                throw new Error("msgId, icon and threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.addReaction(resolveReaction(p.icon), {
                data: { msgId: p.msgId, cliMsgId: p.cliMsgId || p.msgId },
                threadId: p.threadId,
                type,
            });
            return ok(res);
        }

        // â”€â”€ Friends â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "friends": {
            const raw = await api.getAllFriends();
            let list = Array.isArray(raw) ? raw : [];
            if (p.query?.trim()) {
                const q = p.query.trim().toLowerCase();
                list = list.filter((f: any) =>
                    (f.displayName ?? "").toLowerCase().includes(q) ||
                    (f.zaloName ?? "").toLowerCase().includes(q) ||
                    String(f.userId).includes(q),
                );
            }
            const friends = list.map((f: any) => ({
                userId: f.userId,
                displayName: f.displayName,
                zaloName: f.zaloName,
                avatar: f.avatar,
                phoneNumber: f.phoneNumber,
            }));
            return ok({ friends, count: friends.length });
        }

        case "find-user": {
            if (!p.phoneNumber) throw new Error("phoneNumber required");
            const clean = p.phoneNumber.replace(/[\s-]/g, "");
            const res = await api.findUser(clean);
            if (!res?.uid) return ok({ found: false, phoneNumber: clean });
            return ok({
                found: true,
                user: {
                    userId: res.uid,
                    displayName: res.display_name || res.zalo_name,
                    zaloName: res.zalo_name,
                    avatar: res.avatar,
                    cover: res.cover,
                    gender: res.gender,
                    dob: res.dob,
                    status: res.status,
                    globalId: res.globalId,
                },
            });
        }

        case "find-user-by-username": {
            if (!p.username) throw new Error("username required");
            const res = await api.findUserByUsername(p.username);
            return ok({ result: res });
        }

        case "send-friend-request": {
            if (!p.userId) throw new Error("userId required");
            const uid = await resolveUserId(p.userId);
            const msg = p.requestMessage || "Xin chÃ o!";
            await api.sendFriendRequest(msg, uid);
            return ok({ success: true, userId: uid });
        }

        case "get-friend-requests": {
            return ok({ message: "Friend requests feature requires friend-request-store" });
        }

        case "accept-friend-request": {
            if (!p.userId) throw new Error("userId required");
            await api.acceptFriendRequest(p.userId);
            return ok({ success: true, userId: p.userId });
        }

        case "reject-friend-request": {
            if (!p.userId) throw new Error("userId required");
            await api.rejectFriendRequest(p.userId);
            return ok({ success: true, userId: p.userId });
        }

        case "get-sent-requests": {
            const res = await api.getSentFriendRequest();
            const list = Object.entries(res).map(([uid, info]: [string, any]) => ({
                userId: info.userId || uid,
                displayName: info.displayName,
                sentAt: info.fReqInfo?.time,
            }));
            return ok({ requests: list, count: list.length });
        }

        case "undo-friend-request": {
            if (!p.userId) throw new Error("userId required");
            const uid = await resolveUserId(p.userId);
            await api.undoFriendRequest(uid);
            return ok({ success: true, userId: uid });
        }

        case "unfriend": {
            if (!p.userId) throw new Error("userId required");
            const uid = await resolveUserId(p.userId);
            await api.removeFriend(uid);
            return ok({ success: true, userId: uid });
        }

        case "check-friend-status": {
            if (!p.userId) throw new Error("userId required");
            const st = await api.getFriendRequestStatus(p.userId);
            return ok({
                userId: p.userId,
                isFriend: st.is_friend === 1,
                isRequested: st.is_requested === 1,
                isRequesting: st.is_requesting === 1,
            });
        }

        case "set-friend-nickname": {
            if (!p.userId || !p.nickname) throw new Error("userId and nickname required");
            const uid = await resolveUserId(p.userId);
            await api.changeFriendAlias(uid, p.nickname);
            return ok({ success: true, userId: uid, nickname: p.nickname });
        }

        case "remove-friend-nickname": {
            if (!p.userId) throw new Error("userId required");
            const uid = await resolveUserId(p.userId);
            await api.removeFriendAlias(uid);
            return ok({ success: true, userId: uid });
        }

        case "get-online-friends": {
            const res = await api.getFriendOnlines();
            return ok({ onlineFriends: res });
        }

        case "get-close-friends": {
            const res = await api.getCloseFriends();
            return ok({ closeFriends: res });
        }

        case "get-friend-recommendations": {
            const res = await api.getFriendRecommendations();
            return ok({ recommendations: res });
        }

        case "get-alias-list": {
            const res = await api.getAliasList();
            return ok({ aliases: res });
        }

        case "get-related-friend-groups": {
            if (!p.userId) throw new Error("userId required");
            const uid = await resolveUserId(p.userId);
            const res = await api.getRelatedFriendGroup(uid);
            return ok({ groups: res });
        }

        case "get-multi-users-by-phones": {
            if (!p.phoneNumbers?.length) throw new Error("phoneNumbers required");
            const res = await api.getMultiUsersByPhones(p.phoneNumbers);
            return ok({ users: res });
        }

        // â”€â”€ Groups â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "groups": {
            const resp = await api.getAllGroups();
            const ids = Object.keys(resp?.gridVerMap ?? {});
            if (ids.length === 0) return ok({ groups: [], count: 0 });
            try {
                const info = await api.getGroupInfo(ids);
                const map = info?.gridInfoMap ?? {};
                let groups = Object.entries(map).map(([id, g]: [string, any]) => ({
                    groupId: id, name: g.name, desc: g.desc,
                    totalMember: g.totalMember, creatorId: g.creatorId,
                }));
                if (p.query?.trim()) {
                    const q = p.query.trim().toLowerCase();
                    groups = groups.filter(g => (g.name ?? "").toLowerCase().includes(q));
                }
                return ok({ groups, count: groups.length });
            } catch {
                return ok({ groups: ids.map(id => ({ groupId: id })), count: ids.length });
            }
        }

        case "get-group-info": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const info = await api.getGroupInfo([gid]);
            const g = info?.gridInfoMap?.[gid];
            return ok({
                groupId: gid,
                name: g?.name,
                desc: (g as any)?.desc,
                totalMember: (g as any)?.totalMember,
                memberIds: extractMemberIds(g),
                creatorId: (g as any)?.creatorId,
                adminIds: (g as any)?.adminIds,
            });
        }

        case "create-group": {
            if (!p.groupName || !p.memberIds?.length) throw new Error("groupName and memberIds required");
            const ids = await Promise.all(p.memberIds.map(resolveUserId));
            const res = await api.createGroup({ name: p.groupName, members: ids });
            return ok({ success: true, result: res });
        }

        case "add-to-group": {
            if (!p.groupId || !p.memberIds?.length) throw new Error("groupId and memberIds required");
            const gid = await resolveGroupId(p.groupId);
            const ids = await Promise.all(p.memberIds.map(resolveUserId));
            const res = await api.addUserToGroup(ids, gid);
            return ok({ success: true, result: res });
        }

        case "remove-from-group": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.removeUserFromGroup(uid, gid);
            return ok({ success: true, result: res });
        }

        case "leave-group": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.leaveGroup(gid);
            return ok({ success: true, result: res });
        }

        case "rename-group": {
            if (!p.groupId || !p.groupName) throw new Error("groupId and groupName required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.changeGroupName(gid, p.groupName);
            return ok({ success: true, result: res });
        }

        case "add-group-admin": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.addGroupDeputy(gid, uid);
            return ok({ success: true, result: res });
        }

        case "remove-group-admin": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.removeGroupDeputy(gid, uid);
            return ok({ success: true, result: res });
        }

        case "change-group-owner": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.changeGroupOwner(gid, uid);
            return ok({ success: true, result: res });
        }

        case "disperse-group": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.disperseGroup(gid);
            return ok({ success: true, result: res });
        }

        case "update-group-settings": {
            if (!p.groupId || !p.groupSettings) throw new Error("groupId and groupSettings required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.updateGroupSettings(p.groupSettings, gid);
            return ok({ success: true, result: res });
        }

        case "enable-group-link": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.enableGroupLink(gid);
            return ok({ success: true, result: res });
        }

        case "disable-group-link": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.disableGroupLink(gid);
            return ok({ success: true, result: res });
        }

        case "get-group-link": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.getGroupLinkDetail(gid);
            return ok({ result: res });
        }

        case "get-pending-members": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.getPendingGroupMembers(gid);
            return ok({ result: res });
        }

        case "review-pending-members": {
            if (!p.groupId || !p.memberIds?.length || p.isApprove === undefined)
                throw new Error("groupId, memberIds, and isApprove required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.reviewPendingMemberRequest({ members: p.memberIds, isApprove: p.isApprove }, gid);
            return ok({ success: true, result: res });
        }

        case "get-group-blocked": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.getGroupBlockedMember({}, gid);
            return ok({ result: res });
        }

        case "block-group-member": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.addGroupBlockedMember(uid, gid);
            return ok({ success: true, result: res });
        }

        case "unblock-group-member": {
            if (!p.groupId || !p.userId) throw new Error("groupId and userId required");
            const gid = await resolveGroupId(p.groupId);
            const uid = await resolveUserId(p.userId);
            const res = await api.removeGroupBlockedMember(uid, gid);
            return ok({ success: true, result: res });
        }

        case "get-group-members-info": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const groupInfoResp = await api.getGroupInfo([gid]);
            const groupInfo = groupInfoResp?.gridInfoMap?.[gid];
            const memberIds = extractMemberIds(groupInfo);
            const profiles: Record<string, any> = {};
            const unchangedsProfile: string[] = [];
            const batchSize = 40;
            for (let i = 0; i < memberIds.length; i += batchSize) {
                const batch = memberIds.slice(i, i + batchSize);
                const res = await api.getGroupMembersInfo(batch);
                Object.assign(profiles, res?.profiles ?? {});
                unchangedsProfile.push(...((res?.unchangeds_profile ?? []) as string[]));
            }
            return ok({
                groupId: gid,
                totalMemberIds: memberIds.length,
                result: { profiles, unchangeds_profile: unchangedsProfile },
            });
        }

        case "join-group-link": {
            if (!p.link) throw new Error("link required");
            let info = null;
            try { info = await api.getGroupLinkInfo(p.link); } catch {}
            const res = await api.joinGroupLink(p.link);
            return ok({ success: true, groupInfo: info, result: res });
        }

        case "invite-to-groups": {
            if (!p.userId || !p.groupIds?.length) throw new Error("userId and groupIds required");
            const uid = await resolveUserId(p.userId);
            const res = await api.inviteUserToGroups(uid, p.groupIds);
            return ok({ success: true, result: res });
        }

        case "get-group-invites": {
            const res = await api.getGroupInviteBoxList();
            return ok({ invites: res });
        }

        case "join-group-invite": {
            if (!p.groupId) throw new Error("groupId required");
            const res = await api.joinGroupInviteBox(p.groupId);
            return ok({ success: true, result: res });
        }

        case "delete-group-invite": {
            if (!p.groupId) throw new Error("groupId required");
            const res = await api.deleteGroupInviteBox(p.groupId);
            return ok({ success: true, result: res });
        }

        case "change-group-avatar": {
            if (!p.groupId || !p.url) throw new Error("groupId and url required");
            const gid = await resolveGroupId(p.groupId);
            if (/^https?:\/\//i.test(p.url)) {
                const { buffer } = await safeFetch(p.url, 5 * 1024 * 1024);
                await api.changeGroupAvatar({ data: buffer, filename: "avatar.jpg", metadata: { totalSize: buffer.length, width: 400, height: 400 } } as any, gid);
            } else {
                await api.changeGroupAvatar(p.url, gid);
            }
            return ok({ success: true, groupId: gid });
        }

        case "upgrade-group-to-community": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            await api.upgradeGroupToCommunity(gid);
            return ok({ success: true, groupId: gid });
        }

        case "get-group-chat-history": {
            if (!p.groupId) throw new Error("groupId required");
            const gid = await resolveGroupId(p.groupId);
            const res = await api.getGroupChatHistory(gid, p.count ?? 20);
            return ok({ history: res });
        }

        // â”€â”€ Polls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "create-poll": {
            if (!p.threadId || !p.title || !p.options?.length) throw new Error("threadId, title, options required");
            const pollOpts: any = { question: p.title, options: p.options };
            if (p.expiredTime !== undefined) pollOpts.expiredTime = p.expiredTime;
            if (p.allowMultiChoices !== undefined) pollOpts.allowMultiChoices = p.allowMultiChoices;
            if (p.allowAddNewOption !== undefined) pollOpts.allowAddNewOption = p.allowAddNewOption;
            if (p.hideVotePreview !== undefined) pollOpts.hideVotePreview = p.hideVotePreview;
            if (p.isAnonymous !== undefined) pollOpts.isAnonymous = p.isAnonymous;
            const res = await api.createPoll(pollOpts, p.threadId);
            return ok({ success: true, poll: res });
        }

        case "vote-poll": {
            if (!p.pollId || !p.threadId || p.optionId === undefined) throw new Error("pollId, threadId, optionId required");
            const res = await api.votePoll(p.pollId, p.optionId);
            return ok({ success: true, result: res });
        }

        case "lock-poll": {
            if (!p.pollId || !p.threadId) throw new Error("pollId and threadId required");
            const res = await api.lockPoll(p.pollId);
            return ok({ success: true, result: res });
        }

        case "get-poll-detail": {
            if (!p.pollId || !p.threadId) throw new Error("pollId and threadId required");
            const res = await api.getPollDetail(String(p.pollId) as any);
            return ok({ poll: res });
        }

        case "add-poll-options": {
            if (!p.pollId || !p.threadId || !p.options?.length) throw new Error("pollId, threadId, options required");
            const res = await api.addPollOptions({ pollId: p.pollId, options: p.options.map((o: string) => ({ content: o, voted: false })), votedOptionIds: [] });
            return ok({ success: true, result: res });
        }

        case "share-poll": {
            if (!p.pollId || !p.threadId || !p.threadIds?.length) throw new Error("pollId, threadId, threadIds required");
            const res = await api.sharePoll(p.pollId);
            return ok({ success: true, result: res });
        }

        // â”€â”€ Reminders â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "create-reminder": {
            if (!p.threadId || !p.title || !p.startTime) throw new Error("threadId, title, startTime required");
            const reminder: any = { title: p.title, startTime: p.startTime };
            if (p.emoji) reminder.emoji = p.emoji;
            if (p.endTime) reminder.endTime = p.endTime;
            if (p.repeat !== undefined) reminder.repeat = p.repeat;
            const res = await api.createReminder(reminder, p.threadId);
            return ok({ success: true, reminder: res });
        }

        case "edit-reminder": {
            if (!p.reminderId || !p.threadId) throw new Error("reminderId and threadId required");
            const reminder: any = {};
            if (p.title) reminder.title = p.title;
            if (p.startTime) reminder.startTime = p.startTime;
            if (p.endTime) reminder.endTime = p.endTime;
            if (p.emoji) reminder.emoji = p.emoji;
            if (p.repeat !== undefined) reminder.repeat = p.repeat;
            const res = await api.editReminder(p.reminderId, reminder, p.threadId);
            return ok({ success: true, result: res });
        }

        case "remove-reminder": {
            if (!p.reminderId || !p.threadId) throw new Error("reminderId and threadId required");
            const res = await api.removeReminder(p.reminderId, p.threadId);
            return ok({ success: true, result: res });
        }

        case "list-reminders": {
            if (!p.threadId) throw new Error("threadId required");
            const res = await api.getListReminder({}, p.threadId, p.isGroup ? ThreadType.Group : ThreadType.User);
            return ok({ reminders: res });
        }

        case "get-reminder": {
            if (!p.reminderId || !p.threadId) throw new Error("reminderId and threadId required");
            const res = await api.getReminder(p.reminderId);
            return ok({ reminder: res });
        }

        case "get-reminder-responses": {
            if (!p.reminderId || !p.threadId) throw new Error("reminderId and threadId required");
            const res = await api.getReminderResponses(p.reminderId);
            return ok({ responses: res });
        }

        // â”€â”€ Conversation management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "mute-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const duration = p.duration !== undefined ? p.duration : MuteDuration.ONE_HOUR;
            const res = await api.setMute({ action: MuteAction.MUTE, duration }, p.threadId, type);
            return ok({ result: res });
        }

        case "unmute-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.setMute({ action: MuteAction.UNMUTE }, p.threadId, type);
            return ok({ result: res });
        }

        case "pin-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.setPinnedConversations(true, p.threadId, type);
            return ok({ result: res });
        }

        case "unpin-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.setPinnedConversations(false, p.threadId, type);
            return ok({ result: res });
        }

        case "delete-chat": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.deleteChat({ ownerId: api.getOwnId(), cliMsgId: "", globalMsgId: "" }, p.threadId, type);
            return ok({ result: res });
        }

        case "hide-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.setHiddenConversations(true, p.threadId, type);
            return ok({ result: res });
        }

        case "unhide-conversation": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.setHiddenConversations(true, p.threadId, type);
            return ok({ result: res });
        }

        case "get-hidden-conversations": {
            const res = await api.getHiddenConversations();
            return ok({ result: res });
        }

        case "mark-unread": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.addUnreadMark(p.threadId, type);
            return ok({ result: res });
        }

        case "unmark-unread": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.removeUnreadMark(p.threadId, type);
            return ok({ result: res });
        }

        case "get-unread-marks": {
            const res = await api.getUnreadMark();
            return ok({ result: res });
        }

        case "set-auto-delete-chat": {
            if (!p.threadId || p.ttl === undefined) throw new Error("threadId and ttl required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.updateAutoDeleteChat(p.ttl, p.threadId, type);
            return ok({ result: res });
        }

        case "get-auto-delete-chats": {
            const res = await api.getAutoDeleteChat();
            return ok({ result: res });
        }

        case "get-archived-chats": {
            const res = await api.getArchivedChatList();
            return ok({ result: res });
        }

        case "update-archived-chat": {
            if (!p.threadId || p.isArchived === undefined) throw new Error("threadId and isArchived required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.updateArchivedChatList(p.isArchived, { id: p.threadId, type: p.isGroup ? ThreadType.Group : ThreadType.User });
            return ok({ result: res });
        }

        case "get-mute-status": {
            if (!p.threadId) throw new Error("threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const res = await api.getMute();
            return ok({ result: res });
        }

        case "get-pinned-conversations": {
            const res = await api.getPinConversations();
            return ok({ result: res });
        }

        // â”€â”€ Quick messages & auto-reply â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "list-quick-messages": {
            const res = await api.getQuickMessageList();
            return ok({ quickMessages: res });
        }

        case "add-quick-message": {
            if (!p.title || !p.content) throw new Error("title and content required");
            const res = await api.addQuickMessage({ title: p.title, keyword: p.keyword || p.title });
            return ok({ result: res });
        }

        case "remove-quick-message": {
            if (!p.itemId) throw new Error("itemId required");
            const res = await api.removeQuickMessage(p.itemId);
            return ok({ result: res });
        }

        case "update-quick-message": {
            if (!p.itemId) throw new Error("itemId required");
            const item: any = {};
            if (p.title) item.title = p.title;
            if (p.content) item.content = p.content;
            if (p.keyword) item.keyword = p.keyword;
            const res = await api.updateQuickMessage(item, p.itemId);
            return ok({ result: res });
        }

        case "list-auto-replies": {
            const res = await api.getAutoReplyList();
            return ok({ autoReplies: res });
        }

        case "create-auto-reply": {
            if (!p.title || !p.content) throw new Error("title and content required");
            const rule: any = {
                title: p.title,
                content: p.content,
                scope: p.scope ?? AutoReplyScope.Everyone,
            };
            if (p.isEnable !== undefined) rule.isEnable = p.isEnable;
            const res = await api.createAutoReply(rule);
            return ok({ result: res });
        }

        case "update-auto-reply": {
            if (!p.replyId) throw new Error("replyId required");
            const rule: any = {};
            if (p.title) rule.title = p.title;
            if (p.content) rule.content = p.content;
            if (p.scope !== undefined) rule.scope = p.scope;
            if (p.isEnable !== undefined) rule.isEnable = p.isEnable;
            const res = await api.updateAutoReply(rule);
            return ok({ result: res });
        }

        case "delete-auto-reply": {
            if (!p.replyId) throw new Error("replyId required");
            const res = await api.deleteAutoReply(p.replyId);
            return ok({ result: res });
        }

        // â”€â”€ Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "get-settings": {
            const res = await api.getSettings();
            return ok({ settings: res });
        }

        case "update-setting": {
            if (!p.settingKey || p.settingValue === undefined) throw new Error("settingKey and settingValue required");
            const res = await api.updateSettings(p.settingKey, p.settingValue);
            return ok({ result: res });
        }

        case "update-active-status": {
            if (p.active === undefined) throw new Error("active required");
            const res = await api.updateActiveStatus(p.active);
            return ok({ result: res });
        }

        // â”€â”€ Profile & account â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "me": {
            const me = await api.getUserInfo([api.getOwnId()]);
            return ok(me);
        }

        case "status": {
            return ok({ authenticated: true, uid: getCurrentUid() });
        }

        case "get-user-info": {
            const userId = p.userId || p.threadId;
            if (!userId) throw new Error("userId required");
            const cached = getCachedUserInfo(userId);
            if (cached) return ok({ ...cached, cached: true });
            const info: any = await api.getUserInfo([userId]);
            if (info && info[userId]) {
                setCachedUserInfo(userId, info[userId]);
            }
            return ok(info?.[userId]);
        }

        case "last-online": {
            if (!p.userId) throw new Error("userId required");
            const res = await api.lastOnline(p.userId);
            return ok({ result: res });
        }

        case "get-qr": {
            const res = await api.getQR(api.getOwnId());
            return ok({ qr: res });
        }

        case "update-profile": {
            const profile: any = {};
            if (p.name) profile.name = p.name;
            if (p.dob) profile.dob = p.dob;
            if (p.gender !== undefined) profile.gender = p.gender;
            const res = await api.updateProfile(profile);
            return ok({ result: res });
        }

        case "update-profile-bio": {
            if (!p.bio) throw new Error("bio required");
            const res = await api.updateProfileBio(p.bio);
            return ok({ result: res });
        }

        case "change-avatar": {
            if (!p.url) throw new Error("url required");
            if (/^https?:\/\//i.test(p.url)) {
                const { buffer } = await safeFetch(p.url, 5 * 1024 * 1024);
                await api.changeAccountAvatar({ data: buffer, filename: "avatar.jpg", metadata: { totalSize: buffer.length, width: 400, height: 400 } } as any);
            } else {
                await api.changeAccountAvatar(p.url);
            }
            return ok({ success: true });
        }

        case "delete-avatar": {
            const res = await api.deleteAvatar("");
            return ok({ result: res });
        }

        case "get-avatar-list": {
            const res = await api.getAvatarList();
            return ok({ avatars: res });
        }

        case "reuse-avatar": {
            if (!p.photoId) throw new Error("photoId required");
            const res = await api.reuseAvatar(p.photoId);
            return ok({ result: res });
        }

        case "get-biz-account": {
            const res = await api.getBizAccount(api.getOwnId());
            return ok({ result: res });
        }

        case "get-full-avatar": {
            if (!p.userId) throw new Error("userId required");
            const res = await api.getFullAvatar(p.userId);
            return ok({ result: res });
        }

        case "get-friend-board": {
            const res = await api.getFriendBoardList(api.getOwnId());
            return ok({ result: res });
        }

        // â”€â”€ Stickers & misc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "search-stickers": {
            if (!p.keyword) throw new Error("keyword required");
            const ids = await api.getStickers(p.keyword);
            return ok({ stickerIds: ids, count: ids?.length ?? 0 });
        }

        case "search-sticker-detail": {
            if (!p.stickerId) throw new Error("stickerId required");
            const details = await api.getStickersDetail(p.stickerId);
            return ok({ details });
        }

        case "parse-link": {
            if (!p.url) throw new Error("url required");
            const res = await api.parseLink(p.url);
            return ok({ result: res });
        }

        case "send-report": {
            if (!p.userId || !p.reason === undefined) throw new Error("userId and reason required");
            const res = await api.sendReport(p.userId, p.reason ?? 0);
            return ok({ result: res });
        }

        // â”€â”€ Notes & labels â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "create-note": {
            if (!p.threadId || !p.title) throw new Error("threadId and title required");
            const note: any = { title: p.title };
            if (p.description) note.description = p.description;
            if (p.pinAct !== undefined) note.pinAct = p.pinAct;
            const res = await api.createNote(note, p.threadId);
            return ok({ result: res });
        }

        case "edit-note": {
            if (!p.topicId) throw new Error("topicId required");
            const note: any = {};
            if (p.title) note.title = p.title;
            if (p.description) note.description = p.description;
            if (p.pinAct !== undefined) note.pinAct = p.pinAct;
            const res = await api.editNote(p.topicId, note);
            return ok({ result: res });
        }

        case "get-boards": {
            const res = await api.getListBoard({}, "");
            return ok({ boards: res });
        }

        case "get-labels": {
            const res = await api.getLabels();
            return ok({ labels: res });
        }

        // â”€â”€ Catalogs & products â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "create-catalog": {
            if (!p.name) throw new Error("name required");
            const catalog: any = { name: p.name };
            if (p.description) catalog.description = p.description;
            const res = await api.createCatalog(catalog);
            return ok({ result: res });
        }

        case "update-catalog": {
            if (!p.catalogId) throw new Error("catalogId required");
            const catalog: any = {};
            if (p.name) catalog.name = p.name;
            if (p.description) catalog.description = p.description;
            const res = await api.updateCatalog({ catalogId: p.catalogId, ...catalog });
            return ok({ result: res });
        }

        case "delete-catalog": {
            if (!p.catalogId) throw new Error("catalogId required");
            const res = await api.deleteCatalog(p.catalogId);
            return ok({ result: res });
        }

        case "get-catalogs": {
            const res = await api.getCatalogList();
            return ok({ catalogs: res });
        }

        case "create-product": {
            if (!p.catalogId || !p.name || !p.price) throw new Error("catalogId, name, price required");
            const product: any = { name: p.name, price: p.price };
            if (p.description) product.description = p.description;
            const res = await api.createProductCatalog({ catalogId: p.catalogId, productName: p.name || "", price: p.price || "", description: p.description || "" });
            return ok({ result: res });
        }

        case "update-product": {
            if (!p.productId) throw new Error("productId required");
            const product: any = {};
            if (p.name) product.name = p.name;
            if (p.price) product.price = p.price;
            if (p.description) product.description = p.description;
            const res = await api.updateProductCatalog({ ...product, productId: p.productId });
            return ok({ result: res });
        }

        case "delete-product": {
            if (!p.productId) throw new Error("productId required");
            const res = await api.deleteProductCatalog({ productIds: p.productId, catalogId: p.catalogId || "" });
            return ok({ result: res });
        }

        case "get-products": {
            if (!p.catalogId) throw new Error("catalogId required");
            const res = await api.getProductCatalogList({ catalogId: p.catalogId });
            return ok({ products: res });
        }

        // â”€â”€ Zalo-level block â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "zalo-block-user": {
            if (!p.userId) throw new Error("userId required");
            const res = await api.blockUser(p.userId);
            return ok({ result: res });
        }

        case "zalo-unblock-user": {
            if (!p.userId) throw new Error("userId required");
            const res = await api.unblockUser(p.userId);
            return ok({ result: res });
        }

        // â”€â”€ Media cache management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "cache-media": {
            if (!p.url) throw new Error("url required");
            const ext = p.ext || "bin";
            const localPath = await downloadAndCacheMedia(p.url, ext);
            return ok({ cached: true, localPath });
        }

        case "get-cached-media": {
            if (!p.url) throw new Error("url required");
            const ext = p.ext || "bin";
            const cached = getCachedMediaPath(p.url, ext);
            if (cached) return ok({ cached: true, localPath: cached });
            return ok({ cached: false });
        }

        case "cleanup-media-cache": {
            const { cleanupCache } = await import("./media.js");
            const cleaned = cleanupCache();
            return ok({ cleaned });
        }

        case "clear-media-cache": {
            const { clearCache } = await import("./media.js");
            clearCache();
            return ok({ cleared: true });
        }

        // â”€â”€ Message formatting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        case "format-message": {
            if (!p.text) throw new Error("text required");
            const { text, truncated } = prepareMessage(p.text, { formatMarkdown: p.formatMarkdown !== false });
            return ok({ text, truncated });
        }

        case "detect-media": {
            if (!p.raw) throw new Error("raw message required");
            const media = detectReceivedMedia(p.raw);
            return ok({ media });
        }
        
        default:
            throw new Error(`Action "${p.action}" not implemented.`);
    }
}




