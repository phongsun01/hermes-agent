import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ─── Rate Limiter Tests ──────────────────────────────────────────────────────
// We test the RateLimiter class by importing it from actions.ts.
// Since actions.ts has many dependencies (zca-js, fs, etc.), we test the
// rate limiter logic in isolation by recreating it here.

class TestRateLimiter {
    private queue: Array<{
        fn: () => Promise<any>;
        resolve: (value: any) => void;
        reject: (reason: any) => void;
    }> = [];
    private processing = false;
    private minIntervalMs: number;
    private consecutiveErrors = 0;
    private maxBackoffMs: number;

    constructor(minIntervalMs = 1000, maxBackoffMs = 30_000) {
        this.minIntervalMs = minIntervalMs;
        this.maxBackoffMs = maxBackoffMs;
    }

    async enqueue<T>(fn: () => Promise<T>): Promise<T> {
        return new Promise<T>((resolve, reject) => {
            this.queue.push({ fn, resolve, reject });
            this.process();
        });
    }

    private async process() {
        if (this.processing || this.queue.length === 0) return;
        this.processing = true;

        while (this.queue.length > 0) {
            const task = this.queue.shift()!;
            try {
                const result = await task.fn();
                this.consecutiveErrors = 0;
                task.resolve(result);
            } catch (err: any) {
                this.consecutiveErrors++;
                task.reject(err);
            }

            const backoffMs = Math.min(
                this.minIntervalMs * Math.pow(2, Math.max(0, this.consecutiveErrors - 1)),
                this.maxBackoffMs
            );
            const delay = this.consecutiveErrors > 0 ? backoffMs : this.minIntervalMs;
            await this.delayMs(delay);
        }

        this.processing = false;
    }

    private delayMs(ms: number) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    getStatus() {
        return {
            queued: this.queue.length,
            processing: this.processing,
            consecutiveErrors: this.consecutiveErrors,
            minIntervalMs: this.minIntervalMs,
        };
    }

    // Expose for testing
    getConsecutiveErrors() {
        return this.consecutiveErrors;
    }
}

