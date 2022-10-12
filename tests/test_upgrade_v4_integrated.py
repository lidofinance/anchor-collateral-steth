import math
import pytest
import brownie
import utils.config as config

TERRA_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
LIDO_DAO_FINANCE_MULTISIG = "0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb"
STETH_ERROR_MARGIN = 2

@pytest.fixture(scope="module")
def steth_approx_equal():
    def equal(steth_amount_a, steth_amount_b):
        return math.isclose(a=steth_amount_a, b=steth_amount_b, abs_tol=STETH_ERROR_MARGIN)
    return equal


@pytest.mark.parametrize("deposit_amount", [10 * 10**18])
def test_minting_disabled_but_preupgrade_beth_are_withdrawable(
    accounts,
    stranger,
    steth_token,
    lido_oracle_report,
    deploy_vault_and_pass_dao_vote,
    deposit_amount,
    steth_approx_equal
):
    """
    This is a big integrated test that validates,
        a) minting after the v4 upgrade is disabled,
        b) any bETH that were minted before the upgrade are still withdrawable.

    Why is this test so big?

        Rather than dividing this test into smaller unit tests,
        we believe, that a big integrated test will better illustrate
        what the v4 upgrade entails and will show a more cohesive picture.

    This test runs in several stages.

        Stage 0. Setup - declare all the necessary variables.

        Stage 1. Pre-upgrade - validate that we will change
        in this upcoming upgrade. This will help us understand
        what has changed after the upgrade.

        Stage 2. Upgrade - validate post-upgrade configuration

        Stage 3. 2022/01/26 - confirm that the mitigation upgrade (version 3)
        for the 2022/01/26 burned bETH incident has not been performed again.

        Stage 4. Mint - confirm that minting doesn't work. `submit` reverts
        and both beth and steth total supplies remain the same.

        Stage 5. Withdraw - confirm that the user can withdraw their bETH worth of stETH
        that were minted on Terra before the upgrade. We will simulate the bridging of funds
        from Wormhole and call `withdraw` from stranger.`

    """

    ##################
    # STAGE 0. Setup #
    ##################

    # initialize vault proxy
    vault_proxy = brownie.Contract.from_abi(
        "AnchorVaultProxy", config.vault_proxy_addr, brownie.AnchorVaultProxy.abi
    )

    # initialize vault
    vault = brownie.Contract.from_abi(
        "AnchorVault", config.vault_proxy_addr, brownie.AnchorVault.abi
    )

    beth_token = brownie.interface.ERC20(vault.beth_token())

    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)

    ########################
    # STAGE 1. Pre-upgrade #
    ########################

    # minting new bETH works as expected

    prev_beth_total_supply = beth_token.totalSupply()

    vault.submit(
        deposit_amount,
        TERRA_ADDRESS,
        "0x8bada2e",
        vault.version(),
        {"from": stranger, "value": deposit_amount},
    )

    # before and after delta is stranger's balance, as we can't directly query stranger's balance
    preupgrade_terra_beth_minted_to_stranger = (
        beth_token.totalSupply() - prev_beth_total_supply
    )
    assert preupgrade_terra_beth_minted_to_stranger > 0, "new beth were minted"

    # check current implementation address
    assert vault_proxy.implementation() == config.vault_impl_addr

    # check vault version
    assert vault.version() == 3, "version matches"

    # simulate positive rebase and check withdrawal rate
    lido_oracle_report(steth_rebase_mult=1.01)
    vault.get_rate() == 10**18

    # rewards are collectable
    vault.collect_rewards({"from": liquidations_admin})

    # vault is operating
    assert vault.can_deposit_or_withdraw()

    ####################
    # STAGE 2. Upgrade #
    ####################

    # remember pre-upgrade state for Stage 3
    preupgrade_vault_steth_balance = steth_token.balanceOf(vault_proxy)
    preupgrade_finance_steth_balance = steth_token.balanceOf(LIDO_DAO_FINANCE_MULTISIG)

    # deploy a new vault implementation, start and enact DAO vote
    new_vault_implementation = deploy_vault_and_pass_dao_vote()

    # check configuration
    assert config.vault_impl_addr != new_vault_implementation.address
    assert vault_proxy.implementation() == new_vault_implementation.address
    assert vault.version() == 4
    assert vault.beth_token() == beth_token.address
    assert vault.steth_token() == steth_token
    assert vault.admin() == config.lido_dao_agent_address
    assert vault.bridge_connector() == config.bridge_connector_addr
    assert vault.rewards_liquidator() == config.rewards_liquidator_addr
    assert vault.insurance_connector() == config.insurance_connector_addr
    assert vault.liquidations_admin() == config.vault_liquidations_admin_addr
    assert vault.can_deposit_or_withdraw()

    #######################
    # STAGE 3. 2022/01/26 #
    #######################

    assert steth_token.balanceOf(vault_proxy) == preupgrade_vault_steth_balance
    assert (
        steth_token.balanceOf(LIDO_DAO_FINANCE_MULTISIG)
        == preupgrade_finance_steth_balance
    )

    #################
    # STAGE 4. Mint #
    #################

    prev_beth_total_supply = beth_token.totalSupply()
    prev_steth_total_supply = steth_token.totalSupply()

    with brownie.reverts(
        "Minting is closed. Context: https://research.lido.fi/t/sunsetting-lido-on-terra/2367"
    ):
        vault.submit(
            deposit_amount,
            TERRA_ADDRESS,
            "0x8bada2e",
            vault.version(),
            {"from": stranger, "value": deposit_amount},
        )

    postupgrade_terra_beth_minted_to_stranger = (
        beth_token.totalSupply() - prev_beth_total_supply
    )
    steth_minted_to_stranger_post_upgrade = (
        steth_token.totalSupply() - prev_steth_total_supply
    )

    assert postupgrade_terra_beth_minted_to_stranger == 0, "no beth was minted"
    assert steth_minted_to_stranger_post_upgrade == 0, "no steth was minted"

    #####################
    # STAGE 5. Withdraw #
    #####################

    stranger_beth_native_balance_before_bridging = beth_token.balanceOf(stranger)
    assert stranger_beth_native_balance_before_bridging == 0

    # simulate bridging from Terra
    token_bridge = accounts.at(config.wormhole_token_bridge_addr, force=True)
    beth_token.transfer(
        stranger, preupgrade_terra_beth_minted_to_stranger, {"from": token_bridge}
    )

    # confirm that native beth balance equals preupgrade Terra beth balance
    stranger_beth_native_balance_after_bridging = beth_token.balanceOf(stranger.address)
    assert (
        stranger_beth_native_balance_after_bridging
        == preupgrade_terra_beth_minted_to_stranger
    )

    stranger_steth_balance_before_withdrawal = steth_token.balanceOf(stranger.address)
    # withdraw bETH in stETH
    vault.withdraw(
        stranger_beth_native_balance_after_bridging, vault.version(), {"from": stranger}
    )

    # confirm that all bETH were withdrawn
    stranger_beth_native_balance_after_withdrawal = beth_token.balanceOf(
        stranger.address
    )
    assert stranger_beth_native_balance_after_withdrawal == 0

    # confirm that stETH balance is now stETH before + bETH withdrawn
    # it's okay to simply add up these values because withdrawal rate is normally 1 to 1
    # as there was no negative rebase
    assert steth_approx_equal(
        steth_token.balanceOf(stranger.address),
        stranger_steth_balance_before_withdrawal
        + stranger_beth_native_balance_after_bridging,
    )
