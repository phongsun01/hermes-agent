import { ThreadType, Reactions } from "zca-js";
import { getApi } from "./client.js";
import * as nodePath from "node:path";
import { getCachedUserInfo, setCachedUserInfo, getCachedGroupInfo, setCachedGroupInfo, } from "./access-control.js";
import { resolveMediaSource, prepareMessage, downloadAndCacheMedia, getCachedMediaPath, detectReceivedMedia, } from "./media.js";
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
            if (!p.threadId)
                throw new Error("threadId required");
            const source = p.url || p.filePath || p.localPath;
            if (!source)
                throw new Error("url, filePath, or localPath required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const { path: resolvedPath, cleanup } = await resolveMediaSource(source, "zalo-img");
            try {
                const caption = p.message ? prepareMessage(p.message).text : "";
                const res = await api.sendMessage({ msg: caption, attachments: [resolvedPath] }, p.threadId, type);
                return ok({ msgId: res?.message?.msgId });
            }
            finally {
                cleanup();
            }
        }
        case "send-file": {
            if (!p.threadId)
                throw new Error("threadId required");
            const source = p.filePath || p.url || p.localPath;
            if (!source)
                throw new Error("filePath, url, or localPath required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const { path: resolvedPath, cleanup } = await resolveMediaSource(source, "zalo-file");
            try {
                const caption = p.message ? prepareMessage(p.message).text : "";
                const res = await api.sendMessage({ msg: caption, attachments: [resolvedPath] }, p.threadId, type);
                return ok({ msgId: res?.message?.msgId, fileName: nodePath.basename(resolvedPath) });
            }
            finally {
                cleanup();
            }
        }
        case "send-video": {
            if (!p.threadId)
                throw new Error("threadId required");
            const source = p.url || p.filePath || p.localPath;
            if (!source)
                throw new Error("url, filePath, or localPath required");
            const type = p.isGroup ? ThreadType.Group : ThreadType.User;
            const { path: resolvedPath, cleanup } = await resolveMediaSource(source, "zalo-video");
            try {
                const caption = p.message ? prepareMessage(p.message).text : "";
                const res = await api.sendMessage({ msg: caption, attachments: [resolvedPath] }, p.threadId, type);
                return ok({ msgId: res?.message?.msgId });
            }
            finally {
                cleanup();
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
        case "get-user-info": {
            const userId = p.userId || p.threadId;
            if (!userId)
                throw new Error("userId required");
            const cached = getCachedUserInfo(userId);
            if (cached)
                return ok({ ...cached, cached: true });
            const info = await api.getUserInfo([userId]);
            if (info && info[userId]) {
                setCachedUserInfo(userId, info[userId]);
            }
            return ok(info?.[userId]);
        }
        case "get-group-info": {
            const gid = await resolveGroupId(p.groupId || p.threadId);
            const cached = getCachedGroupInfo(gid);
            if (cached)
                return ok({ ...cached, cached: true });
            const info = await api.getGroupInfo([gid]);
            const groupData = info?.gridInfoMap?.[gid];
            if (groupData) {
                setCachedGroupInfo(gid, groupData);
            }
            return ok(groupData);
        }
        case "refresh-group-info": {
            const gid = await resolveGroupId(p.groupId || p.threadId);
            const info = await api.getGroupInfo([gid]);
            const groupData = info?.gridInfoMap?.[gid];
            if (groupData) {
                setCachedGroupInfo(gid, groupData);
            }
            return ok(groupData);
        }
        // Media cache management
        case "cache-media": {
            if (!p.url)
                throw new Error("url required");
            const ext = p.ext || "bin";
            const localPath = await downloadAndCacheMedia(p.url, ext);
            return ok({ cached: true, localPath });
        }
        case "get-cached-media": {
            if (!p.url)
                throw new Error("url required");
            const ext = p.ext || "bin";
            const cached = getCachedMediaPath(p.url, ext);
            if (cached) {
                return ok({ cached: true, localPath: cached });
            }
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
        // Message formatting
        case "format-message": {
            if (!p.text)
                throw new Error("text required");
            const { text, truncated } = prepareMessage(p.text, { formatMarkdown: p.formatMarkdown !== false });
            return ok({ text, truncated });
        }
        case "detect-media": {
            if (!p.raw)
                throw new Error("raw message required");
            const media = detectReceivedMedia(p.raw);
            return ok({ media });
        }
        default:
            throw new Error(`Action "${p.action}" not implemented in worker yet.`);
    }
}
