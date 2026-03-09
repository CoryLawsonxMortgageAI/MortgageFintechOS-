"""Tests for the priority task queue system."""

import pytest

from core.task_queue import Task, TaskPriority, TaskStatus, TaskQueue


def _make_task(priority: TaskPriority = TaskPriority.MEDIUM, action: str = "test_action") -> Task:
    return Task(priority=priority, agent_name="TEST", action=action)


@pytest.mark.asyncio
async def test_enqueue_dequeue():
    """Tasks should dequeue in priority order."""
    q = TaskQueue()
    low = _make_task(TaskPriority.LOW)
    critical = _make_task(TaskPriority.CRITICAL)
    medium = _make_task(TaskPriority.MEDIUM)

    await q.enqueue(low)
    await q.enqueue(critical)
    await q.enqueue(medium)

    first = await q.dequeue()
    assert first.priority == TaskPriority.CRITICAL
    assert first.status == TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_complete_adds_to_history():
    """Completing a task should add it to history."""
    q = TaskQueue()
    task = _make_task()
    await q.enqueue(task)
    dequeued = await q.dequeue()
    q.complete(dequeued, result={"ok": True})

    assert dequeued.status == TaskStatus.COMPLETED
    assert len(q.history) == 1
    assert q.history[0].result == {"ok": True}


@pytest.mark.asyncio
async def test_fail_retries_until_max():
    """Failing should increment retries, then mark FAILED at max."""
    q = TaskQueue()
    task = _make_task()
    task.max_retries = 2
    await q.enqueue(task)
    dequeued = await q.dequeue()

    q.fail(dequeued, "error 1")
    assert dequeued.status == TaskStatus.RETRYING
    assert dequeued.retries == 1

    q.fail(dequeued, "error 2")
    assert dequeued.status == TaskStatus.RETRYING
    assert dequeued.retries == 2

    # Third fail exceeds max_retries — task is now FAILED
    q.fail(dequeued, "error 3")
    assert dequeued.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_get_stats():
    """Stats should reflect queue state."""
    q = TaskQueue()
    t1 = _make_task()
    t2 = _make_task()
    await q.enqueue(t1)
    await q.enqueue(t2)

    d1 = await q.dequeue()
    q.complete(d1)
    d2 = await q.dequeue()
    d2.max_retries = 0
    q.fail(d2, "boom")

    stats = q.get_stats()
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["pending"] == 0


@pytest.mark.asyncio
async def test_serialize_restore():
    """Queue history should round-trip through serialization."""
    q = TaskQueue()
    task = _make_task(action="serialize_test")
    await q.enqueue(task)
    dequeued = await q.dequeue()
    q.complete(dequeued, result={"data": "value"})

    data = q.to_dict()
    assert len(data["history"]) == 1

    q2 = TaskQueue()
    q2.restore_from_dict(data)
    assert len(q2.history) == 1
    assert q2.history[0].action == "serialize_test"
    assert q2.history[0].result == {"data": "value"}


@pytest.mark.asyncio
async def test_queue_size():
    """Size should reflect pending items."""
    q = TaskQueue()
    assert q.size == 0
    await q.enqueue(_make_task())
    await q.enqueue(_make_task())
    assert q.size == 2
    await q.dequeue()
    assert q.size == 1
