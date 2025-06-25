"""
Retry logic for handling transient failures.
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from .constants import MAX_SCAN_RETRIES, SCAN_RETRY_DELAY

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def with_retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]],
    max_attempts: int = MAX_SCAN_RETRIES,
    delay: float = SCAN_RETRY_DELAY,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
) -> Callable[[F], F]:
    """Decorator that retries a function on specified exceptions.
    
    Args:
        exceptions: Exception or tuple of exceptions to catch and retry on.
        max_attempts: Maximum number of attempts (including the first).
        delay: Initial delay between retries in seconds.
        backoff_factor: Factor to multiply delay by after each failure.
        max_delay: Maximum delay between retries in seconds.
        
    Returns:
        Decorated function that will retry on failure.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Optional[Exception] = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise
                        logger.warning(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.info(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    time.sleep(current_delay)
                    
                    # Exponential backoff with max delay
                    current_delay = min(current_delay * backoff_factor, max_delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"{func.__name__} failed with unknown error")
        
        return wrapper  # type: ignore[return-value]
    
    return decorator


def with_timeout(timeout: float) -> Callable[[F], F]:
    """Decorator that adds a timeout to a function.
    
    Note: This is a placeholder for future implementation.
    Proper timeout handling requires different approaches for
    synchronous vs asynchronous functions.
    
    Args:
        timeout: Timeout in seconds.
        
    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # TODO: Implement proper timeout handling
            # For now, just pass through
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore[return-value]
    
    return decorator