import pytest
from brownie import Contract, accounts, interface

from scripts.deploy_ropsten import deploy_vault
from scripts.deploy_ropsten import (
    admin_addr,
    beth_token_addr,
    steth_token_addr,
    rewards_liquidator_addr,
    anchor_rewards_distributor,
    no_liquidation_interval,
    wormhole_token_bridge,
    restricted_liquidation_interval,
)

TERRA_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
UST_WRAPPER_ADDRESS = "0x6cA13a4ab78dd7D657226b155873A04DB929A3A4"


@pytest.fixture(scope="function")
def vault(AnchorVault):
    deployer = accounts.at("0x02139137FdD974181a49268D7b0AE888634E5469", force=True)
    anchor_vault = deploy_vault(deployer, False)
    return Contract.from_abi("AnchorVault", anchor_vault, AnchorVault.abi)


@pytest.fixture(scope="function")
def steth_token_ropsten():
    return interface.LidoRopsten(steth_token_addr)


@pytest.fixture(scope="function")
def beth_token_ropsten(bEth):
    return Contract.from_abi("bEth", beth_token_addr, bEth.abi)


@pytest.fixture(scope="function")
def ust_token_ropsten():
    return interface.UST(UST_WRAPPER_ADDRESS)


def test_initial_config_correct(vault):
    assert vault.admin() == admin_addr
    assert vault.beth_token() == beth_token_addr
    assert vault.steth_token() == steth_token_addr
    assert vault.liquidations_admin() == admin_addr
    assert vault.rewards_liquidator() == rewards_liquidator_addr
    assert vault.no_liquidation_interval() == no_liquidation_interval
    assert vault.anchor_rewards_distributor() == anchor_rewards_distributor
    assert vault.restricted_liquidation_interval() == restricted_liquidation_interval


def test_submit_happy_path_steth(vault, steth_token_ropsten, beth_token_ropsten):
    vault_user = accounts[0]
    amount = 0.5 * 10 ** 18

    vault_steth_balance_before = steth_token_ropsten.balanceOf(vault.address)
    steth_balance_before = steth_token_ropsten.balanceOf(vault_user)
    wormhole_beth_balance_before = beth_token_ropsten.balanceOf(wormhole_token_bridge)

    steth_token_ropsten.approve(vault, amount, {"from": vault_user})
    vault.submit(amount, TERRA_ADDRESS, "0xab", vault.version(), {"from": vault_user})

    steth_balance_after = steth_token_ropsten.balanceOf(vault_user)

    assert steth_balance_before > steth_balance_after
    assert vault_steth_balance_before < steth_token_ropsten.balanceOf(vault.address)
    assert wormhole_beth_balance_before < beth_token_ropsten.balanceOf(
        wormhole_token_bridge
    )


def test_submit_happy_path_eth(vault, steth_token_ropsten, beth_token_ropsten):
    vault_user = accounts[0]
    amount = 0.5 * 10 ** 18

    wormhole_beth_balance_before = beth_token_ropsten.balanceOf(wormhole_token_bridge)
    vault_steth_balance_before = steth_token_ropsten.balanceOf(vault.address)
    balance_before = vault_user.balance()

    vault.submit(
        amount,
        TERRA_ADDRESS,
        "0xab",
        vault.version(),
        {"from": vault_user, "value": amount},
    )

    assert balance_before > vault_user.balance()
    assert vault_steth_balance_before < steth_token_ropsten.balanceOf(vault.address)
    assert wormhole_beth_balance_before < beth_token_ropsten.balanceOf(
        wormhole_token_bridge
    )


def test_collect_rewards_happy_path(
    vault, steth_token_ropsten, ust_token_ropsten, helpers
):
    deployer = accounts.at("0x02139137FdD974181a49268D7b0AE888634E5469", force=True)
    vault_user = accounts[0]
    amount = 0.5 * 10 ** 18

    wormhole_bridge_ust_balance_before = ust_token_ropsten.balanceOf(
        wormhole_token_bridge
    )

    steth_token_ropsten.approve(vault, amount, {"from": vault_user})
    vault.submit(
        amount,
        TERRA_ADDRESS,
        "0xab",
        vault.version(),
        {"from": vault_user, "value": amount},
    )

    steth_token_ropsten.simulateBeaconRewards({"from": deployer})

    tx = vault.collect_rewards({"from": vault_user})

    vault_evt = helpers.assert_single_event_named("RewardsCollected", tx, source=vault)

    assert vault_evt["steth_amount"] > 0
    assert vault_evt["ust_amount"] > 0
    assert wormhole_bridge_ust_balance_before < ust_token_ropsten.balanceOf(
        wormhole_token_bridge
    )
