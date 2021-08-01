from contextlib import contextmanager
from brownie import chain


@contextmanager
def chain_snapshot():
    try:
        print('Making chain snapshot...')
        chain.snapshot()
        yield
    finally:
        print('Reverting the chain...')
        chain.revert()
