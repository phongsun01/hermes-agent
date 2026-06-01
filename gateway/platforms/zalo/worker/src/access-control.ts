/**
 * Access Control for Zalo Platform
 *
 * Ported from zaloclaw patterns:
 * - DM policy: control who can DM the bot (allowlist, denylist, open, closed)
 * - Group policy: control which groups the bot responds to
 * - Mention gating: require @mention in groups before responding
 * - Per-user and per-group overrides
 */

import { getCurrentUid } from "./client.js";

// ─── Policy Types ────────────────────────────────────────────────────────────

export type DmPolicy = "open" | "closed" | "allowlist" | "denylist";
export type GroupPolicy = "open" | "closed" | "allowlist" | "denylist";

export interface AccessControlConfig {
    dmPolicy: DmPolicy;
    groupPolicy: GroupPolicy;
    requireMention: boolean;
    allowlistedUsers: Set<string>;
    denylistedUsers: Set<string>;
    allowlistedGroups: Set<string>;
    denylistedGroups: Set<string>;
    mentionPatterns: RegExp[];
    botName?: string;
    botUserId?: string;
}

export const DEFAULT_CONFIG: AccessControlConfig = {
    dmPolicy: "open",
    groupPolicy: "open",
    requireMention: false,
    allowlistedUsers: new Set(),
    denylistedUsers: new Set(),
    allowlistedGroups: new Set(),
    denylistedGroups: new Set(),
    mentionPatterns: [],
};

// ─── Config Parser ───────────────────────────────────────────────────────────

export function parseAccessControlConfig(raw: any): AccessControlConfig {
    if (!raw || typeof raw !== "object") {
        return { ...DEFAULT_CONFIG };
    }

    const dmPolicy = parseDmPolicy(raw.dmPolicy);
    const groupPolicy = parseGroupPolicy(raw.groupPolicy);
    const requireMention = Boolean(raw.requireMention);

    const allowlistedUsers = parseIdSet(raw.allowlistedUsers);
    const denylistedUsers = parseIdSet(raw.denylistedUsers);
    const allowlistedGroups = parseIdSet(raw.allowlistedGroups);
    const denylistedGroups = parseIdSet(raw.denylistedGroups);

    const mentionPatterns = parseMentionPatterns(raw.mentionPatterns);

    return {
        dmPolicy,
        groupPolicy,
        requireMention,
        allowlistedUsers,
        denylistedUsers,
        allowlistedGroups,
        denylistedGroups,
        mentionPatterns,
        botName: raw.botName,
        botUserId: raw.botUserId,
    };
}

function parseDmPolicy(value: any): DmPolicy {
    if (typeof value === "string" && ["open", "closed", "allowlist", "denylist"].includes(value)) {
        return value as DmPolicy;
    }
    return "open";
}

function parseGroupPolicy(value: any): GroupPolicy {
    if (typeof value === "string" && ["open", "closed", "allowlist", "denylist"].includes(value)) {
        return value as GroupPolicy;
    }
    return "open";
}

function parseIdSet(value: any): Set<string> {
    if (Array.isArray(value)) {
        return new Set(value.map(String).filter(Boolean));
    }
    if (typeof value === "string" && value.trim()) {
        return new Set(value.split(",").map(s => s.trim()).filter(Boolean));
    }
    return new Set();
}

function parseMentionPatterns(value: any): RegExp[] {
    if (Array.isArray(value)) {
        const patterns: RegExp[] = [];
        for (const p of value) {
            if (typeof p === "string" && p.trim()) {
                try {
                    patterns.push(new RegExp(p, "i"));
                } catch {
                    console.error(`[Zalo AC] Invalid mention pattern: ${p}`);
                }
            }
        }
        return patterns;
    }
    if (typeof value === "string" && value.trim()) {
        try {
            return [new RegExp(value, "i")];
        } catch {
            return [];
        }
    }
    return [];
}

// ─── Access Check Engine ─────────────────────────────────────────────────────

export interface MessageContext {
    fromId: string;
    chatId: string;
    isGroup: boolean;
    text: string;
}

export enum AccessDecision {
    ALLOW = "allow",
    DENY = "deny",
    IGNORE = "ignore",
}

export interface AccessResult {
    decision: AccessDecision;
    reason?: string;
}

export function checkAccess(
    ctx: MessageContext,
    config: AccessControlConfig,
): AccessResult {
    if (ctx.isGroup) {
        return checkGroupAccess(ctx, config);
    }
    return checkDmAccess(ctx, config);
}

function checkDmAccess(
    ctx: MessageContext,
    config: AccessControlConfig,
): AccessResult {
    const { fromId } = ctx;

    // Denylist takes priority
    if (config.denylistedUsers.has(fromId)) {
        return { decision: AccessDecision.DENY, reason: "user denylisted" };
    }

    switch (config.dmPolicy) {
        case "open":
            return { decision: AccessDecision.ALLOW };

        case "closed":
            return { decision: AccessDecision.DENY, reason: "DM policy is closed" };

        case "allowlist":
            if (config.allowlistedUsers.has(fromId)) {
                return { decision: AccessDecision.ALLOW };
            }
            return { decision: AccessDecision.DENY, reason: "user not in allowlist" };

        case "denylist":
            return { decision: AccessDecision.ALLOW };

        default:
            return { decision: AccessDecision.ALLOW };
    }
}

