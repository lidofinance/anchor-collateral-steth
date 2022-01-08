import sys

from brownie import Contract, AnchorVault, Wei, network
from brownie import BridgeConnectorWormhole, accounts

from utils.config import (
    gas_price,
    get_deployer_account,
    get_env, 
    get_is_live,
    prompt_bool,
    token_bridge_wormhole_address,
    token_bridge_wormhole_ropsten_address,
    vault_proxy_address,
    vault_ropsten_address,
    beth_token_address,
    beth_token_ropsten_address,
    ust_shuttle_token_address,
    ust_shuttle_token_ropsten_address,
)

def deploy_wormhole_bridge_connector(
    token_bridge_wormhole,
    beth_token,
    ust_wrapper_token,
    tx_params,
    publish_source=False,
):
    connector = BridgeConnectorWormhole.deploy(
        token_bridge_wormhole,
        beth_token,
        ust_wrapper_token,
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
    net = network.show_active()

    if not is_live:
        deployer.transfer(changer, Wei("2 ether"))

    if net == "ropsten":
        vault = AnchorVault.at(vault_ropsten_address)
        beth_token = beth_token_ropsten_address
        ust_wrapper_token = ust_shuttle_token_ropsten_address
        bridge_address = token_bridge_wormhole_ropsten_address
    else:
        vault = Contract.from_abi('AnchorVault', vault_proxy_address, AnchorVault.abi)
        beth_token = beth_token_address
        ust_wrapper_token = ust_shuttle_token_address
        bridge_address = token_bridge_wormhole_address

    print('Deployer:', deployer)
    print('Bridge connector changer:', changer)
    print('AnchorVault:', vault.address)
    print('AnchorVault bridge connector:', vault.bridge_connector())
    print('Wormhole Token Bridge:', bridge_address)
    print('Gas price:', gas_price)

    sys.stdout.write('Proceed? [y/n]: ')

    if not prompt_bool():
        print('Aborting')
        return

    connector = deploy_wormhole_bridge_connector(
        bridge_address,
        beth_token,
        ust_wrapper_token,
        tx_params={'from': deployer, 'gas_price': Wei(gas_price), 'required_confs': 1},
        publish_source=False
    )

    switch_bridge_connector_in_vault(
        vault,
        connector,
        tx_params={'from': changer, 'gas_price': Wei(gas_price)}
    )