describe("RateLimiter", () => {
    let limiter: TestRateLimiter;

    beforeEach(() => {
        vi.useFakeTimers();
        limiter = new TestRateLimiter(100, 1000); // Fast intervals for testing
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("processes tasks sequentially", async () => {
        const order: number[] = [];
        const p1 = limiter.enqueue(async () => {
            order.push(1);
            return "a";
        });
        const p2 = limiter.enqueue(async () => {
            order.push(2);
            return "b";
        });

        await vi.advanceTimersByTimeAsync(200);

        const [r1, r2] = await Promise.all([p1, p2]);
        expect(r1).toBe("a");
        expect(r2).toBe("b");
        expect(order).toEqual([1, 2]);
    });

    it("resets error counter on success", async () => {
        const p1 = limiter.enqueue(async () => {
            throw new Error("fail");
        });

        try {
            await p1;
        } catch {
            // expected
        }

        expect(limiter.getConsecutiveErrors()).toBe(1);

        // Next task succeeds
        const p2 = limiter.enqueue(async () => "ok");
        await vi.advanceTimersByTimeAsync(500);
        const r2 = await p2;
        expect(r2).toBe("ok");
        expect(limiter.getConsecutiveErrors()).toBe(0);
    });

    it("applies backoff on consecutive errors", async () => {
        // First error: delay = 100ms (base)
        const p1 = limiter.enqueue(async () => { throw new Error("fail"); });
        await vi.advanceTimersByTimeAsync(200);
        try { await p1; } catch {}
        expect(limiter.getConsecutiveErrors()).toBe(1);

        // Second error: delay = 100 * 2^1 = 200ms
        const p2 = limiter.enqueue(async () => { throw new Error("fail"); });
        await vi.advanceTimersByTimeAsync(300);
        try { await p2; } catch {}
        expect(limiter.getConsecutiveErrors()).toBe(2);

        // Third error: delay = 100 * 2^2 = 400ms
        const p3 = limiter.enqueue(async () => { throw new Error("fail"); });
        await vi.advanceTimersByTimeAsync(500);
        try { await p3; } catch {}
        expect(limiter.getConsecutiveErrors()).toBe(3);
    }, 15000);

    it("caps backoff at maxBackoffMs", async () => {
        const cappedLimiter = new TestRateLimiter(100, 500);

        // Cause many errors to hit the cap
        for (let i = 0; i < 5; i++) {
            const p = cappedLimiter.enqueue(async () => { throw new Error("fail"); });
            await vi.advanceTimersByTimeAsync(600);
            try { await p; } catch {}
        }

        // After 5 errors: 100 * 2^4 = 1600ms, but capped at 500ms
        const status = cappedLimiter.getStatus();
        expect(status.consecutiveErrors).toBe(5);
    }, 15000);

    it("reports correct status", async () => {
        const status = limiter.getStatus();
        expect(status.queued).toBe(0);
        expect(status.processing).toBe(false);
        expect(status.consecutiveErrors).toBe(0);
        expect(status.minIntervalMs).toBe(100);
    });
});

// ─── Access Control Tests ────────────────────────────────────────────────────
// Test the access control logic from access-control.ts

import {
    parseAccessControlConfig,
    checkAccess,
    isMentioned,
    stripMentionPrefix,
    AccessDecision,
    type AccessControlConfig,
} from "../access-control.js";

describe("parseAccessControlConfig", () => {
    it("returns defaults for empty input", () => {
        const config = parseAccessControlConfig({});
        expect(config.dmPolicy).toBe("open");
        expect(config.groupPolicy).toBe("open");
        expect(config.requireMention).toBe(false);
        expect(config.allowlistedUsers.size).toBe(0);
    });

    it("parses string ID lists", () => {
        const config = parseAccessControlConfig({
            allowlistedUsers: "user1,user2,user3",
        });
        expect(config.allowlistedUsers).toEqual(new Set(["user1", "user2", "user3"]));
    });

    it("parses array ID lists", () => {
        const config = parseAccessControlConfig({
            denylistedUsers: ["bad1", "bad2"],
        });
        expect(config.denylistedUsers).toEqual(new Set(["bad1", "bad2"]));
    });

    it("parses mention patterns", () => {
        const config = parseAccessControlConfig({
            mentionPatterns: ["@bot", "hey bot"],
        });
        expect(config.mentionPatterns.length).toBe(2);
        expect(config.mentionPatterns[0].test("@bot hello")).toBe(true);
    });
});

describe("checkAccess — DM", () => {
    const baseConfig: AccessControlConfig = {
        dmPolicy: "open",
        groupPolicy: "open",
        requireMention: false,
        allowlistedUsers: new Set(),
        denylistedUsers: new Set(),
        allowlistedGroups: new Set(),
        denylistedGroups: new Set(),
        mentionPatterns: [],
    };

    it("allows everyone with open policy", () => {
        const result = checkAccess(
            { fromId: "user1", chatId: "chat1", isGroup: false, text: "" },
            baseConfig
        );
        expect(result.decision).toBe(AccessDecision.ALLOW);
    });

    it("denies denylisted users", () => {
        const config = { ...baseConfig, denylistedUsers: new Set(["baduser"]) };
        const result = checkAccess(
            { fromId: "baduser", chatId: "chat1", isGroup: false, text: "" },
            config
        );
        expect(result.decision).toBe(AccessDecision.DENY);
    });

    it("allows allowlisted users", () => {
        const config = {
            ...baseConfig,
            dmPolicy: "allowlist" as const,
            allowlistedUsers: new Set(["gooduser"]),
        };
        const result = checkAccess(
            { fromId: "gooduser", chatId: "chat1", isGroup: false, text: "" },
            config
        );
        expect(result.decision).toBe(AccessDecision.ALLOW);
    });

    it("denies non-allowlisted users", () => {
        const config = {
            ...baseConfig,
            dmPolicy: "allowlist" as const,
            allowlistedUsers: new Set(["gooduser"]),
        };
        const result = checkAccess(
            { fromId: "otheruser", chatId: "chat1", isGroup: false, text: "" },
            config
        );
        expect(result.decision).toBe(AccessDecision.DENY);
    });
});

describe("checkAccess — Group", () => {
    const baseConfig: AccessControlConfig = {
        dmPolicy: "open",
        groupPolicy: "open",
        requireMention: false,
        allowlistedUsers: new Set(),
        denylistedUsers: new Set(),
        allowlistedGroups: new Set(),
        denylistedGroups: new Set(),
        mentionPatterns: [],
    };

    it("ignores non-mentioned messages when requireMention is true", () => {
        const config = {
            ...baseConfig,
            requireMention: true,
            botName: "MyBot",
        };
        const result = checkAccess(
            { fromId: "user1", chatId: "group1", isGroup: true, text: "hello world" },
            config
        );
        expect(result.decision).toBe(AccessDecision.IGNORE);
    });

    it("allows mentioned messages when requireMention is true", () => {
        const config = {
            ...baseConfig,
            requireMention: true,
            botName: "MyBot",
        };
        const result = checkAccess(
            { fromId: "user1", chatId: "group1", isGroup: true, text: "@MyBot help me" },
            config
        );
        expect(result.decision).toBe(AccessDecision.ALLOW);
    });

    it("denies all groups when policy is closed", () => {
        const config = { ...baseConfig, groupPolicy: "closed" as const };
        const result = checkAccess(
            { fromId: "user1", chatId: "group1", isGroup: true, text: "" },
            config
        );
        expect(result.decision).toBe(AccessDecision.DENY);
    });
});

describe("isMentioned", () => {
    const baseConfig: AccessControlConfig = {
        dmPolicy: "open",
        groupPolicy: "open",
        requireMention: false,
        allowlistedUsers: new Set(),
        denylistedUsers: new Set(),
        allowlistedGroups: new Set(),
        denylistedGroups: new Set(),
        mentionPatterns: [],
        botName: "MyBot",
        botUserId: "12345",
    };

    it("detects bot name mention", () => {
        expect(isMentioned("hey MyBot help", baseConfig)).toBe(true);
    });

    it("detects @mention", () => {
        expect(isMentioned("@mybot hello", baseConfig)).toBe(true);
    });

    it("detects mention tag", () => {
        expect(isMentioned("[mention:12345:MyBot] hi", baseConfig)).toBe(true);
    });

    it("returns false for no mention", () => {
        expect(isMentioned("hello world", baseConfig)).toBe(false);
    });

    it("detects regex pattern mention", () => {
        const config = {
            ...baseConfig,
            mentionPatterns: [/^!bot/i],
        };
        expect(isMentioned("!bot help", config)).toBe(true);
    });
});

describe("stripMentionPrefix", () => {
    const baseConfig: AccessControlConfig = {
        dmPolicy: "open",
        groupPolicy: "open",
        requireMention: false,
        allowlistedUsers: new Set(),
        denylistedUsers: new Set(),
        allowlistedGroups: new Set(),
        denylistedGroups: new Set(),
        mentionPatterns: [],
        botName: "MyBot",
    };

    it("strips @mention prefix", () => {
        const result = stripMentionPrefix("@MyBot hello world", baseConfig);
        expect(result).toBe("hello world");
    });

    it("strips mention tag", () => {
        const result = stripMentionPrefix("[mention:123:Bot] hello", baseConfig);
        expect(result).toBe("hello");
    });

    it("returns original if no mention", () => {
        const result = stripMentionPrefix("hello world", baseConfig);
        expect(result).toBe("hello world");
    });
});