function checkGroupAccess(
    ctx: MessageContext,
    config: AccessControlConfig,
): AccessResult {
    const { fromId, chatId, text } = ctx;

    // Denylist takes priority (user-level)
    if (config.denylistedUsers.has(fromId)) {
        return { decision: AccessDecision.DENY, reason: "user denylisted" };
    }

    // Group-level policy
    switch (config.groupPolicy) {
        case "closed":
            return { decision: AccessDecision.DENY, reason: "group policy is closed" };

        case "allowlist":
            if (!config.allowlistedGroups.has(chatId)) {
                return { decision: AccessDecision.DENY, reason: "group not in allowlist" };
            }
            break;

        case "denylist":
            if (config.denylistedGroups.has(chatId)) {
                return { decision: AccessDecision.DENY, reason: "group denylisted" };
            }
            break;

        case "open":
        default:
            break;
    }

    // Mention gating
    if (config.requireMention) {
        if (!isMentioned(text, config)) {
            return { decision: AccessDecision.IGNORE, reason: "bot not mentioned" };
        }
    }

    return { decision: AccessDecision.ALLOW };
}

// ─── Mention Detection ───────────────────────────────────────────────────────

export function isMentioned(text: string, config: AccessControlConfig): boolean {
    if (!text) return false;

    // Check regex mention patterns first
    for (const pattern of config.mentionPatterns) {
        if (pattern.test(text)) {
            return true;
        }
    }

    // Check bot name mention (case-insensitive)
    if (config.botName) {
        const botNameLower = config.botName.toLowerCase();
        const textLower = text.toLowerCase();

        // Direct name match: "BotName" or "@BotName"
        if (textLower.includes(botNameLower)) {
            return true;
        }

        // Check for @mention style
        if (textLower.startsWith("@" + botNameLower) || textLower.includes(" @" + botNameLower)) {
            return true;
        }
    }

    // Check bot user ID mention
    if (config.botUserId) {
        if (text.includes(config.botUserId)) {
            return true;
        }
    }

    // Fallback: check for common Zalo mention patterns
    // Zalo uses [mention:user_id:name] format in some contexts
    if (config.botUserId) {
        const mentionPattern = new RegExp(`\\[mention:${config.botUserId}`, "i");
        if (mentionPattern.test(text)) {
            return true;
        }
    }

    return false;
}

// ─── Strip Mention Prefix ────────────────────────────────────────────────────

export function stripMentionPrefix(text: string, config: AccessControlConfig): string {
    if (!text) return text;

    // Strip @botname prefix
    if (config.botName) {
        const botNameLower = config.botName.toLowerCase();
        const textLower = text.toLowerCase();

        if (textLower.startsWith("@" + botNameLower)) {
            return text.slice(botNameLower.length + 1).trim();
        }
    }

    // Strip [mention:...] tags
    const mentionTagPattern = /^\[mention:[^\]]*\]\s*/i;
    return text.replace(mentionTagPattern, "").trim();
}

// ─── Cache for User/Group Info ───────────────────────────────────────────────

interface CachedInfo {
    data: any;
    cachedAt: number;
}

const TTL_MS = 5 * 60 * 1000; // 5 minutes

const userInfoCache = new Map<string, CachedInfo>();
const groupInfoCache = new Map<string, CachedInfo>();

export function getCachedUserInfo(userId: string): any | null {
    const cached = userInfoCache.get(userId);
    if (cached && Date.now() - cached.cachedAt < TTL_MS) {
        return cached.data;
    }
    userInfoCache.delete(userId);
    return null;
}

export function setCachedUserInfo(userId: string, data: any): void {
    userInfoCache.set(userId, { data, cachedAt: Date.now() });
}

export function getCachedGroupInfo(groupId: string): any | null {
    const cached = groupInfoCache.get(groupId);
    if (cached && Date.now() - cached.cachedAt < TTL_MS) {
        return cached.data;
    }
    groupInfoCache.delete(groupId);
    return null;
}

export function setCachedGroupInfo(groupId: string, data: any): void {
    groupInfoCache.set(groupId, { data, cachedAt: Date.now() });
}

export function clearAllCaches(): void {
    userInfoCache.clear();
    groupInfoCache.clear();
}

// ─── Status Reporting ────────────────────────────────────────────────────────

export function getAccessControlStatus(config: AccessControlConfig): any {
    return {
        dmPolicy: config.dmPolicy,
        groupPolicy: config.groupPolicy,
        requireMention: config.requireMention,
        allowlistedUsers: config.allowlistedUsers.size,
        denylistedUsers: config.denylistedUsers.size,
        allowlistedGroups: config.allowlistedGroups.size,
        denylistedGroups: config.denylistedGroups.size,
        mentionPatterns: config.mentionPatterns.length,
        botName: config.botName,
        botUserId: config.botUserId,
        cacheStats: {
            userInfoEntries: userInfoCache.size,
            groupInfoEntries: groupInfoCache.size,
        },
    };
}
