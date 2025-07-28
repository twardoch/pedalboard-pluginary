"""
Timeout handling for plugin operations.
"""

import asyncio
import concurrent.futures
import functools
import logging
from typing import Any, Awaitable, Callable, TypeVar, Union

from .constants import PLUGIN_LOAD_TIMEOUT

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class TimeoutError(Exception):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout: float):
        super().__init__(message)
        self.timeout = timeout


def sync_timeout(func: Callable[..., T], timeout: float, *args: Any, **kwargs: Any) -> T:
    """Execute synchronous function with timeout using ThreadPoolExecutor.
    
    Args:
        func: Function to execute.
        timeout: Timeout in seconds.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        Function result.
        
    Raises:
        TimeoutError: If function execution exceeds timeout.
        Exception: Any exception raised by the function.
    """
    logger.debug(f"Executing {func.__name__} with {timeout}s timeout")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except concurrent.futures.TimeoutError:
            logger.warning(f"{func.__name__} timed out after {timeout}s")
            # Cancel the future to prevent resource leaks
            future.cancel()
            raise TimeoutError(f"{func.__name__} timed out after {timeout}s", timeout)
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise


async def async_timeout(coro_func: Callable[..., Awaitable[T]], timeout: float, *args: Any, **kwargs: Any) -> T:
    """Execute coroutine function with timeout.
    
    Args:
        coro_func: Coroutine function to execute.
        timeout: Timeout in seconds.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        Function result.
        
    Raises:
        TimeoutError: If function execution exceeds timeout.
        Exception: Any exception raised by the function.
    """
    logger.debug(f"Executing {coro_func.__name__} with {timeout}s timeout")
    
    try:
        result: T = await asyncio.wait_for(coro_func(*args, **kwargs), timeout=timeout)
        logger.debug(f"{coro_func.__name__} completed successfully")
        return result
    except asyncio.TimeoutError:
        logger.warning(f"{coro_func.__name__} timed out after {timeout}s")
        raise TimeoutError(f"{coro_func.__name__} timed out after {timeout}s", timeout)
    except Exception as e:
        logger.error(f"{coro_func.__name__} failed: {e}")
        raise


def with_sync_timeout(timeout: float = PLUGIN_LOAD_TIMEOUT) -> Callable[[F], F]:
    """Decorator that adds timeout to synchronous functions.
    
    Args:
        timeout: Timeout in seconds.
        
    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return sync_timeout(func, timeout, *args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


def with_async_timeout(timeout: float = PLUGIN_LOAD_TIMEOUT) -> Callable[[F], F]:
    """Decorator that adds timeout to async functions.
    
    Args:
        timeout: Timeout in seconds.
        
    Returns:
        Decorated function.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await async_timeout(func, timeout, *args, **kwargs)
        return async_wrapper  # type: ignore[return-value]
    return decorator