
import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
from typing import Dict, List, Optional, Any
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

    async def connect(self) -> bool:
        """Start the Node.js worker subprocess."""
        if not self.worker_script.exists():
            logger.error(f"[Zalo] Worker script not found at {self.worker_script}. Did you run 'npm run build'?")
            return False

        logger.info(f"[Zalo] Starting worker process: node {self.worker_script}")
        
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
                cwd=str(self.worker_dir)
            )
            
            # Thread to read stdout
            self.worker_thread = threading.Thread(target=self._read_worker_stdout, daemon=True)
            self.worker_thread.start()
            
            # Thread to read stderr (for logging)
            threading.Thread(target=self._read_worker_stderr, daemon=True).start()
            
            logger.info("[Zalo] Worker process started successfully.")
            self._mark_connected()
            return True
        except Exception as e:
            logger.error(f"[Zalo] Failed to start worker: {e}")
            return False

    async def disconnect(self):
        """Stop the worker subprocess."""
        if self.worker:
            self.worker.terminate()
            self.worker = None
        self._mark_disconnected()
        logger.info("[Zalo] Worker process stopped.")

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
            print(f"[Zalo] 📨 Message from {event.source.user_name}: {event.text[:60]}", flush=True)
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
        """Get information about a Zalo chat."""
        try:
            # For now, return a basic info or call worker if needed
            # Zalo worker currently has 'friends' and 'groups' actions
            # We can use those to find the chat name
            # For simplicity, returning a placeholder if not found
            return {
                "name": f"Zalo Chat {chat_id}",
                "type": "dm" if not chat_id.startswith("g") else "group" # Simple heuristic
            }
        except Exception as e:
            logger.error(f"[Zalo] Failed to get chat info: {e}")
            return {"name": chat_id, "type": "dm"}

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
            
            params = {
                "action": "send",
                "threadId": chat_id,
                "message": content,
                "isGroup": is_group
            }
            if reply_to:
                params["replyTo"] = reply_to

            result = await self._call_worker("zalo_action", params)
            
            return SendResult(success=True, message_id=result.get("msgId") if result else None)
        except Exception as e:
            logger.error(f"[Zalo] Failed to send message: {e}")
            return SendResult(success=False, error=str(e))

def check_zalo_requirements() -> bool:
    """Check if Node.js is available."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except:
        return False
