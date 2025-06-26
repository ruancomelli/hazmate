import asyncio
from collections.abc import AsyncIterator
from typing import TypeVar

_T = TypeVar("_T")


async def ainterleave(*async_iterators: AsyncIterator[_T]) -> AsyncIterator[_T]:
    """Interleave results from multiple async iterators.

    When an iterator is exhausted, it's removed and the others continue.
    Stops when all iterators are exhausted.
    """
    iterators = list(async_iterators)

    while iterators:
        # Try to get one item from each active iterator
        offset = 0
        for i in range(len(iterators)):
            index = i - offset

            try:
                item = await anext(iterators[index])
                yield item
            except StopAsyncIteration:
                # This iterator is exhausted, remove it
                iterators.pop(index)
                offset += 1


async def ainterleave_queued(*iters: AsyncIterator[_T]) -> AsyncIterator[_T]:
    queue: asyncio.Queue[_T | None] = asyncio.Queue()
    finished = 0
    total = len(iters)

    async def drain_iterator(it: AsyncIterator[_T]):
        try:
            async for item in it:
                await queue.put(item)
        finally:
            # Put a sentinel value to mark one iterator is done
            await queue.put(None)

    # Start one task per iterator
    tasks = [asyncio.create_task(drain_iterator(it)) for it in iters]

    while finished < total:
        item = await queue.get()
        if item is None:
            finished += 1
        else:
            yield item

    # Ensure all tasks are awaited to avoid warnings
    await asyncio.gather(*tasks, return_exceptions=True)


async def aislice(
    async_iterator: AsyncIterator,
    start: int,
    stop: int | None = None,
) -> AsyncIterator:
    """Async version of itertools.islice."""
    async for index, item in aenumerate(async_iterator):
        if stop is not None and index >= stop:
            break
        if index >= start:
            yield item


async def aenumerate(async_iterator: AsyncIterator, start: int = 0) -> AsyncIterator:
    """Async version of enumerate."""
    count = start
    async for item in async_iterator:
        yield count, item
        count += 1
