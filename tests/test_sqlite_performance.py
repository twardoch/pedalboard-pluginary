"""Performance tests for SQLite cache backend."""

import time
import tempfile
import pytest
from pathlib import Path
from typing import Dict, List

from pedalboard_pluginary.cache.sqlite_backend import SQLiteCacheBackend
from pedalboard_pluginary.cache.json_backend import JSONCacheBackend
from pedalboard_pluginary.models import PluginInfo, PluginParameter


def create_test_plugin(plugin_id: str, name: str, manufacturer: str = "TestMfg") -> PluginInfo:
    """Create a test plugin for benchmarking."""
    plugin_path_obj = Path(f"/test/path/{name.replace(' ', '_')}.plugin")
    return PluginInfo(
        id=plugin_id,
        name=name,
        path=str(plugin_path_obj), # Path should be a string
        filename=plugin_path_obj.name,
        plugin_type="test",
        manufacturer=manufacturer,
        parameters={
            f"param_{i}": PluginParameter(
                name=f"param_{i}",
                value=float(i)
            ) for i in range(10)  # 10 parameters per plugin
        }
    )


def generate_test_plugins(count: int) -> Dict[str, PluginInfo]:
    """Generate test plugins for benchmarking."""
    plugins = {}
    manufacturers = ["TestMfg", "SynthCorp", "AudioTech", "PluginLabs", "MusicSoft"]
    
    for i in range(count):
        plugin_id = f"test_plugin_{i:04d}"
        name = f"Test Plugin {i}"
        manufacturer = manufacturers[i % len(manufacturers)]
        
        plugins[plugin_id] = create_test_plugin(plugin_id, name, manufacturer)
    
    return plugins


