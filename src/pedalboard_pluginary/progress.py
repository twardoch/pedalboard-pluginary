"""
Progress reporting implementations.
"""

import logging
from typing import Any, Callable, Optional

from tqdm import tqdm

from .protocols import ProgressReporter

logger = logging.getLogger(__name__)


class TqdmProgress(ProgressReporter):
    """Progress reporter using tqdm progress bars."""
    
    def __init__(self) -> None:
        """Initialize the progress reporter."""
        self._pbar: Optional[tqdm[Any]] = None
        self._total: int = 0
        self._current: int = 0
        self._description: str = ""
    
    def start(self, total: int, description: str = "") -> None:
        """Start progress tracking.
        
        Args:
            total: Total number of items to process.
            description: Optional description of the operation.
        """
        self._total = total
        self._current = 0
        self._description = description
        self._pbar = tqdm(total=total, desc=description)
    
    def update(self, amount: int = 1, message: Optional[str] = None) -> None:
        """Update progress.
        
        Args:
            amount: Number of items completed (default: 1).
            message: Optional status message.
        """
        if self._pbar is None:
            return
        
        self._current += amount
        self._pbar.update(amount)
        
        if message and hasattr(self._pbar, 'set_description'):
            # Update description with message
            self._pbar.set_description(f"{self._description} - {message}")
    
    def finish(self, message: Optional[str] = None) -> None:
        """Finish progress tracking.
        
        Args:
            message: Optional completion message.
        """
        if self._pbar is None:
            return
        
        # Ensure we reach 100%
        if self._current < self._total:
            self._pbar.update(self._total - self._current)
        
        if message and hasattr(self._pbar, 'set_description'):
            # Update description with message
            self._pbar.set_description(f"{self._description} - {message}")
        
        self._pbar.close()
        self._pbar = None


class NoOpProgress(ProgressReporter):
    """No-operation progress reporter for quiet mode."""
    
    def start(self, total: int, description: str = "") -> None:
        """Start progress tracking (no-op)."""
    
    def update(self, amount: int = 1, message: Optional[str] = None) -> None:
        """Update progress (no-op)."""
    
    def finish(self, message: Optional[str] = None) -> None:
        """Finish progress tracking (no-op)."""


class LogProgress(ProgressReporter):
    """Progress reporter that logs to standard logging."""
    
    def __init__(self, log_level: int = logging.INFO):
        """Initialize the progress reporter.
        
        Args:
            log_level: Logging level to use for progress messages.
        """
        self._log_level = log_level
        self._total: int = 0
        self._current: int = 0
        self._description: str = ""
    
    def start(self, total: int, description: str = "") -> None:
        """Start progress tracking.
        
        Args:
            total: Total number of items to process.
            description: Optional description of the operation.
        """
        self._total = total
        self._current = 0
        self._description = description
        
        logger.log(
            self._log_level,
            f"Starting: {description} (0/{total})"
        )
    
    def update(self, amount: int = 1, message: Optional[str] = None) -> None:
        """Update progress.
        
        Args:
            amount: Number of items completed (default: 1).
            message: Optional status message.
        """
        self._current += amount
        
        progress_pct = (self._current / self._total * 100) if self._total > 0 else 0
        status = f"{self._description}: {self._current}/{self._total} ({progress_pct:.1f}%)"
        
        if message:
            status += f" - {message}"
        
        logger.log(self._log_level, status)
    
    def finish(self, message: Optional[str] = None) -> None:
        """Finish progress tracking.
        
        Args:
            message: Optional completion message.
        """
        status = f"Completed: {self._description}"
        if message:
            status += f" - {message}"
        
        logger.log(self._log_level, status)


class CallbackProgress(ProgressReporter):
    """Progress reporter that calls user-provided callbacks."""
    
    def __init__(
        self,
        on_start: Optional[Callable[[int, str], None]] = None,
        on_update: Optional[Callable[[int, int, Optional[str]], None]] = None,
        on_finish: Optional[Callable[[Optional[str]], None]] = None,
    ):
        """Initialize the progress reporter with callbacks.
        
        Args:
            on_start: Callback for start(total, description).
            on_update: Callback for update(current, total, message).
            on_finish: Callback for finish(message).
        """
        self._on_start = on_start
        self._on_update = on_update
        self._on_finish = on_finish
        self._total: int = 0
        self._current: int = 0
    
    def start(self, total: int, description: str = "") -> None:
        """Start progress tracking.
        
        Args:
            total: Total number of items to process.
            description: Optional description of the operation.
        """
        self._total = total
        self._current = 0
        
        if self._on_start:
            self._on_start(total, description)
    
    def update(self, amount: int = 1, message: Optional[str] = None) -> None:
        """Update progress.
        
        Args:
            amount: Number of items completed (default: 1).
            message: Optional status message.
        """
        self._current += amount
        
        if self._on_update:
            self._on_update(self._current, self._total, message)
    
    def finish(self, message: Optional[str] = None) -> None:
        """Finish progress tracking.
        
        Args:
            message: Optional completion message.
        """
        if self._on_finish:
            self._on_finish(message)