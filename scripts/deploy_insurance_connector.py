from brownie import interface
from brownie.network import priority_fee

from brownie import (
    InsuranceConnector,
    MockSelfOwnedStETHBurner
)

import utils.log as log
import utils.config as c

from utils.log import assert_equals

def warn_live():
    print('Running on a live network, cannot run further checks.')
    print('Run on a mainnet fork to do this.')

def main():
    burner_addr = c.selfowned_steth_burner_addr
    deployer = c.get_deployer_account(c.get_is_live())

    if burner_addr is None:
        log.nb('SelfOwnedStETHBurner is not yet deployed')
        if c.get_is_live():
            warn_live()
            return

        log.ok('Deploying mock instead of real burner')
        burner_addr = MockSelfOwnedStETHBurner.deploy(
            c.steth_token_addr,
            c.lido_dao_voting_addr,
            {'from' : deployer }
        )
    else:
        log.ok('Using already deployed SelfOwnedStETHBurner')

    burner = interface.SelfOwnedStETHBurner(burner_addr)

    log.ok('SelfOwnedStETHBurner', burner.address)
    assert_equals(' - steth ', burner.LIDO(), c.steth_token_addr)
    assert_equals(' - voting', burner.VOTING(), c.lido_dao_voting_addr)

    if c.get_is_live():
        warn_live()
        priority_fee('auto')

    log.nb('Do you want to continue deploy process?')
    c.prompt_bool()

    verify_flag = c.get_is_live()

    insurance_connector = InsuranceConnector.deploy(
        burner.address,
        {'from': deployer },
        publish_source=verify_flag
    )

    log.ok('InsuranceConnector', insurance_connector.address)

    assert_equals(
        ' - burner',
        insurance_connector.get_self_owned_steth_burner(),
        burner.address
    )

    print()
    log.nb('Please save the insurance connector address', insurance_connector.address)
