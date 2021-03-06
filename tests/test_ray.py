import pytest
import random

ray = pytest.importorskip("ray")

import rx
import rx.operators as ops
from rx.subject import Subject
import rxray


def test_defaults():
    data = range(200)
    ray.init()

    result = rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: i*2)),
        ),
        ops.to_list(),
    ).run()

    ray.shutdown()
    assert result == [i*2 for i in data]


def test_factory_with_context():
    data = range(200)
    ray.init()

    def factory(scale):
        def _factory():
            return rx.pipe(ops.map(lambda i: i*3))

        return _factory

    result = rx.from_(data).pipe(
        rxray.distribute(factory(scale=3)),
        ops.to_list(),
    ).run()

    ray.shutdown()
    assert result == [i*3 for i in data]


def test_rr_batch_multiple_actors():
    data = range(200)
    ray.init()

    result = rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: i*2)),
            actor_count=3,
            batch_size=16,
            queue_size=3),
        ops.to_list(),
    ).run()

    ray.shutdown()
    assert result == [i*2 for i in data]


def test_rr_batch_empty_on_completion():
    data = range(192)
    ray.init()

    result = rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: i*2)),
            actor_count=3,
            batch_size=16,
            queue_size=3
        ),
        ops.to_list(),
    ).run()

    ray.shutdown()
    assert result == [i*2 for i in data]


def test_key_partitioning():
    data = [(i, j) for i in range(17) for j in range(100)]
    random.shuffle(data)
    ray.init()

    result = rx.from_(data).pipe(
        rxray.distribute(            
            lambda: rx.pipe(ops.map(lambda i: (i[0], i[1]*2))),
            actor_selector=rxray.partition_by_key(lambda i: i[0]),
        ),
        ops.to_list(),
    ).run()

    ray.shutdown()

    # check that items are ordered by key
    for key in range(17):
        key_result = list(filter(lambda i: i[0] == key, result))
        key_data = list(filter(lambda i: i[0] == key, data))
        assert key_result == [(i[0], i[1]*2) for i in key_data]


def test_statefull_key_partitioning():
    data = [(i, j) for i in range(17) for j in range(100)]
    random.shuffle(data)
    ray.init()

    result = rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(
                ops.group_by(lambda i: i[0]),
                ops.flat_map(lambda g: g.pipe(
                    ops.map(lambda i: i[1]),
                    ops.average(),
                    ops.map(lambda i: (g.key, i)),
                ))
            ),
            actor_selector=rxray.partition_by_key(lambda i: i[0]),
        ),
        ops.to_list(),
    ).run()

    ray.shutdown()

    # check that items are ordered by key
    assert len(result) == 17
    for r in result:
        assert r[1] == 49.5

def test_completion():
    data = Subject()
    ray.init()

    completed = False

    def on_completed():
        nonlocal completed
        completed = True

    data.pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.take(1)),
            actor_count=2,
            queue_size=2,
        ),
    ).subscribe(
        on_completed=on_completed
    )

    # queue size adds latency to the reception of completed/error
    for _ in range(3):
        data.on_next(0)
        assert completed is False
    data.on_next(0)
    assert completed is True
    ray.shutdown()


def test_error():
    data = Subject()
    ray.init()

    error = None

    def on_error(e):
        nonlocal error
        error = e

    data.pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: 1/i)),
            actor_count=2,
            queue_size=2,
        ),
    ).subscribe(
        on_error=on_error
    )

    data.on_next(2)
    data.on_next(0)
    # queue size adds latency to the reception of completed/error        
    for _ in range(3):
        data.on_next(2)
    assert type(error) == ZeroDivisionError
    ray.shutdown()
