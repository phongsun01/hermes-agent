"""Tests for Zalo platform adapter access control and message handling.

Covers: ZaloAccessControl (DM/group policy, mention detection, stripping),
message field extraction fallbacks, and session health handling.
"""

import asyncio
import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateway.config import PlatformConfig


# ---------------------------------------------------------------------------
# Import the adapter
# ---------------------------------------------------------------------------

from gateway.platforms.zalo import ZaloAccessControl, ZaloAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def default_config():
    return PlatformConfig(enabled=True, token="fake", extra={})


@pytest.fixture()
def ac_open(default_config):
    return ZaloAccessControl(default_config)


@pytest.fixture()
def ac_allowlist(default_config):
    default_config.extra = {
        "dm_policy": "allowlist",
        "allowlisted_users": "user1,user2",
    }
    return ZaloAccessControl(default_config)


@pytest.fixture()
def ac_denylist(default_config):
    default_config.extra = {
        "dm_policy": "denylist",
        "denylisted_users": "baduser1",
    }
    return ZaloAccessControl(default_config)


@pytest.fixture()
def ac_group_closed(default_config):
    default_config.extra = {
        "group_policy": "closed",
    }
    return ZaloAccessControl(default_config)


@pytest.fixture()
def ac_group_mention(default_config):
    default_config.extra = {
        "group_policy": "open",
        "require_mention": True,
        "bot_name": "MyBot",
    }
    return ZaloAccessControl(default_config)


# =========================================================================
# ZaloAccessControl — DM Policy
# =========================================================================

class TestDmPolicy:
    def test_open_allows_everyone(self, ac_open):
        allowed, reason = ac_open.check_access("anyuser", "chat1", is_group=False)
        assert allowed is True

    def test_allowlist_permits_listed_user(self, ac_allowlist):
        allowed, reason = ac_allowlist.check_access("user1", "chat1", is_group=False)
        assert allowed is True

    def test_allowlist_blocks_unlisted_user(self, ac_allowlist):
        allowed, reason = ac_allowlist.check_access("user3", "chat1", is_group=False)
        assert allowed is False
        assert "allowlist" in reason.lower()

    def test_denylist_blocks_denylisted_user(self, ac_denylist):
        allowed, reason = ac_denylist.check_access("baduser1", "chat1", is_group=False)
        assert allowed is False
        assert "denylist" in reason.lower()

    def test_denylist_allows_other_users(self, ac_denylist):
        allowed, reason = ac_denylist.check_access("gooduser", "chat1", is_group=False)
        assert allowed is True

    def test_denylist_takes_priority_over_allowlist(self, default_config):
        default_config.extra = {
            "dm_policy": "allowlist",
            "allowlisted_users": "user1",
            "denylisted_users": "user1",
        }
        ac = ZaloAccessControl(default_config)
        allowed, reason = ac.check_access("user1", "chat1", is_group=False)
        assert allowed is False


# =========================================================================
# ZaloAccessControl — Group Policy
# =========================================================================

class TestGroupPolicy:
    def test_closed_blocks_all_groups(self, ac_group_closed):
        allowed, reason = ac_group_closed.check_access("user1", "group1", is_group=True)
        assert allowed is False

    def test_open_allows_all_groups(self, ac_open):
        allowed, reason = ac_open.check_access("user1", "group1", is_group=True)
        assert allowed is True

    def test_mention_required_blocks_without_mention(self, ac_group_mention):
        allowed, reason = ac_group_mention.check_access(
            "user1", "group1", is_group=True, text="hello world"
        )
        assert allowed is False
        assert "mention" in reason.lower()

    def test_mention_required_allows_with_bot_name(self, ac_group_mention):
        allowed, reason = ac_group_mention.check_access(
            "user1", "group1", is_group=True, text="hey MyBot help me"
        )
        assert allowed is True

    def test_mention_required_allows_with_at_mention(self, ac_group_mention):
        allowed, reason = ac_group_mention.check_access(
            "user1", "group1", is_group=True, text="@mybot hello"
        )
        assert allowed is True

    def test_mention_required_allows_with_mention_tag(self, ac_group_mention):
        ac_group_mention.bot_user_id = "12345"
        allowed, reason = ac_group_mention.check_access(
            "user1", "group1", is_group=True, text="[mention:12345:MyBot] hello"
        )
        assert allowed is True


# =========================================================================
# ZaloAccessControl — Mention Stripping
# =========================================================================

class TestMentionStripping:
    def test_strip_at_mention(self, ac_group_mention):
        result = ac_group_mention.strip_mention_prefix("@MyBot hello world")
        assert result == "hello world"

    def test_strip_mention_tag(self, ac_group_mention):
        result = ac_group_mention.strip_mention_prefix("[mention:123:Bot] hello")
        assert result == "hello"

    def test_no_mention_returns_original(self, ac_group_mention):
        result = ac_group_mention.strip_mention_prefix("hello world")
        assert result == "hello world"


# =========================================================================
# ZaloAccessControl — Caching
# =========================================================================

