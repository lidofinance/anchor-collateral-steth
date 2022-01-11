import sys

from brownie import Wei, accounts, network, RopstenMockRewardsLiquidator

from utils.config import (
    gas_price,
    get_deployer_account,
    get_env,
    get_is_live,
    prompt_bool,
    steth_token_address,
    steth_token_ropsten_address,
    ust_wormhole_token_address,
    ust_wormhole_token_ropsten_address,
    steth_vault_address,
    steth_vault_ropsten_address
)

def deploy_mock_rewards_liquidator(
    steth_token,
    ust_wrapper_token,
    steth_vault,
    ust_per_steth,
    tx_params,
    publish_source=False,
):
    liquidator = RopstenMockRewardsLiquidator.deploy(
        steth_token,
        ust_wrapper_token,
        steth_vault,
        ust_per_steth,
        tx_params,
        publish_source=publish_source,
    )

    assert liquidator.steth_token() == steth_token
    assert liquidator.ust_token() == ust_wrapper_token
    assert liquidator.steth_vault() == steth_vault
    assert liquidator.ust_per_steth() == ust_per_steth

    return liquidator


def main():
    is_live = get_is_live()
    deployer = get_deployer_account(is_live)
    net = get_env('NET', False, None, 'mainnet')

    if net == 'ropsten':
        steth_token = steth_token_ropsten_address
        steth_vault = steth_vault_ropsten_address
        ust_wrapper_token = ust_wormhole_token_ropsten_address
    else:
        steth_token = steth_token_address
        steth_vault = steth_vault_address
        ust_wrapper_token = ust_wormhole_token_address

    ust_per_steth = 100 * 10**6
    admin_address = '0x02139137fdd974181a49268d7b0ae888634e5469'

    print('Deployer:', deployer)
    print('stETH token:', steth_token)
    print('UST token (wrapped):', ust_wrapper_token)
    print('stETH vault:', steth_vault)
    print('UST per stETH:', ust_per_steth)
    print('Gas price:', gas_price)

    sys.stdout.write('Proceed? [y/n]: ')

    if not prompt_bool():
        print('Aborting')
        return

    liquidator = deploy_mock_rewards_liquidator(
        steth_token,
        ust_wrapper_token,
        steth_vault,
        Wei(ust_per_steth),
        tx_params={'from': deployer, 'gas_price': Wei(gas_price), 'required_confs': 1},
        publish_source=False
    )

    liquidator.set_admin(admin_address, {'from': deployer, 'gas_price': Wei(gas_price)})

    assert liquidator.admin() == admin_address
