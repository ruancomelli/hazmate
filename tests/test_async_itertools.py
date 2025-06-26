import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from hazmate.utils.async_itertools import ainterleave, ainterleave_queued, aislice


async def async_range(n: int) -> AsyncIterator[int]:
    """Helper function to create an async iterator from range."""
    for i in range(n):
        yield i


async def async_iter_from_list(items: list[Any]) -> AsyncIterator[Any]:
    """Helper function to create an async iterator from a list."""
    for item in items:
        yield item


async def async_range_with_delay(n: int, delay: float = 0.01) -> AsyncIterator[int]:
    """Helper function to create an async iterator with delays for testing concurrency."""
    for i in range(n):
        await asyncio.sleep(delay)
        yield i


class TestAinterleave:
    """Test cases for ainterleave function."""

    @pytest.mark.asyncio
    async def test_ainterleave_two_equal_length_iterators(self):
        """Test interleaving two iterators of equal length."""
        iter1 = async_range(3)  # [0, 1, 2]
        iter2 = async_iter_from_list(["a", "b", "c"])  # ['a', 'b', 'c']

        result = [item async for item in ainterleave(iter1, iter2)]

        # Should alternate between the two iterators
        assert result == [0, "a", 1, "b", 2, "c"]

    @pytest.mark.asyncio
    async def test_ainterleave_different_lengths(self):
        """Test interleaving iterators of different lengths."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list(["a", "b", "c", "d"])  # ['a', 'b', 'c', 'd']

        result = [item async for item in ainterleave(iter1, iter2)]

        # Should continue with remaining items from longer iterator
        assert result == [0, "a", 1, "b", "c", "d"]

    @pytest.mark.asyncio
    async def test_ainterleave_three_iterators(self):
        """Test interleaving three iterators."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list(["a", "b"])  # ['a', 'b']
        iter3 = async_iter_from_list([10, 20, 30])  # [10, 20, 30]

        result = [item async for item in ainterleave(iter1, iter2, iter3)]

        # Should rotate through all three iterators
        assert result == [0, "a", 10, 1, "b", 20, 30]

    @pytest.mark.asyncio
    async def test_ainterleave_empty_iterator(self):
        """Test interleaving with an empty iterator."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list([])  # []
        iter3 = async_iter_from_list(["a", "b"])  # ['a', 'b']

        result = [item async for item in ainterleave(iter1, iter2, iter3)]

        # Empty iterator should be ignored
        assert result == [0, "a", 1, "b"]

    @pytest.mark.asyncio
    async def test_ainterleave_all_empty(self):
        """Test interleaving with all empty iterators."""
        iter1 = async_iter_from_list([])
        iter2 = async_iter_from_list([])

        result = [item async for item in ainterleave(iter1, iter2)]

        assert result == []

    @pytest.mark.asyncio
    async def test_ainterleave_single_iterator(self):
        """Test interleaving with a single iterator."""
        iter1 = async_range(3)  # [0, 1, 2]

        result = [item async for item in ainterleave(iter1)]

        assert result == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_ainterleave_no_iterators(self):
        """Test interleaving with no iterators."""
        result = [item async for item in ainterleave()]

        assert result == []

    @pytest.mark.asyncio
    async def test_ainterleave_one_much_longer(self):
        """Test when one iterator is much longer than others."""
        iter1 = async_range(1)  # [0]
        iter2 = async_range(5)  # [0, 1, 2, 3, 4]

        result = [item async for item in ainterleave(iter1, iter2)]

        # Should alternate initially, then continue with longer one
        assert result == [0, 0, 1, 2, 3, 4]


class TestAislice:
    """Test cases for aislice function."""

    @pytest.mark.asyncio
    async def test_aislice_normal_range(self):
        """Test normal slicing with start and stop."""
        async_iter = async_range(10)  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        result = [item async for item in aislice(async_iter, 2, 6)]

        assert result == [2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_aislice_from_beginning(self):
        """Test slicing from the beginning."""
        async_iter = async_range(5)  # [0, 1, 2, 3, 4]

        result = [item async for item in aislice(async_iter, 0, 3)]

        assert result == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_aislice_stop_beyond_length(self):
        """Test when stop is beyond iterator length."""
        async_iter = async_range(3)  # [0, 1, 2]

        result = [item async for item in aislice(async_iter, 1, 10)]

        assert result == [1, 2]

    @pytest.mark.asyncio
    async def test_aislice_start_beyond_length(self):
        """Test when start is beyond iterator length."""
        async_iter = async_range(3)  # [0, 1, 2]

        result = [item async for item in aislice(async_iter, 5, 10)]

        assert result == []

    @pytest.mark.asyncio
    async def test_aislice_start_equals_stop(self):
        """Test when start equals stop."""
        async_iter = async_range(5)  # [0, 1, 2, 3, 4]

        result = [item async for item in aislice(async_iter, 2, 2)]

        assert result == []

    @pytest.mark.asyncio
    async def test_aislice_empty_iterator(self):
        """Test slicing an empty iterator."""
        async_iter = async_iter_from_list([])

        result = [item async for item in aislice(async_iter, 0, 5)]

        assert result == []

    @pytest.mark.asyncio
    async def test_aislice_single_item_range(self):
        """Test slicing to get a single item."""
        async_iter = async_range(10)  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        result = [item async for item in aislice(async_iter, 5, 6)]

        assert result == [5]

    @pytest.mark.asyncio
    async def test_aislice_string_items(self):
        """Test slicing with string items."""
        items = ["a", "b", "c", "d", "e", "f"]
        async_iter = async_iter_from_list(items)

        result = [item async for item in aislice(async_iter, 1, 4)]

        assert result == ["b", "c", "d"]

    @pytest.mark.asyncio
    async def test_aislice_zero_start(self):
        """Test slicing with start=0."""
        async_iter = async_range(4)  # [0, 1, 2, 3]

        result = [item async for item in aislice(async_iter, 0, 2)]

        assert result == [0, 1]

    @pytest.mark.asyncio
    async def test_aislice_large_range(self):
        """Test slicing with a larger range."""
        async_iter = async_range(100)

        result = [item async for item in aislice(async_iter, 95, 100)]

        assert result == [95, 96, 97, 98, 99]


class TestIntegration:
    """Integration tests combining both functions."""

    @pytest.mark.asyncio
    async def test_aislice_then_ainterleave(self):
        """Test using aislice output as input to ainterleave."""
        # Create sliced iterators
        slice1 = aislice(async_range(10), 0, 3)  # [0, 1, 2]
        slice2 = aislice(async_range(10), 5, 8)  # [5, 6, 7]

        result = [item async for item in ainterleave(slice1, slice2)]

        assert result == [0, 5, 1, 6, 2, 7]

    @pytest.mark.asyncio
    async def test_ainterleave_then_aislice(self):
        """Test using ainterleave output as input to aislice."""
        # Create interleaved iterator
        iter1 = async_range(3)  # [0, 1, 2]
        iter2 = async_iter_from_list(["a", "b", "c"])  # ['a', 'b', 'c']
        interleaved = ainterleave(iter1, iter2)  # [0, 'a', 1, 'b', 2, 'c']

        result = [item async for item in aislice(interleaved, 1, 5)]

        assert result == ["a", 1, "b", 2]


class TestAinterleaveQueued:
    """Test cases for ainterleave_queued function."""

    @pytest.mark.asyncio
    async def test_ainterleave_queued_two_equal_length_iterators(self):
        """Test queued interleaving with two iterators of equal length."""
        iter1 = async_range(3)  # [0, 1, 2]
        iter2 = async_iter_from_list(["a", "b", "c"])  # ['a', 'b', 'c']

        result = [item async for item in ainterleave_queued(iter1, iter2)]

        # All items should be present (order may vary due to concurrency)
        assert len(result) == 6
        assert set(result) == {0, 1, 2, "a", "b", "c"}

    @pytest.mark.asyncio
    async def test_ainterleave_queued_different_lengths(self):
        """Test queued interleaving with iterators of different lengths."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list(["a", "b", "c", "d"])  # ['a', 'b', 'c', 'd']

        result = [item async for item in ainterleave_queued(iter1, iter2)]

        # All items should be present
        assert len(result) == 6
        assert set(result) == {0, 1, "a", "b", "c", "d"}

    @pytest.mark.asyncio
    async def test_ainterleave_queued_three_iterators(self):
        """Test queued interleaving with three iterators."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list(["a", "b"])  # ['a', 'b']
        iter3 = async_iter_from_list([10, 20, 30])  # [10, 20, 30]

        result = [item async for item in ainterleave_queued(iter1, iter2, iter3)]

        # All items should be present
        assert len(result) == 7
        assert set(result) == {0, 1, "a", "b", 10, 20, 30}

    @pytest.mark.asyncio
    async def test_ainterleave_queued_empty_iterator(self):
        """Test queued interleaving with an empty iterator."""
        iter1 = async_range(2)  # [0, 1]
        iter2 = async_iter_from_list([])  # []
        iter3 = async_iter_from_list(["a", "b"])  # ['a', 'b']

        result = [item async for item in ainterleave_queued(iter1, iter2, iter3)]

        # Empty iterator should be ignored
        assert len(result) == 4
        assert set(result) == {0, 1, "a", "b"}

    @pytest.mark.asyncio
    async def test_ainterleave_queued_all_empty(self):
        """Test queued interleaving with all empty iterators."""
        iter1 = async_iter_from_list([])
        iter2 = async_iter_from_list([])

        result = [item async for item in ainterleave_queued(iter1, iter2)]

        assert result == []

    @pytest.mark.asyncio
    async def test_ainterleave_queued_single_iterator(self):
        """Test queued interleaving with a single iterator."""
        iter1 = async_range(3)  # [0, 1, 2]

        result = [item async for item in ainterleave_queued(iter1)]

        assert result == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_ainterleave_queued_no_iterators(self):
        """Test queued interleaving with no iterators."""
        result = [item async for item in ainterleave_queued()]

        assert result == []

    @pytest.mark.asyncio
    async def test_ainterleave_queued_one_much_longer(self):
        """Test queued interleaving when one iterator is much longer than others."""
        iter1 = async_range(1)  # [0]
        iter2 = async_range(5)  # [0, 1, 2, 3, 4]

        result = [item async for item in ainterleave_queued(iter1, iter2)]

        # All items should be present
        assert len(result) == 6
        assert set(result) == {0, 1, 2, 3, 4}
        # There should be two zeros (one from each iterator)
        assert result.count(0) == 2

    @pytest.mark.asyncio
    async def test_ainterleave_queued_concurrent_behavior(self):
        """Test that ainterleave_queued actually processes iterators concurrently."""
        # Use iterators with delays to test concurrency
        iter1 = async_range_with_delay(3, 0.1)  # Slower iterator
        iter2 = async_range_with_delay(3, 0.05)  # Faster iterator

        import time

        start_time = time.time()
        result = [item async for item in ainterleave_queued(iter1, iter2)]
        end_time = time.time()

        # All items should be present
        assert len(result) == 6
        assert set(result) == {0, 1, 2}

        # With concurrency, total time should be less than sum of sequential delays
        # Sequential would be: 3*0.1 + 3*0.05 = 0.45 seconds
        # Concurrent should be closer to max(3*0.1, 3*0.05) = 0.3 seconds
        # Allow some tolerance for test execution overhead
        assert end_time - start_time < 0.4

    @pytest.mark.asyncio
    async def test_ainterleave_queued_order_independence(self):
        """Test that ainterleave_queued produces consistent results regardless of order."""
        # Run multiple times to check for race conditions
        for _ in range(5):
            iter1 = async_range(3)
            iter2 = async_iter_from_list(["a", "b", "c"])

            result = [item async for item in ainterleave_queued(iter1, iter2)]

            # Should always have the same set of items
            assert len(result) == 6
            assert set(result) == {0, 1, 2, "a", "b", "c"}

    @pytest.mark.asyncio
    async def test_ainterleave_queued_exception_handling(self):
        """Test that ainterleave_queued handles exceptions in iterators gracefully."""

        async def failing_iterator():
            yield 1
            yield 2
            raise ValueError("Test exception")

        iter1 = async_range(3)  # [0, 1, 2]
        iter2 = failing_iterator()  # [1, 2, then exception]

        # The function should handle the exception and continue with other iterators
        result = []
        try:
            async for item in ainterleave_queued(iter1, iter2):
                result.append(item)
        except Exception:
            # Some items might have been yielded before the exception
            pass

        # At least the items from the successful iterator should be present
        # The exact behavior depends on timing, but we should get at least some items
        assert len(result) >= 3  # At least the items from iter1
        # Check that items from iter1 are present
        assert 0 in result
        assert 1 in result
        assert 2 in result

    @pytest.mark.asyncio
    async def test_ainterleave_queued_with_duplicates(self):
        """Test queued interleaving with duplicate values across iterators."""
        iter1 = async_iter_from_list([1, 2, 1])
        iter2 = async_iter_from_list([2, 3, 1])

        result = [item async for item in ainterleave_queued(iter1, iter2)]

        # Should have all items, including duplicates
        assert len(result) == 6
        assert result.count(1) == 3  # 1 appears twice in iter1, once in iter2
        assert result.count(2) == 2  # 2 appears once in each iterator
        assert result.count(3) == 1  # 3 appears once in iter2