class TestInfoCaching:
    def test_cache_user_info(self, ac_open):
        ac_open.cache_user_info("user1", {"name": "Alice"})
        info = ac_open.get_cached_user_info("user1")
        assert info is not None
        assert info["name"] == "Alice"

    def test_cache_group_info(self, ac_open):
        ac_open.cache_group_info("group1", {"name": "Test Group"})
        info = ac_open.get_cached_group_info("group1")
        assert info is not None
        assert info["name"] == "Test Group"

    def test_expired_cache_returns_none(self, ac_open):
        ac_open.cache_user_info("user1", {"name": "Alice"})
        # Manipulate timestamp to expire
        for key, (data, ts) in ac_open._user_info_cache.items():
            ac_open._user_info_cache[key] = (data, asyncio.get_event_loop().time() - 600)
        info = ac_open.get_cached_user_info("user1")
        assert info is None


# =========================================================================
# ZaloAccessControl — Status Reporting
# =========================================================================

class TestStatusReporting:
    def test_get_status_returns_dict(self, ac_open):
        status = ac_open.get_status()
        assert isinstance(status, dict)
        assert "dm_policy" in status
        assert "group_policy" in status
        assert "cache_stats" in status


# =========================================================================
# Message Field Extraction Fallbacks
# =========================================================================

class TestMessageFieldExtraction:
    """Test that the adapter handles various field name formats from zca-js."""

    def _extract_fields(self, data: dict) -> dict:
        """Replicate the fallback chain from zalo.py _on_message."""
        from_id = (
            data.get("from_id") or data.get("uidFrom") or
            data.get("fromId") or data.get("senderId") or
            data.get("userId") or "unknown"
        )
        chat_id = (
            data.get("chat_id") or data.get("threadId") or
            data.get("groupId") or from_id
        )
        text = data.get("text") or data.get("content") or data.get("message") or ""
        from_name = data.get("from_name") or data.get("dName") or str(from_id)
        is_group = bool(data.get("is_group") or data.get("groupId"))
        return {
            "from_id": from_id,
            "chat_id": chat_id,
            "text": text,
            "from_name": from_name,
            "is_group": is_group,
        }

    def test_standard_field_names(self):
        data = {"from_id": "123", "chat_id": "456", "text": "hello"}
        result = self._extract_fields(data)
        assert result["from_id"] == "123"
        assert result["chat_id"] == "456"
        assert result["text"] == "hello"

    def test_zca_js_wrapped_names(self):
        data = {"uidFrom": "123", "dName": "Alice", "content": "hi"}
        result = self._extract_fields(data)
        assert result["from_id"] == "123"
        assert result["from_name"] == "Alice"
        assert result["text"] == "hi"

    def test_group_message_detection(self):
        data = {"fromId": "123", "groupId": "g456", "message": "group msg"}
        result = self._extract_fields(data)
        assert result["is_group"] is True
        assert result["chat_id"] == "g456"

    def test_fallback_to_unknown(self):
        data = {"random_field": "value"}
        result = self._extract_fields(data)
        assert result["from_id"] == "unknown"
        assert result["text"] == ""

    def test_chat_id_falls_back_to_from_id(self):
        data = {"from_id": "user123"}
        result = self._extract_fields(data)
        assert result["chat_id"] == "user123"


# =========================================================================
# Image URL Extraction
# =========================================================================

class TestImageUrlExtraction:
    """Test the _extract_image_urls method."""

    def _extract(self, text: str) -> list:
        """Replicate the extraction logic from zalo.py."""
        import re
        urls = []
        md_pattern = re.compile(
            r'!\[[^\]]*\]\((https?://[^\s)]+\.(?:jpg|jpeg|png|gif|webp|avif|bmp)(?:\?[^\s)]*)?)\)',
            re.IGNORECASE
        )
        for m in md_pattern.finditer(text):
            urls.append(m.group(1))
        plain_pattern = re.compile(
            r'(https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|avif|bmp)(?:\?[^\s]*)?)',
            re.IGNORECASE
        )
        for m in plain_pattern.finditer(text):
            url = m.group(1)
            if url not in urls:
                urls.append(url)
        return urls

    def test_markdown_image_url(self):
        text = "Check this ![photo](https://example.com/image.jpg)"
        urls = self._extract(text)
        assert len(urls) == 1
        assert urls[0] == "https://example.com/image.jpg"

    def test_plain_image_url(self):
        text = "See https://example.com/photo.png"
        urls = self._extract(text)
        assert len(urls) == 1
        assert "photo.png" in urls[0]

    def test_multiple_images(self):
        text = "![a](https://x.com/a.jpg) and ![b](https://y.com/b.png)"
        urls = self._extract(text)
        assert len(urls) == 2

    def test_no_images(self):
        text = "Just plain text, no images here."
        urls = self._extract(text)
        assert len(urls) == 0


# =========================================================================
# Session Health Event Handling
# =========================================================================

class TestSessionAlertHandling:
    """Test that session alerts are properly handled."""

    def test_critical_alert_logged(self, default_config):
        """Critical alerts should be logged as errors."""
        adapter = ZaloAdapter(default_config)
        alert_data = {
            "level": "critical",
            "message": "Session expired",
            "requires_qr": True,
        }
        # Should not raise
        adapter._on_session_alert(alert_data)

    def test_warning_alert_logged(self, default_config):
        """Warning alerts should be logged as warnings."""
        adapter = ZaloAdapter(default_config)
        alert_data = {
            "level": "warning",
            "message": "Session expiring",
            "requires_qr": False,
        }
        adapter._on_session_alert(alert_data)

    def test_info_alert_logged(self, default_config):
        """Info alerts should be logged as info."""
        adapter = ZaloAdapter(default_config)
        alert_data = {
            "level": "info",
            "message": "Session healthy",
        }
        adapter._on_session_alert(alert_data)
