from brownie import (
    bEth,
    AnchorVault,
    AnchorVaultProxy,
    InsuranceConnector,
    BridgeConnectorWormhole,
    MockSelfOwnedStETHBurner,
)
from brownie import accounts, Contract, ZERO_ADDRESS

import utils.config as c

beth_token_addr = "0xA60100d5e12E9F83c1B04997314cf11685A618fF"
steth_token_addr = "0xd40EefCFaB888C9159a61221def03bF77773FC19"
admin_addr = "0x02139137fdd974181a49268d7b0ae888634e5469"
rewards_liquidator_addr = "0x81c73492380eC87B464b2E53f7e7f9dD30c7ded9"
anchor_rewards_distributor = (
    "0x000000000000000000000000976309db2db556f107c28fe4d7eab7c7e676c194"
)
wormhole_token_bridge = "0xF174F9A837536C449321df1Ca093Bb96948D5386"
no_liquidation_interval = 0
restricted_liquidation_interval = 0


def deploy_insurance_connector(deployer, verify_flag):
    burner_addr = MockSelfOwnedStETHBurner.deploy(
        steth_token_addr,
        ZERO_ADDRESS,
        {"from": deployer},
    )
    return InsuranceConnector.deploy(
        burner_addr, {"from": deployer}, publish_source=verify_flag
    )


def deploy_bridge_connector(deployer, verify_flag):
    return BridgeConnectorWormhole.deploy(
        wormhole_token_bridge, {"from": deployer}, publish_source=verify_flag
    )


def deploy_vault(deployer, verify_flag):
    insurance_connector = deploy_insurance_connector(deployer, verify_flag)
    bridge_connector = deploy_bridge_connector(deployer, verify_flag)
    beth = Contract.from_abi("bEth", beth_token_addr, bEth.abi)

    impl = AnchorVault.deploy({"from": deployer}, publish_source=verify_flag)
    impl.petrify_impl({"from": deployer})
    proxy = AnchorVaultProxy.deploy(
        impl.address, deployer, {"from": deployer}, publish_source=verify_flag
    )
    vault = Contract.from_abi("AnchorVault", proxy.address, AnchorVault.abi)
    vault.initialize(
        beth_token_addr, steth_token_addr, admin_addr, admin_addr, {"from": deployer}
    )
    vault.configure(
        bridge_connector.address,
        rewards_liquidator_addr,
        insurance_connector,
        admin_addr,
        no_liquidation_interval,
        restricted_liquidation_interval,
        anchor_rewards_distributor,
        {"from": deployer},
    )
    beth.set_minter(vault, {"from": deployer})
    vault.resume({"from": deployer})

    return vault


def main():
    deployer = accounts.load("ropsten-deployer")
    verify_flag = c.get_is_live()

    deploy_vault(deployer, verify_flag)
