
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    ProcessingOutcome,
    SendResult,
)

logger = logging.getLogger(__name__)


class ZaloAccessControl:
    """Python-side access control for Zalo messages.

    Mirrors the worker-side access control for defense-in-depth.
    The worker does the primary filtering; this layer catches any
    messages that slip through and provides Python-side config access.
    """

    def __init__(self, config: PlatformConfig):
        self.dm_policy = self._parse_dm_policy(config)
        self.group_policy = self._parse_group_policy(config)
        self.require_mention = self._parse_require_mention(config)
        self.allowlisted_users = self._parse_id_set(config, "allowlisted_users")
        self.denylisted_users = self._parse_id_set(config, "denylisted_users")
        self.allowlisted_groups = self._parse_id_set(config, "allowlisted_groups")
        self.denylisted_groups = self._parse_id_set(config, "denylisted_groups")
        self.mention_patterns = self._compile_mention_patterns(config)
        self.bot_name = self._get_bot_name(config)
        self.bot_user_id = self._get_bot_user_id(config)

        # Info caches (TTL-based)
        self._user_info_cache: Dict[str, tuple] = {}
        self._group_info_cache: Dict[str, tuple] = {}
        self._cache_ttl = 300  # 5 minutes

    def _parse_dm_policy(self, config: PlatformConfig) -> str:
        raw = config.extra.get("dm_policy") or os.getenv("ZALO_DM_POLICY", "open")
        if raw in ("open", "closed", "allowlist", "denylist"):
            return raw
        return "open"

    def _parse_group_policy(self, config: PlatformConfig) -> str:
        raw = config.extra.get("group_policy") or os.getenv("ZALO_GROUP_POLICY", "open")
        if raw in ("open", "closed", "allowlist", "denylist"):
            return raw
        return "open"

    def _parse_require_mention(self, config: PlatformConfig) -> bool:
        raw = config.extra.get("require_mention")
        if raw is None:
            raw = os.getenv("ZALO_REQUIRE_MENTION", "false")
        if isinstance(raw, str):
            return raw.lower() in ("true", "1", "yes", "on")
        return bool(raw)

    def _parse_id_set(self, config: PlatformConfig, key: str) -> Set[str]:
        raw = config.extra.get(key)
        if raw is None:
            env_key = f"ZALO_{key.upper()}"
            raw = os.getenv(env_key, "")
        if isinstance(raw, list):
            return {str(x).strip() for x in raw if str(x).strip()}
        if isinstance(raw, str):
            return {x.strip() for x in raw.split(",") if x.strip()}
        return set()

    def _compile_mention_patterns(self, config: PlatformConfig) -> List[re.Pattern]:
        raw = config.extra.get("mention_patterns")
        if raw is None:
            raw = os.getenv("ZALO_MENTION_PATTERNS", "")
        if isinstance(raw, str) and raw.strip():
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                loaded = [raw.strip()]
        elif isinstance(raw, list):
            loaded = raw
        else:
            return []

        compiled = []
        for pattern in loaded:
            if isinstance(pattern, str) and pattern.strip():
                try:
                    compiled.append(re.compile(pattern, re.IGNORECASE))
                except re.error as exc:
                    logger.warning("[Zalo AC] Invalid mention pattern %r: %s", pattern, exc)
        return compiled

    def _get_bot_name(self, config: PlatformConfig) -> Optional[str]:
        return config.extra.get("bot_name") or os.getenv("ZALO_BOT_NAME")

    def _get_bot_user_id(self, config: PlatformConfig) -> Optional[str]:
        return config.extra.get("bot_user_id") or os.getenv("ZALO_BOT_USER_ID")

    def check_access(self, from_id: str, chat_id: str, is_group: bool, text: str = "") -> tuple[bool, str]:
        """Check if a message should be processed.

        Returns (allowed, reason) tuple.
        """
        if is_group:
            return self._check_group_access(from_id, chat_id, text)
        return self._check_dm_access(from_id)

    def _check_dm_access(self, from_id: str) -> tuple[bool, str]:
        if from_id in self.denylisted_users:
            return False, "user denylisted"

        if self.dm_policy == "open":
            return True, ""
        if self.dm_policy == "closed":
            return False, "DM policy is closed"
        if self.dm_policy == "allowlist":
            if from_id in self.allowlisted_users:
                return True, ""
            return False, "user not in allowlist"
        if self.dm_policy == "denylist":
            return True, ""

        return True, ""

    def _check_group_access(self, from_id: str, chat_id: str, text: str) -> tuple[bool, str]:
        if from_id in self.denylisted_users:
            return False, "user denylisted"

        if self.group_policy == "closed":
            return False, "group policy is closed"
        if self.group_policy == "allowlist":
            if chat_id not in self.allowlisted_groups:
                return False, "group not in allowlist"
        if self.group_policy == "denylist":
            if chat_id in self.denylisted_groups:
                return False, "group denylisted"

        if self.require_mention:
            if not self._is_mentioned(text):
                return False, "bot not mentioned"

        return True, ""

    def _is_mentioned(self, text: str) -> bool:
        if not text:
            return False

        for pattern in self.mention_patterns:
            if pattern.search(text):
                return True

        if self.bot_name:
            bot_lower = self.bot_name.lower()
            text_lower = text.lower()
            if bot_lower in text_lower:
                return True

        if self.bot_user_id and self.bot_user_id in text:
            return True

        if self.bot_user_id:
            if re.search(rf'\[mention:{re.escape(self.bot_user_id)}', text, re.IGNORECASE):
                return True

        return False

    def strip_mention_prefix(self, text: str) -> str:
        if not text:
            return text

        if self.bot_name:
            bot_lower = self.bot_name.lower()
            text_lower = text.lower()
            prefix = "@" + bot_lower
            if text_lower.startswith(prefix):
                return text[len(prefix):].strip()

        text = re.sub(r'^\[mention:[^\]]*\]\s*', '', text, flags=re.IGNORECASE).strip()
        return text

    def cache_user_info(self, user_id: str, info: dict) -> None:
        self._user_info_cache[user_id] = (info, asyncio.get_event_loop().time())

    def get_cached_user_info(self, user_id: str) -> Optional[dict]:
        if user_id in self._user_info_cache:
            info, timestamp = self._user_info_cache[user_id]
            if asyncio.get_event_loop().time() - timestamp < self._cache_ttl:
                return info
            del self._user_info_cache[user_id]
        return None

    def cache_group_info(self, group_id: str, info: dict) -> None:
        self._group_info_cache[group_id] = (info, asyncio.get_event_loop().time())

    def get_cached_group_info(self, group_id: str) -> Optional[dict]:
        if group_id in self._group_info_cache:
            info, timestamp = self._group_info_cache[group_id]
            if asyncio.get_event_loop().time() - timestamp < self._cache_ttl:
                return info
            del self._group_info_cache[group_id]
        return None

    def get_status(self) -> dict:
        return {
            "dm_policy": self.dm_policy,
            "group_policy": self.group_policy,
            "require_mention": self.require_mention,
            "allowlisted_users": len(self.allowlisted_users),
            "denylisted_users": len(self.denylisted_users),
            "allowlisted_groups": len(self.allowlisted_groups),
            "denylisted_groups": len(self.denylisted_groups),
            "mention_patterns": len(self.mention_patterns),
            "bot_name": self.bot_name,
            "bot_user_id": self.bot_user_id,
            "cache_stats": {
                "user_info_entries": len(self._user_info_cache),
                "group_info_entries": len(self._group_info_cache),
            },
        }


