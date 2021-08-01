=======================
RxRay
=======================

.. image:: https://badge.fury.io/py/rxray.svg
    :target: https://badge.fury.io/py/rxray

.. image:: https://github.com/maki-nage/rxray/workflows/Python%20package/badge.svg
    :target: https://github.com/maki-nage/rxray/actions?query=workflow%3A%22Python+package%22
    :alt: Github WorkFlows


RxPy operator to distribute a computation with `ray <https://ray.io/>`_

Get Started
============

The distribute operator can be used directly in an existing pipeline to
parallelize computations:

.. code:: python3

    data = range(200)
    ray.init()

    rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: i*2)),
        ),
    ).subscribe()


When the distributed computation is statefull, items can be pinned to an actor
with a key based selector:

.. code:: python3

    data = [(i, j) for i in range(17) for j in range(100)]
    random.shuffle(data)
    ray.init()

    rx.from_(data).pipe(
        rxray.distribute(
            lambda: rx.pipe(ops.map(lambda i: (i[0], i[1]*2))),
            actor_selector=rxray.partition_by_key(lambda i: i[0]),
        ),
    ).subscribe()


Installation
=============

RxRay is available on PyPi and can be installed with pip:

.. code:: console

    python3 -m pip install rxray