class TestSQLitePerformance:
    """Performance tests comparing SQLite vs JSON backends."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sqlite_backend(self, temp_dir):
        """Create SQLite backend for testing."""
        return SQLiteCacheBackend(temp_dir / "test.db")
    
    @pytest.fixture
    def json_backend(self, temp_dir):
        """Create JSON backend for testing."""
        return JSONCacheBackend(temp_dir / "test.json")
    
    @pytest.fixture
    def small_dataset(self):
        """Small dataset for basic tests."""
        return generate_test_plugins(100)
    
    @pytest.fixture
    def medium_dataset(self):
        """Medium dataset for performance tests."""
        return generate_test_plugins(500)
    
    @pytest.fixture
    def large_dataset(self):
        """Large dataset for scalability tests."""
        return generate_test_plugins(1000)
    
    def test_sqlite_save_performance(self, sqlite_backend, medium_dataset):
        """Test SQLite save performance."""
        start_time = time.time()
        sqlite_backend.save(medium_dataset)
        save_time = time.time() - start_time
        
        assert save_time < 2.0, f"SQLite save took {save_time:.2f}s, expected < 2.0s"
        
        # Verify data was saved
        stats = sqlite_backend.get_stats()
        assert stats['total_plugins'] == len(medium_dataset)
    
    def test_json_save_performance(self, json_backend, medium_dataset):
        """Test JSON save performance."""
        start_time = time.time()
        json_backend.save(medium_dataset)
        save_time = time.time() - start_time
        
        # JSON should be reasonably fast for medium datasets
        assert save_time < 3.0, f"JSON save took {save_time:.2f}s, expected < 3.0s"
    
    def test_sqlite_load_performance(self, sqlite_backend, medium_dataset):
        """Test SQLite load performance."""
        # First save the data
        sqlite_backend.save(medium_dataset)
        
        # Then test load performance
        start_time = time.time()
        loaded_plugins = sqlite_backend.load()
        load_time = time.time() - start_time
        
        assert load_time < 1.0, f"SQLite load took {load_time:.2f}s, expected < 1.0s"
        assert len(loaded_plugins) == len(medium_dataset)
    
    def test_json_load_performance(self, json_backend, medium_dataset):
        """Test JSON load performance."""
        # First save the data
        json_backend.save(medium_dataset)
        
        # Then test load performance
        start_time = time.time()
        loaded_plugins = json_backend.load()
        load_time = time.time() - start_time
        
        assert load_time < 2.0, f"JSON load took {load_time:.2f}s, expected < 2.0s"
        assert len(loaded_plugins) == len(medium_dataset)
    
    def test_sqlite_search_performance(self, sqlite_backend, medium_dataset):
        """Test SQLite search performance."""
        # Save test data
        sqlite_backend.save(medium_dataset)
        
        # Test search performance
        start_time = time.time()
        results = sqlite_backend.search("TestMfg", limit=50)
        search_time = time.time() - start_time
        
        assert search_time < 0.1, f"SQLite search took {search_time:.3f}s, expected < 0.1s"
        assert len(results) > 0, "Search should return results"
    
    def test_sqlite_filter_performance(self, sqlite_backend, medium_dataset):
        """Test SQLite filter performance."""
        # Save test data
        sqlite_backend.save(medium_dataset)
        
        # Test filter performance
        start_time = time.time()
        results = sqlite_backend.filter_by_type("test")
        filter_time = time.time() - start_time
        
        assert filter_time < 0.1, f"SQLite filter took {filter_time:.3f}s, expected < 0.1s"
        assert len(results) == len(medium_dataset), "All plugins should match filter"
    
    def test_sqlite_update_performance(self, sqlite_backend, small_dataset):
        """Test SQLite update performance."""
        # Save initial data
        sqlite_backend.save(small_dataset)
        
        # Test update performance
        plugin_id = list(small_dataset.keys())[0]
        plugin = small_dataset[plugin_id]
        
        start_time = time.time()
        sqlite_backend.update(plugin_id, plugin)
        update_time = time.time() - start_time
        
        assert update_time < 0.1, f"SQLite update took {update_time:.3f}s, expected < 0.1s"
    
    def test_scalability_comparison(self, sqlite_backend, json_backend, large_dataset):
        """Compare scalability between SQLite and JSON backends."""
        # Test SQLite with large dataset
        start_time = time.time()
        sqlite_backend.save(large_dataset)
        sqlite_save_time = time.time() - start_time
        
        start_time = time.time()
        sqlite_loaded = sqlite_backend.load()
        sqlite_load_time = time.time() - start_time
        
        # Test JSON with large dataset
        start_time = time.time()
        json_backend.save(large_dataset)
        json_save_time = time.time() - start_time
        
        start_time = time.time()
        json_loaded = json_backend.load()
        json_load_time = time.time() - start_time
        
        # SQLite should be competitive or better
        print(f"SQLite save: {sqlite_save_time:.2f}s, load: {sqlite_load_time:.2f}s")
        print(f"JSON save: {json_save_time:.2f}s, load: {json_load_time:.2f}s")
        
        # Verify both loaded correctly
        assert len(sqlite_loaded) == len(large_dataset)
        assert len(json_loaded) == len(large_dataset)
        
        # SQLite should be reasonably fast
        assert sqlite_save_time < 5.0, "SQLite save should be under 5 seconds"
        assert sqlite_load_time < 2.0, "SQLite load should be under 2 seconds"
    
    def test_memory_efficiency(self, sqlite_backend, large_dataset):
        """Test that SQLite backend is memory efficient."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure memory before
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Save large dataset
        sqlite_backend.save(large_dataset)
        
        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (< 50MB for 1000 plugins)
        assert memory_increase < 50, f"Memory increase {memory_increase:.1f}MB too high"
        
        # Test that loading doesn't keep everything in memory
        loaded_plugins = sqlite_backend.load()
        memory_after_load = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory shouldn't increase much more after loading
        load_memory_increase = memory_after_load - memory_after
        assert load_memory_increase < 30, f"Load memory increase {load_memory_increase:.1f}MB too high"
        
        assert len(loaded_plugins) == len(large_dataset)