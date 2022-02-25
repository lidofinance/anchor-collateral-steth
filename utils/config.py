import os
import sys

from brownie import network, accounts

# external addresses
ust_token_addr = '0xa693B19d2931d498c5B318dF961919BB4aee87a5'
steth_token_addr = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
lido_dao_voting_addr = '0x2e59A20f205bB85a89C53f1936454680651E618e'
lido_dao_agent_addr = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
selfowned_steth_burner_addr = '0x1e0C8542A59c286e73c30c45612d9C3a674A6cbC'
wormhole_addr = '0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B'
wormhole_token_bridge_addr = '0x3ee18B2214AFF97000D974cf647E7C347E8fa585'

# intergration addresses
vault_proxy_addr = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
vault_impl_addr = '0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171'
beth_token_addr = '0x707F9118e33A9B8998beA41dd0d46f38bb963FC8'
bridge_connector_addr = '0x2618e94a7F6118acED2E51e0a05da43D2e2eD40C'
rewards_liquidator_addr = '0xE3c8A4De3b8A484ff890a38d6D7B5D278d697Fb7'
insurance_connector_addr = '0x714E3BcddBdC2045Bd3BE35c8642885470b25b11'
dev_multisig_addr = '0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0'
vault_liquidations_admin_addr = '0x1A9967A7b0c3dd39962296E53F5cf56471385dF2'

# Terra addresses
terra_rewards_distributor_addr = '0x2c4ab12675bccba793170e21285f8793611135df'

# intergation params
rew_liq_max_steth_eth_price_difference_percent = 1.5
rew_liq_max_eth_usdc_price_difference_percent = 3
rew_liq_max_usdc_ust_price_difference_percent = 3
rew_liq_max_steth_ust_price_difference_percent = 5

# Wormhole migration addresses
wh_migrator_addr = '0x02454e9dd8D8d49d4A20Df27F5E1c3a51b4c1C27'
wh_migration_executor_addr = '0xe19fc582dd93FA876CF4061Eb5456F310144F57b'


def get_is_live():
    return network.show_active() != "development"


def get_deployer_account(is_live):
    if is_live and "DEPLOYER" not in os.environ:
        raise EnvironmentError(
            "Please set DEPLOYER env variable to the deployer account name"
        )

    return accounts.load(os.environ["DEPLOYER"]) if is_live else accounts[0]


def get_env(name, is_required=True, message=None, default=None):
    if name not in os.environ:
        if is_required:
            raise EnvironmentError(message or f'Please set {name} env variable')
        else:
            return default

    return os.environ[name]


def prompt_bool():
    choice = input().lower()

    if choice in {"yes", "y"}:
        return True

    if choice in {"no", "n"}:
        return False

    sys.stdout.write("Please respond with 'yes' or 'no'")
