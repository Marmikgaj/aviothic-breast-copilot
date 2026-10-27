"""Thread-safe in-memory session manager for ephemeral patient contexts.

Complies with PRD §7 and ADR-002:
- Strictly ephemeral in-memory storage (no database leakage across patients).
- Automatic session cleanup after idle timeout (default 60 minutes).
- Zero PHI persistence to disk.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from src.context.schemas import ConversationTurn, PatientContext, ProcessedReport
from src.core.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Thread-safe manager for ephemeral in-memory patient sessions."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        """Initialize session manager.

        Args:
            default_ttl_seconds: Session time-to-live after last activity in seconds (default: 1 hour).
        """
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: dict[str, PatientContext] = {}
        self._lock = threading.RLock()

    def create_session(self, session_id: str | None = None, metadata: dict[str, str] | None = None) -> PatientContext:
        """Create a new ephemeral patient context session.

        Args:
            session_id: Optional explicit session ID; if omitted, an ID is generated.
            metadata: Optional session metadata dict.

        Returns:
            The created PatientContext instance.
        """
        with self._lock:
            context = PatientContext(
                metadata=metadata or {},
            )
            if session_id:
                context.session_id = session_id

            self._sessions[context.session_id] = context
            logger.info("Created ephemeral patient session", session_id=context.session_id)
            return context

    def get_session(self, session_id: str) -> PatientContext | None:
        """Retrieve a session by ID if it exists and has not expired.

        Args:
            session_id: The session ID to look up.

        Returns:
            PatientContext if active, None if not found or expired.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            # Check expiration
            now = datetime.now(UTC)
            elapsed = (now - session.updated_at).total_seconds()
            if elapsed > self.default_ttl_seconds:
                logger.info("Session expired due to inactivity", session_id=session_id, elapsed_sec=elapsed)
                del self._sessions[session_id]
                return None

            return session

    def get_or_create_session(self, session_id: str) -> PatientContext:
        """Retrieve an existing session or create a new one with the given ID.

        Args:
            session_id: Session ID to lookup or create.

        Returns:
            Existing or newly created PatientContext.
        """
        with self._lock:
            session = self.get_session(session_id)
            if session:
                return session
            return self.create_session(session_id=session_id)

    def add_report(self, session_id: str, report: ProcessedReport) -> PatientContext:
        """Add a processed clinical report to a patient session.

        If a report with the same report_id already exists in the session,
        it is replaced with the updated version.

        Args:
            session_id: The session to attach the report to.
            report: The processed clinical report.

        Returns:
            Updated PatientContext.

        Raises:
            KeyError: If session_id does not exist or has expired.
        """
        with self._lock:
            session = self.get_session(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found or has expired.")

            # Replace existing or append new
            existing_idx = next(
                (i for i, r in enumerate(session.reports) if r.report_id == report.report_id),
                None,
            )
            if existing_idx is not None:
                session.reports[existing_idx] = report
                logger.info("Updated existing report in session", session_id=session_id, report_id=report.report_id)
            else:
                session.reports.append(report)
                logger.info(
                    "Added report to session",
                    session_id=session_id,
                    report_id=report.report_id,
                    modality=report.modality.value,
                    total_reports=len(session.reports),
                )

            session.touch()
            return session

    def add_turn(self, session_id: str, turn: ConversationTurn) -> PatientContext:
        """Add a conversation turn to the session history.

        Args:
            session_id: The session ID.
            turn: ConversationTurn to append.

        Returns:
            Updated PatientContext.

        Raises:
            KeyError: If session_id does not exist or has expired.
        """
        with self._lock:
            session = self.get_session(session_id)
            if not session:
                raise KeyError(f"Session '{session_id}' not found or has expired.")

            session.history.append(turn)
            session.touch()
            logger.debug(
                "Added conversation turn",
                session_id=session_id,
                turn_id=turn.turn_id,
                role=turn.role.value,
                turn_count=len(session.history),
            )
            return session

    def delete_session(self, session_id: str) -> bool:
        """Explicitly purge a patient session from memory.

        Args:
            session_id: Session ID to remove.

        Returns:
            True if removed, False if not present.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info("Purged patient session from memory", session_id=session_id)
                return True
            return False

    def clear_expired_sessions(self, max_idle_seconds: int | None = None) -> int:
        """Evict all sessions that have exceeded the idle timeout.

        Args:
            max_idle_seconds: Max idle seconds before eviction (defaults to default_ttl_seconds).

        Returns:
            Number of evicted sessions.
        """
        ttl = max_idle_seconds or self.default_ttl_seconds
        now = datetime.now(UTC)
        evicted = 0

        with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items() if (now - session.updated_at).total_seconds() > ttl
            ]
            for sid in expired_ids:
                del self._sessions[sid]
                evicted += 1

        if evicted > 0:
            logger.info("Evicted expired sessions", count=evicted)
        return evicted

    def active_session_count(self) -> int:
        """Return the number of currently active in-memory sessions."""
        with self._lock:
            return len(self._sessions)

    def clear_all(self) -> None:
        """Purge all sessions (useful for test isolation)."""
        with self._lock:
            self._sessions.clear()


# Module-level singleton instance
_session_manager: SessionManager | None = None
_manager_lock = threading.Lock()


def get_session_manager() -> SessionManager:
    """Return the global SessionManager singleton."""
    global _session_manager
    with _manager_lock:
        if _session_manager is None:
            _session_manager = SessionManager()
        return _session_manager
