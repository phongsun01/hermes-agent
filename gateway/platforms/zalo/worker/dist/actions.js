import { ThreadType, Reactions } from "zca-js";
import { getApi } from "./client.js";
import * as nodeFs from "node:fs";
import * as nodePath from "node:path";
import * as nodeOs from "node:os";
// Helper for result formatting
function ok(data) {
    return {
        success: true,
        data: data
    };
}
// ─── Name→ID resolvers (Extracted from zaloclaw) ──────────────────────────────
export async function resolveUserId(nameOrId) {
    if (/^\d+$/.test(nameOrId))
        return nameOrId;
    const api = await getApi();
    const friends = await api.getAllFriends();
    const list = Array.isArray(friends) ? friends : [];
    const q = nameOrId.toLowerCase();
    const hit = list.find((f) => (f.displayName ?? "").toLowerCase() === q ||
        (f.zaloName ?? "").toLowerCase() === q);
    if (hit)
        return String(hit.userId);
    throw new Error(`User not found: "${nameOrId}"`);
}
export async function resolveGroupId(nameOrId) {
    if (/^\d+$/.test(nameOrId))
        return nameOrId;
    const api = await getApi();
    const resp = await api.getAllGroups();
    const ids = Object.keys(resp?.gridVerMap ?? {});
    if (ids.length === 0)
        throw new Error("No groups found");
    const info = await api.getGroupInfo(ids);
    const map = info?.gridInfoMap ?? {};
    const q = nameOrId.toLowerCase();
    const hit = Object.entries(map).find(([, g]) => (g.name ?? "").toLowerCase() === q);
    if (hit)
        return hit[0];
    throw new Error(`Group not found: "${nameOrId}"`);
}
export function extractMemberIds(groupInfo) {
    const ids = groupInfo?.memberIds ?? [];
    if (ids.length > 0)
        return ids;
    const verList = groupInfo?.memVerList ?? [];
    return verList.map((e) => e.split("_")[0]).filter(Boolean);
}
// ─── Reaction icon resolver ──────────────────────────────────────────────────
const REACTION_MAP = {
    heart: Reactions.HEART, love: Reactions.HEART,
    like: Reactions.LIKE, thumbsup: Reactions.LIKE,
    haha: Reactions.HAHA, laugh: Reactions.HAHA,
    wow: Reactions.WOW, surprised: Reactions.WOW,
    cry: Reactions.CRY, sad: Reactions.CRY,
    angry: Reactions.ANGRY,
    none: Reactions.NONE,
    "👍": Reactions.LIKE, "❤️": Reactions.HEART, "😆": Reactions.HAHA,
    "😮": Reactions.WOW, "😢": Reactions.CRY, "😠": Reactions.ANGRY,
};
function resolveReaction(raw) {
    return REACTION_MAP[raw.toLowerCase()] ?? raw;
}
export async function dispatch(p) {
    const api = await getApi();
    switch (p.action) {
        case "send": {
            if (!p.threadId || !p.message)
                throw new Error("threadId and message required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const content = { msg: p.message };
            if (p.urgency !== undefined)
                content.urgency = p.urgency;
            const res = await api.sendMessage(content, p.threadId, type);
            return ok({ msgId: res?.message?.msgId });
        }
        case "send-image": {
            if (!p.threadId || !p.url)
                throw new Error("threadId and url required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            let resolvedPath = p.url;
            if (/^https?:\/\//i.test(p.url)) {
                // Simplified download logic
                const tmpDir = nodeOs.tmpdir();
                resolvedPath = nodePath.join(tmpDir, `zalo-img-${Date.now()}.jpg`);
                // Note: Real implementation would use fetch
                const response = await fetch(p.url);
                const buffer = Buffer.from(await response.arrayBuffer());
                nodeFs.writeFileSync(resolvedPath, buffer);
            }
            try {
                const res = await api.sendMessage({ msg: p.message || "", attachments: [resolvedPath] }, p.threadId, type);
                return ok({ msgId: res?.message?.msgId });
            }
            finally {
                if (/^https?:\/\//i.test(p.url)) {
                    try {
                        nodeFs.unlinkSync(resolvedPath);
                    }
                    catch { }
                }
            }
        }
        case "send-file": {
            if (!p.threadId)
                throw new Error("threadId required");
            const localFile = p.filePath || p.url;
            if (!localFile)
                throw new Error("filePath or url required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            let resolvedPath = localFile;
            if (/^https?:\/\//i.test(localFile)) {
                const tmpDir = nodeOs.tmpdir();
                resolvedPath = nodePath.join(tmpDir, `zalo-file-${Date.now()}`);
                const response = await fetch(localFile);
                const buffer = Buffer.from(await response.arrayBuffer());
                nodeFs.writeFileSync(resolvedPath, buffer);
            }
            try {
                const res = await api.sendMessage({ msg: p.message || "", attachments: [resolvedPath] }, p.threadId, type);
                return ok({ success: true, message: res?.message });
            }
            finally {
                if (/^https?:\/\//i.test(localFile)) {
                    try {
                        nodeFs.unlinkSync(resolvedPath);
                    }
                    catch { }
                }
            }
        }
        case "add-reaction": {
            if (!p.msgId || !p.icon || !p.threadId)
                throw new Error("msgId, icon and threadId required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            // Note: zaloclaw uses cliMsgId which we might not have yet in this simple worker
            // but zca-js supports msgId in some cases
            const res = await api.addReaction(resolveReaction(p.icon), {
                data: { msgId: p.msgId, cliMsgId: p.cliMsgId || p.msgId },
                threadId: p.threadId,
                type,
            });
            return ok(res);
        }
        case "friends": {
            const friends = await api.getAllFriends();
            return ok(friends);
        }
        case "groups": {
            const groups = await api.getAllGroups();
            return ok(groups);
        }
        case "get-group-info": {
            const gid = await resolveGroupId(p.groupId || p.threadId);
            const info = await api.getGroupInfo([gid]);
            return ok(info?.gridInfoMap?.[gid]);
        }
        case "me": {
            const me = await api.getUserInfo([api.getOwnId()]);
            return ok(me);
        }
        default:
            throw new Error(`Action "${p.action}" not implemented in worker yet.`);
    }
}