class ZaloAdapter(BasePlatformAdapter):
    """
    Zalo platform adapter using a Node.js subprocess worker.
    """

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.ZALO)
        self.worker: Optional[subprocess.Popen] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.request_id = 0
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.loop = asyncio.get_event_loop()
        
        # Path to the worker
        self.worker_dir = Path(__file__).parent / "zalo" / "worker"
        self.worker_script = self.worker_dir / "dist" / "index.js"

        # Access control
        self.ac = ZaloAccessControl(config)

        # Supervision / auto-restart
        self._supervisor_task: Optional[asyncio.Task] = None
        self._restart_count = 0
        self._max_restarts = 10
        self._restart_backoff = 5  # seconds, doubles each restart
        self._connected_time = 0.0

        # Metrics
        self._metrics = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "restarts": 0,
            "started_at": None,
        }

    async def connect(self) -> bool:
        """Start the Node.js worker subprocess."""
        if not self.worker_script.exists():
            logger.error(f"[Zalo] Worker script not found at {self.worker_script}. Did you run 'npm run build'?")
            return False

        logger.info(f"[Zalo] Starting worker process: node {self.worker_script}")

        # Pass HERMES_HOME + Zalo access control env vars to worker
        from hermes_constants import get_hermes_home
        worker_env = os.environ.copy()
        worker_env["HERMES_HOME"] = str(get_hermes_home())

        # Pass access control config from .env or config.yaml extra
        ac_vars = {
            "ZALO_DM_POLICY": self.config.extra.get("dm_policy"),
            "ZALO_GROUP_POLICY": self.config.extra.get("group_policy"),
            "ZALO_REQUIRE_MENTION": str(self.config.extra.get("require_mention")).lower() if self.config.extra.get("require_mention") is not None else None,
            "ZALO_ALLOWLISTED_USERS": self._format_id_list("allowlisted_users"),
            "ZALO_DENYLISTED_USERS": self._format_id_list("denylisted_users"),
            "ZALO_ALLOWLISTED_GROUPS": self._format_id_list("allowlisted_groups"),
            "ZALO_DENYLISTED_GROUPS": self._format_id_list("denylisted_groups"),
            "ZALO_BOT_NAME": self.config.extra.get("bot_name"),
            "ZALO_BOT_USER_ID": self.config.extra.get("bot_user_id"),
        }
        for key, val in ac_vars.items():
            if val:
                worker_env[key] = val

        try:
            self.worker = subprocess.Popen(
                ["node", str(self.worker_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(self.worker_dir),
                env=worker_env
            )
            
            # Thread to read stdout
            self.worker_thread = threading.Thread(target=self._read_worker_stdout, daemon=True)
            self.worker_thread.start()
            
            # Thread to read stderr (for logging)
            threading.Thread(target=self._read_worker_stderr, daemon=True).start()
            
            logger.info("[Zalo] Worker process started successfully.")
            self._mark_connected()
            self._connected_time = asyncio.get_event_loop().time()
            self._metrics["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Start supervisor task
            if not self._supervisor_task or self._supervisor_task.done():
                self._supervisor_task = asyncio.create_task(self._supervise_worker())
            
            return True
        except Exception as e:
            logger.error(f"[Zalo] Failed to start worker: {e}")
            return False

    def _format_id_list(self, key: str) -> str:
        """Format an ID set as comma-separated string for env var."""
        # Read from config.extra first (works in Docker), fallback to self.ac
        val = self.config.extra.get(key)
        if isinstance(val, list):
            return ",".join(str(x).strip() for x in val if str(x).strip())
        if isinstance(val, str) and val.strip():
            return val.strip()
        id_set = getattr(self.ac, f"{key}", set())
        if isinstance(id_set, set):
            return ",".join(sorted(id_set)) if id_set else ""
        return ""

    async def disconnect(self):
        """Stop the worker subprocess."""
        # Cancel supervisor
        if self._supervisor_task and not self._supervisor_task.done():
            self._supervisor_task.cancel()
            try:
                await self._supervisor_task
            except asyncio.CancelledError:
                pass
        
        if self.worker:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.worker.kill()
            self.worker = None
        self._mark_disconnected()
        logger.info("[Zalo] Worker process stopped.")

    async def _supervise_worker(self):
        """Monitor worker health and auto-restart on crash.
        
        Uses exponential backoff: 5s -> 10s -> 20s -> ... -> 300s cap.
        Stops restarting after _max_restarts to avoid infinite loops.
        """
        backoff = self._restart_backoff
        max_backoff = 300  # 5 minutes
        
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            if self.worker is None:
                continue  # Intentionally stopped
            
            if self.worker.poll() is None:
                continue  # Still running
            
            # Worker has died
            exit_code = self.worker.returncode
            logger.error(f"[Zalo] Worker died with exit code {exit_code}")
            self._metrics["errors"] += 1
            
            # Check if we've exceeded max restarts
            if self._restart_count >= self._max_restarts:
                logger.error(
                    f"[Zalo] Max restarts ({self._max_restarts}) reached. "
                    f"Worker will not be auto-restarted. Manual intervention required."
                )
                self._mark_disconnected()
                return
            
            # Exponential backoff
            logger.info(f"[Zalo] Restarting worker in {backoff}s (attempt {self._restart_count + 1}/{self._max_restarts})")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            
            # Attempt restart
            self._restart_count += 1
            self._metrics["restarts"] = self._restart_count
            logger.info(f"[Zalo] Attempting worker restart #{self._restart_count}")
            
            success = await self.connect()
            if success:
                logger.info(f"[Zalo] Worker restarted successfully (attempt #{self._restart_count})")
                backoff = self._restart_backoff  # Reset backoff on success
            else:
                logger.error(f"[Zalo] Worker restart failed (attempt #{self._restart_count})")

    def get_metrics(self) -> dict:
        """Return adapter metrics for monitoring."""
        uptime = 0.0
        if self._connected_time > 0:
            uptime = asyncio.get_event_loop().time() - self._connected_time
        
        return {
            "platform": "zalo",
            "connected": self.worker is not None and self.worker.poll() is None,
            "uptime_seconds": round(uptime, 1),
            "restart_count": self._restart_count,
            "messages_sent": self._metrics["messages_sent"],
            "messages_received": self._metrics["messages_received"],
            "errors": self._metrics["errors"],
            "started_at": self._metrics["started_at"],
            "pending_requests": len(self.pending_requests),
        }

    def record_message_sent(self):
        """Track a sent message for metrics."""
        self._metrics["messages_sent"] += 1

    def record_message_received(self):
        """Track a received message for metrics."""
        self._metrics["messages_received"] += 1

    def _read_worker_stdout(self):
        """Continuously read lines from the worker's stdout."""
        while self.worker and self.worker.stdout:
            line = self.worker.stdout.readline()
            if not line:
                break
            
            try:
                data = json.loads(line)
                if "id" in data:
                    # This is a response to a request
                    self.loop.call_soon_threadsafe(self._handle_response, data)
                elif data.get("type") == "event":
                    # This is an unsolicited event (message, qr_code, etc.)
                    self.loop.call_soon_threadsafe(self._handle_event, data["data"])
            except json.JSONDecodeError:
                logger.debug(f"[Zalo Worker Output] {line.strip()}")
            except Exception as e:
                logger.error(f"[Zalo] Error parsing worker output: {e}")

    def _read_worker_stderr(self):
        """Log worker's stderr to Python logger."""
        while self.worker and self.worker.stderr:
            try:
                line = self.worker.stderr.readline()
            except (UnicodeDecodeError, ValueError):
                continue
            if not line:
                break
            stripped = line.strip()
            logger.info(f"[Zalo Worker] {stripped}")
            # Print key lifecycle events to terminal (INFO logs go to file only)
            if any(kw in stripped for kw in ("Login successful", "Listening for Zalo", "credentials", "Fatal error", "No credentials")):
                print(f"[Zalo] {stripped}", flush=True)

    def _handle_response(self, data: dict):
        req_id = str(data.get("id"))
        future = self.pending_requests.pop(req_id, None)
        if future:
            if "error" in data:
                future.set_exception(RuntimeError(data["error"]))
            else:
                future.set_result(data.get("result"))

    def _handle_event(self, event: dict):
        event_type = event.get("type")
        payload = event.get("payload")
        
        if event_type == "message":
            self._on_message(payload)
        elif event_type == "qr_code":
            self._on_qr_code(payload)
        elif event_type == "media_received":
            self._on_media_received(payload)
        elif event_type == "session_alert":
            self._on_session_alert(payload)

    def _on_message(self, data: dict):
        """Handle incoming message from Zalo."""
        try:
            # Log raw data to understand actual field names from zca-js
            logger.debug(f"[Zalo] Raw message data keys: {list(data.keys())}")
            logger.debug(f"[Zalo] Raw message data: {json.dumps(data, ensure_ascii=False, default=str)[:500]}")

            # Use safe fallbacks for all fields
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

            # Access control check (defense-in-depth layer)
            allowed, reason = self.ac.check_access(str(from_id), str(chat_id), is_group, text)
            if not allowed:
                logger.debug(f"[Zalo AC] Blocked message from {from_id} in {'group' if is_group else 'DM'} {chat_id}: {reason}")
                return

            # Strip mention prefix for cleaner processing
            text = self.ac.strip_mention_prefix(text)

            source = self.build_source(
                chat_id=str(chat_id),
                chat_type="group" if is_group else "dm",
                user_id=str(from_id),
                user_name=from_name,
            )

            event = MessageEvent(
                text=text,
                message_type=MessageType.TEXT,
                source=source,
                raw_message=data.get("raw") or data,
                message_id=data.get("message_id") or data.get("msg_id") or data.get("messageId"),
            )
            logger.info(f"[Zalo] Inbound message from {event.source.user_id}: {event.text[:80]}")
            self.record_message_received()
            print(f"[Zalo] Message from {event.source.user_name}: {event.text[:60]}", flush=True)

            # Auto-detect and echo back image URLs from user messages
            image_urls = self._extract_image_urls(text)
            if image_urls:
                for img_url in image_urls:
                    asyncio.create_task(self._send_image_async(chat_id, img_url, is_group))

            # Send typing indicator before processing
            asyncio.create_task(self._send_typing_async(chat_id, is_group))

            # Dispatch via BasePlatformAdapter standard pipeline
            asyncio.create_task(self.handle_message(event))
        except Exception as e:
            logger.error(f"[Zalo] Error handling message: {e}", exc_info=True)
            logger.debug(f"[Zalo] Message data was: {data}")

    def _on_qr_code(self, data: dict):
        """Handle QR code event."""
        qr_data = data.get("qr_data")
        if not qr_data:
            return

        from hermes_constants import get_hermes_home
        import base64
        import time

        data_dir = Path(get_hermes_home()) / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        qr_path = data_dir / "zalo_qr.png"

        # --- Cleanup old QR file before saving new one ---
        if qr_path.exists():
            try:
                qr_path.unlink()
                logger.debug("[Zalo] Old QR file removed.")
            except Exception:
                # File locked or permission issue — save with timestamp suffix instead
                ts = int(time.time())
                qr_path = data_dir / f"zalo_qr_{ts}.png"
                logger.debug(f"[Zalo] Could not remove old QR, using new name: {qr_path.name}")

        try:
            image_data = None
            if isinstance(qr_data, dict) and qr_data.get("image"):
                image_data = base64.b64decode(qr_data["image"])
            elif isinstance(qr_data, str):
                # Fallback if qr_data is just a base64 string
                image_data = base64.b64decode(qr_data)

            if image_data:
                qr_path.write_bytes(image_data)
                msg = f"[Zalo] QR code saved to {qr_path}. Please scan to login."
                logger.info(msg)
                print(f"\n📱 {msg}", flush=True)

            # Also log the URL if available for convenience
            if isinstance(qr_data, dict) and qr_data.get("url"):
                logger.info(f"[Zalo] QR URL: {qr_data['url']}")

        except Exception as e:
            logger.error(f"[Zalo] Failed to save QR code: {e}")

    def _on_media_received(self, data: dict):
        """Handle received media event."""
        try:
            media_type = data.get("type", "unknown")
            url = data.get("url", "")
            local_path = data.get("local_path", "")
            thread_id = data.get("thread_id", "")
            
            logger.info(f"[Zalo] Received {media_type} media: {url[:80]} → {local_path}")
            print(f"[Zalo] 📎 Received {media_type}: {local_path}", flush=True)
            
            # Cache the media locally for potential use by the agent
            if local_path and Path(local_path).exists():
                self.cache_image_from_bytes(
                    Path(local_path).read_bytes(),
                    filename=f"{media_type}_{thread_id}_{Path(local_path).name}"
                )
        except Exception as e:
            logger.error(f"[Zalo] Error handling received media: {e}", exc_info=True)

    def _on_session_alert(self, data: dict):
        """Handle session health alert from worker."""
        level = data.get("level", "info")
        message = data.get("message", "")
        requires_qr = data.get("requires_qr", False)

        if level == "critical":
            logger.error(f"[Zalo Session] CRITICAL: {message}")
            print(f"\n[Zalo] SESSION EXPIRED: {message}", flush=True)
            print(f"[Zalo] Please scan the new QR code to re-login.", flush=True)
        elif level == "warning":
            logger.warning(f"[Zalo Session] WARNING: {message}")
            print(f"[Zalo] Session warning: {message}", flush=True)
        else:
            logger.info(f"[Zalo Session] {message}")

    async def _call_worker(self, method: str, params: dict) -> Any:
        """Call a method on the Node.js worker and wait for response."""
        if not self.worker or not self.worker.stdin:
            raise RuntimeError("Zalo worker not running")

        self.request_id += 1
        req_id = str(self.request_id)
        future = self.loop.create_future()
        self.pending_requests[req_id] = future

        request = {
            "id": req_id,
            "method": method,
            "params": params
        }
        
        self.worker.stdin.write(json.dumps(request) + "\n")
        self.worker.stdin.flush()
        
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            raise RuntimeError(f"Zalo worker request {req_id} timed out")

    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """Get information about a Zalo chat, using cache when available."""
        # Check cache first
        cached = self.ac.get_cached_group_info(chat_id)
        if cached:
            return cached

        try:
            # Try to get from worker
            result = await self._call_worker("zalo_action", {
                "action": "get-group-info",
                "groupId": chat_id,
            })
            if result and result.get("success"):
                info = result.get("data", {})
                self.ac.cache_group_info(chat_id, info)
                return {
                    "name": info.get("name", f"Zalo Chat {chat_id}"),
                    "type": "group",
                    "member_count": info.get("memberCount", 0),
                }
        except Exception as e:
            logger.debug(f"[Zalo] Failed to get chat info from worker: {e}")

        # Fallback to basic info
        return {
            "name": f"Zalo Chat {chat_id}",
            "type": "dm" if not chat_id.startswith("g") else "group"
        }

    async def update_access_control(self, config: dict) -> dict:
        """Update access control configuration at runtime."""
        # Update Python-side config
        if "dm_policy" in config:
            self.ac.dm_policy = config["dm_policy"]
        if "group_policy" in config:
            self.ac.group_policy = config["group_policy"]
        if "require_mention" in config:
            self.ac.require_mention = bool(config["require_mention"])
        if "allowlisted_users" in config:
            self.ac.allowlisted_users = set(str(x).strip() for x in config["allowlisted_users"] if str(x).strip())
        if "denylisted_users" in config:
            self.ac.denylisted_users = set(str(x).strip() for x in config["denylisted_users"] if str(x).strip())
        if "allowlisted_groups" in config:
            self.ac.allowlisted_groups = set(str(x).strip() for x in config["allowlisted_groups"] if str(x).strip())
        if "denylisted_groups" in config:
            self.ac.denylisted_groups = set(str(x).strip() for x in config["denylisted_groups"] if str(x).strip())
        if "bot_name" in config:
            self.ac.bot_name = config["bot_name"]
        if "bot_user_id" in config:
            self.ac.bot_user_id = config["bot_user_id"]

        # Sync to worker
        try:
            worker_result = await self._call_worker("update_access_control", config)
            logger.info("[Zalo] Access control config updated in worker")
        except Exception as e:
            logger.warning(f"[Zalo] Failed to sync AC config to worker: {e}")

        return self.ac.get_status()

    async def get_access_control_status(self) -> dict:
        """Get current access control status."""
        python_status = self.ac.get_status()
        try:
            worker_status = await self._call_worker("get_access_control_status", {})
            python_status["worker"] = worker_status
        except Exception as e:
            python_status["worker_error"] = str(e)
        return python_status

    async def clear_access_control_caches(self) -> dict:
        """Clear all access control caches."""
        self.ac._user_info_cache.clear()
        self.ac._group_info_cache.clear()
        try:
            await self._call_worker("clear_access_control_caches", {})
        except Exception as e:
            logger.warning(f"[Zalo] Failed to clear worker caches: {e}")
        return {"cleared": True}

    async def get_session_health(self) -> dict:
        """Get current session health status."""
        try:
            return await self._call_worker("get_session_health", {})
        except Exception as e:
            logger.warning(f"[Zalo] Failed to get session health: {e}")
            return {"status": "unknown", "error": str(e)}

    async def trigger_qr_login(self) -> dict:
        """Manually trigger QR re-login."""
        try:
            return await self._call_worker("trigger_qr_login", {})
        except Exception as e:
            logger.error(f"[Zalo] Failed to trigger QR login: {e}")
            return {"error": str(e)}

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SendResult:
        """Send a message via Zalo."""
        try:
            # Determine if it's a group
            is_group = False
            if metadata and metadata.get("is_group"):
                is_group = True
            elif chat_id.startswith("g"): # Heuristic for Zalo group IDs
                is_group = True

            # Auto-detect image URLs in content and send as images
            image_urls = self._extract_image_urls(content)
            if image_urls:
                # Send images first
                for img_url in image_urls:
                    await self.send_image(chat_id, image_url=img_url, is_group=is_group)
                # Send remaining text (with image URLs removed)
                clean_text = self._remove_image_urls(content)
                if clean_text.strip():
                    params = {
                        "action": "send",
                        "threadId": chat_id,
                        "message": clean_text.strip(),
                        "isGroup": is_group
                    }
                    if reply_to:
                        params["replyTo"] = reply_to
                    result = await self._call_worker("zalo_action", params)
                    return SendResult(success=True, message_id=result.get("msgId") if result else None)
                return SendResult(success=True)
            else:
                params = {
                    "action": "send",
                    "threadId": chat_id,
                    "message": content,
                    "isGroup": is_group
                }
                if reply_to:
                    params["replyTo"] = reply_to

                result = await self._call_worker("zalo_action", params)
                
                self.record_message_sent()
                return SendResult(success=True, message_id=result.get("msgId") if result else None)
        except Exception as e:
            logger.error(f"[Zalo] Failed to send message: {e}")
            self._metrics["errors"] += 1
            return SendResult(success=False, error=str(e))

    def _extract_image_urls(self, text: str) -> list:
        """Extract image URLs from text content."""
        urls = []
        
        # Match markdown images: ![alt](url)
        md_pattern = re.compile(r'!\[[^\]]*\]\((https?://[^\s)]+\.(?:jpg|jpeg|png|gif|webp|avif|bmp)(?:\?[^\s)]*)?)\)', re.IGNORECASE)
        for m in md_pattern.finditer(text):
            urls.append(m.group(1))
        
        # Match plain image URLs (standalone URLs ending in image extensions)
        plain_pattern = re.compile(r'(https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|avif|bmp)(?:\?[^\s]*)?)', re.IGNORECASE)
        for m in plain_pattern.finditer(text):
            url = m.group(1)
            if url not in urls:
                urls.append(url)
        
        return urls

    def _remove_image_urls(self, text: str) -> str:
        """Remove image URLs from text, leaving surrounding text."""
        # Remove markdown images
        text = re.sub(r'!\[[^\]]*\]\(https?://[^\s)]+\)', '', text)
        # Remove standalone image URLs
        text = re.sub(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|avif|bmp)(?:\?[^\s]*)?', '', text, flags=re.IGNORECASE)
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    async def _send_image_async(self, chat_id: str, url: str, is_group: bool = False) -> None:
        """Async wrapper to send an image URL back to the user."""
        try:
            logger.info(f"[Zalo] Auto-echoing image URL: {url[:80]}...")
            print(f"[Zalo] 🖼️ Sending image: {url[:60]}...", flush=True)
            result = await self.send_image(chat_id, image_url=url, is_group=is_group)
            if result.success:
                logger.info(f"[Zalo] Image sent successfully: {url[:80]}")
            else:
                logger.warning(f"[Zalo] Failed to send image: {result.error}")
        except Exception as e:
            logger.error(f"[Zalo] Error sending auto-echoed image: {e}", exc_info=True)

    async def _send_typing_async(self, chat_id: str, is_group: bool = False) -> None:
        """Send typing indicator to user."""
        try:
            await self._call_worker("zalo_action", {
                "action": "send-typing",
                "threadId": chat_id,
                "isGroup": is_group,
            })
        except Exception as e:
            logger.debug(f"[Zalo] Failed to send typing indicator: {e}")

    async def send_image(
        self,
        chat_id: str,
        image_url: Optional[str] = None,
        image_path: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SendResult:
        """Send an image via Zalo."""
        try:
            is_group = self._is_group_chat(chat_id, metadata)
            
            params = {
                "action": "send-image",
                "threadId": chat_id,
                "isGroup": is_group,
            }
            if image_url:
                params["url"] = image_url
            if image_path:
                params["filePath"] = image_path
            if caption:
                params["message"] = caption
            if reply_to:
                params["replyTo"] = reply_to

            result = await self._call_worker("zalo_action", params)
            return SendResult(success=True, message_id=result.get("msgId") if result else None)
        except Exception as e:
            logger.error(f"[Zalo] Failed to send image: {e}")
            return SendResult(success=False, error=str(e))

    async def send_file(
        self,
        chat_id: str,
        file_url: Optional[str] = None,
        file_path: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SendResult:
        """Send a file via Zalo."""
        try:
            is_group = self._is_group_chat(chat_id, metadata)
            
            params = {
                "action": "send-file",
                "threadId": chat_id,
                "isGroup": is_group,
            }
            if file_url:
                params["url"] = file_url
            if file_path:
                params["filePath"] = file_path
            if caption:
                params["message"] = caption
            if reply_to:
                params["replyTo"] = reply_to

            result = await self._call_worker("zalo_action", params)
            return SendResult(success=True, message_id=result.get("msgId") if result else None)
        except Exception as e:
            logger.error(f"[Zalo] Failed to send file: {e}")
            return SendResult(success=False, error=str(e))

    async def send_video(
        self,
        chat_id: str,
        video_url: Optional[str] = None,
        video_path: Optional[str] = None,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SendResult:
        """Send a video via Zalo."""
        try:
            is_group = self._is_group_chat(chat_id, metadata)
            
            params = {
                "action": "send-video",
                "threadId": chat_id,
                "isGroup": is_group,
            }
            if video_url:
                params["url"] = video_url
            if video_path:
                params["filePath"] = video_path
            if caption:
                params["message"] = caption
            if reply_to:
                params["replyTo"] = reply_to

            result = await self._call_worker("zalo_action", params)
            return SendResult(success=True, message_id=result.get("msgId") if result else None)
        except Exception as e:
            logger.error(f"[Zalo] Failed to send video: {e}")
            return SendResult(success=False, error=str(e))

    async def format_message(self, text: str, format_markdown: bool = True) -> dict:
        """Format a message for Zalo (markdown conversion + truncation)."""
        try:
            result = await self._call_worker("zalo_action", {
                "action": "format-message",
                "text": text,
                "formatMarkdown": format_markdown,
            })
            return result or {"text": text, "truncated": False}
        except Exception as e:
            logger.warning(f"[Zalo] Failed to format message: {e}")
            return {"text": text, "truncated": False}

    async def cache_media(self, url: str, ext: str = "bin") -> dict:
        """Download and cache media from a URL."""
        try:
            result = await self._call_worker("zalo_action", {
                "action": "cache-media",
                "url": url,
                "ext": ext,
            })
            return result or {}
        except Exception as e:
            logger.error(f"[Zalo] Failed to cache media: {e}")
            return {}

    async def get_cached_media(self, url: str, ext: str = "bin") -> Optional[str]:
        """Get the local path of cached media."""
        try:
            result = await self._call_worker("zalo_action", {
                "action": "get-cached-media",
                "url": url,
                "ext": ext,
            })
            if result and result.get("cached"):
                return result.get("localPath")
            return None
        except Exception as e:
            logger.debug(f"[Zalo] Failed to get cached media: {e}")
            return None

    async def cleanup_media_cache(self) -> int:
        """Clean up expired media cache entries."""
        try:
            result = await self._call_worker("zalo_action", {
                "action": "cleanup-media-cache",
            })
            return result.get("cleaned", 0) if result else 0
        except Exception as e:
            logger.warning(f"[Zalo] Failed to cleanup media cache: {e}")
            return 0

    async def clear_media_cache(self) -> bool:
        """Clear all media cache entries."""
        try:
            await self._call_worker("zalo_action", {
                "action": "clear-media-cache",
            })
            return True
        except Exception as e:
            logger.warning(f"[Zalo] Failed to clear media cache: {e}")
            return False

    def cache_image_from_bytes(self, image_data: bytes, filename: str = "image.png") -> str:
        """Cache an image from bytes and return a local path.
        
        This is used by Hermes' built-in image caching system.
        """
        from hermes_constants import get_hermes_home
        
        cache_dir = Path(get_hermes_home()) / "data" / "zalo-media-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a unique filename
        import hashlib
        hash_val = hashlib.md5(image_data).hexdigest()[:12]
        local_path = cache_dir / f"{hash_val}_{filename}"
        
        local_path.write_bytes(image_data)
        logger.debug(f"[Zalo] Cached image to {local_path}")
        return str(local_path)

    def _is_group_chat(self, chat_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if a chat ID represents a group."""
        if metadata and metadata.get("is_group"):
            return True
        # Heuristic: Zalo group IDs often start with 'g' or contain specific patterns
        if chat_id.startswith("g"):
            return True
        return False

def check_zalo_requirements() -> bool:
    """Check if Node.js is available."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except:
        return False
