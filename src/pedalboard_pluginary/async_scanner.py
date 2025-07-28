"""
Async scanner implementation for concurrent plugin scanning.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator, List, Optional, TYPE_CHECKING

from .constants import PLUGIN_LOAD_TIMEOUT
from .models import PluginInfo
from .protocols import ProgressReporter

if TYPE_CHECKING:
    from .protocols import PluginScanner

logger = logging.getLogger(__name__)


class AsyncScannerMixin:
    """Mixin to add async capabilities to scanners.
    
    This mixin expects to be mixed with a class that implements the PluginScanner protocol.
    """
    
    async def scan_plugin_async(self, path: Path) -> Optional[PluginInfo]:
        """Async wrapper for plugin scanning with timeout.
        
        Args:
            path: Path to the plugin file.
            
        Returns:
            PluginInfo object if successful, None if scanning failed.
        """
        try:
            # Use asyncio.to_thread for CPU-bound plugin loading
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, self.scan_plugin, path),  # type: ignore[attr-defined]
                timeout=PLUGIN_LOAD_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"Plugin {path} timed out during async scan")
            return None
        except Exception as e:
            logger.error(f"Error in async plugin scan for {path}: {e}")
            return None
    
    async def scan_plugins_batch(
        self, 
        paths: List[Path], 
        max_concurrent: int = 10,
        progress_reporter: Optional[ProgressReporter] = None
    ) -> AsyncIterator[PluginInfo]:
        """Scan multiple plugins concurrently with backpressure control.
        
        Args:
            paths: List of plugin paths to scan.
            max_concurrent: Maximum number of concurrent scans.
            progress_reporter: Optional progress reporter.
            
        Yields:
            PluginInfo objects for successfully scanned plugins.
        """
        if not paths:
            return
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_with_semaphore(path: Path) -> Optional[PluginInfo]:
            async with semaphore:
                return await self.scan_plugin_async(path)
        
        # Create tasks for all paths
        tasks = [scan_with_semaphore(path) for path in paths]
        
        # Start progress tracking
        if progress_reporter:
            progress_reporter.start(len(tasks), f"Scanning {len(tasks)} plugins")
        
        completed = 0
        successful = 0
        
        # Process tasks as they complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            completed += 1
            
            if result:
                successful += 1
                yield result
            
            # Update progress
            if progress_reporter:
                message = f"Completed {completed}/{len(tasks)} ({successful} successful)"
                progress_reporter.update(1, message)
        
        # Finish progress tracking
        if progress_reporter:
            progress_reporter.finish(f"Scan completed: {successful}/{len(tasks)} plugins")
    
    async def scan_directory_async(
        self, 
        directory: Path,
        max_concurrent: int = 10,
        progress_reporter: Optional[ProgressReporter] = None
    ) -> List[PluginInfo]:
        """Async scan of an entire directory.
        
        Args:
            directory: Directory to scan for plugins.
            max_concurrent: Maximum number of concurrent scans.
            progress_reporter: Optional progress reporter.
            
        Returns:
            List of successfully scanned plugins.
        """
        # Find plugin files
        plugin_files = self.find_plugin_files([directory])  # type: ignore[attr-defined]
        
        # Scan plugins concurrently
        plugins = []
        async for plugin in self.scan_plugins_batch(
            plugin_files, 
            max_concurrent=max_concurrent,
            progress_reporter=progress_reporter
        ):
            plugins.append(plugin)
        
        return plugins


