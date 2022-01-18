import sys

from brownie import accounts, Contract, AnchorVault, BridgeConnectorWormhole, Wei

from utils.config import (
    gas_price,
    get_deployer_account,
    get_env, get_is_live,
    prompt_bool,
    token_bridge_wormhole_address,
    vault_proxy_address,
)

def deploy_wormhole_bridge_connector(
    token_bridge_wormhole,
    tx_params,
    publish_source=False,
):
    connector = BridgeConnectorWormhole.deploy(
        token_bridge_wormhole,
        tx_params,
        publish_source=publish_source,
    )

    assert connector.wormhole_token_bridge() == token_bridge_wormhole

    return connector


def switch_bridge_connector_in_vault(vault, connector, tx_params):
    tx = vault.set_bridge_connector(connector.address, tx_params)
    tx.info()

    assert vault.bridge_connector() == connector.address


def main():
    is_live = get_is_live()
    deployer = get_deployer_account(is_live)
    changer = accounts.load(get_env('CHANGER'))

    if not is_live:
        deployer.transfer(changer, Wei("2 ether"))

    vault = Contract.from_abi('AnchorVault', vault_proxy_address, AnchorVault.abi)

    print('Deployer:', deployer)
    print('Bridge connector changer:', changer)
    print('AnchorVault:', vault.address)
    print('AnchorVault bridge connector:', vault.bridge_connector())
    print('Wormhole Token Bridge:', token_bridge_wormhole_address)
    print('Gas price:', gas_price)

    sys.stdout.write('Proceed? [y/n]: ')

    if not prompt_bool():
        print('Aborting')
        return

    connector = deploy_wormhole_bridge_connector(
        token_bridge_wormhole_address,
        tx_params={'from': deployer, 'gas_price': Wei(gas_price), 'required_confs': 1},
        publish_source=is_live
    )

    switch_bridge_connector_in_vault(
        vault,
        connector,
        tx_params={'from': changer, 'gas_price': Wei(gas_price)}
    )
