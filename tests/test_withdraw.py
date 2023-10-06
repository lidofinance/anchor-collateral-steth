import math
import brownie
import pytest
import utils.config as config

from brownie import bEth, reverts
from utils.beth import beth_holders, CSV_DOWNLOADED_AT_BLOCK
from utils.helpers import ETH

STETH_ERROR_MARGIN = 2

@pytest.fixture(scope="module")
def steth_approx_equal():
    def equal(steth_amount_a, steth_amount_b):
        return math.isclose(
            a=steth_amount_a, b=steth_amount_b, abs_tol=STETH_ERROR_MARGIN
        )

    return equal

def test_withdraw_not_working(
    deploy_vault_and_pass_dao_vote,
    accounts
):
    beth_token = bEth.at(config.beth_token_addr)

    vault = brownie.Contract.from_abi(
        "AnchorVault", config.vault_proxy_addr, brownie.AnchorVault.abi
    )

    #deploy vault, run and pass vote
    deploy_vault_and_pass_dao_vote()

    [holder_address, _, _] = beth_holders[2]

    holder_account = accounts.at(holder_address, True)

    # not using balances from csv, since they may change
    beth_balance = beth_token.balanceOf(holder_account.address)

    with reverts():
        vault.withdraw(
                beth_balance + 1, vault.version(), holder_account, {"from": holder_account}
        )

    vault.withdraw(
        beth_balance, vault.version(), holder_account, {"from": holder_account}
    )


#@pytest.mark.skip(reason="test working only at 17965130 block")
@pytest.mark.parametrize("rebase_coeff", [0, 1_000, -1_000])
def test_withdraw_using_actual_holders(
    lido_oracle_report, rebase_coeff,
    accounts, steth_token, deploy_vault_and_pass_dao_vote, steth_approx_equal
):
    """
    @dev Due to an incident on 2022-01-26, a number of bETH tokens were effectively burned
         by bridging to an unreachable address on Terra. These tokens are forever held by the
         Wormhole token bridge address. The corresponding stETH tokens were later withdrawn
         from the `AnchorVault` contract by the DAO and refunded to the original depositors.

         The amount of burned bETH that was subsequently refunded is accessible by calling
         `AnchorVault.total_beth_refunded()` function.

         See: https://github.com/lidofinance/anchor-collateral-steth/pull/19

         Tx 1: 0xc875f85f525d9bc47314eeb8dc13c288f0814cf06865fc70531241e21f5da09d
         bETH burned: 4449999990000000000
         Tx 2: 0x7abe086dd5619a577f50f87660a03ea0a1934c4022cd432ddf00734771019951
         bETH burned: 439111118580000000000
    """

    #check block number for downloaded file
    # assert web3.eth.block_number == CSV_DOWNLOADED_AT_BLOCK, "Invalid block number to check holders"

    BETH_BURNED = 4449999990000000000 + 439111118580000000000

    vault = brownie.Contract.from_abi(
        "AnchorVault", config.vault_proxy_addr, brownie.AnchorVault.abi
    )

    beth_token = bEth.at(config.beth_token_addr)

    before_vault_version = vault.version()

    deploy_vault_and_pass_dao_vote()

    if rebase_coeff != 0:
        lido_oracle_report(cl_diff=ETH(rebase_coeff))

    #vault balance
    steth_vault_balance = steth_token.balanceOf(vault.address)
    beth_total_supply = beth_token.totalSupply()
    total_beth_refunded = vault.total_beth_refunded()
    beth_balance = beth_total_supply - total_beth_refunded

    #calculate withdrawal rate
    rate = 1
    if steth_vault_balance < beth_balance:
        rate = steth_vault_balance / beth_balance

    print('')
    print('steth_vault_balance', steth_vault_balance)
    print('beth_total_supply', beth_total_supply)
    print('total_beth_refunded', total_beth_refunded)
    print('beth_balance', beth_balance)
    print('rate', rate)
    print('')

    prev_beth_total_supply = beth_token.totalSupply()

    withdrawn = 0

    count = len(beth_holders)
    print("Total holders", len(beth_holders))

    # current version
    after_vault_version = vault.version()
    assert before_vault_version != after_vault_version, "version is not changed"

    i = 0
    for holder in beth_holders:
        i += 1

        config.progress(i, count)

        [holder_address, _, _] = holder

        holder_account = accounts.at(holder_address, True)

        # not using balances from csv, since they may change
        prev_beth_balance = beth_token.balanceOf(holder_account)
        prev_steth_balance = steth_token.balanceOf(holder_account)

        is_wormhole = holder_account.address == config.wormhole_token_bridge_addr

        withdraw_amount = prev_beth_balance

        if is_wormhole:
            withdraw_amount = prev_beth_balance - BETH_BURNED

        vault.withdraw(
            withdraw_amount, after_vault_version, holder_account, {"from": holder_account}
        )

        withdrawn += withdraw_amount

        assert beth_token.balanceOf(holder_account) == prev_beth_balance - withdraw_amount
        assert steth_approx_equal(
            steth_token.balanceOf(holder_account),
            prev_steth_balance + withdraw_amount * rate,
        )

    assert beth_token.totalSupply() == prev_beth_total_supply - withdrawn
    assert beth_token.totalSupply() == BETH_BURNED