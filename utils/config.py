import os
import sys

from brownie import network, accounts

# external addresses
ust_token_addr = '0xa693B19d2931d498c5B318dF961919BB4aee87a5'
steth_token_addr = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
lido_dao_voting_addr = '0x2e59A20f205bB85a89C53f1936454680651E618e'
wormhole_addr = '0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B'
wormhole_token_bridge_addr = '0x3ee18B2214AFF97000D974cf647E7C347E8fa585'
lido_dao_agent_address = '0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c'
lido_dao_token_manager_address = '0xf73a1260d222f447210581DDf212D915c09a3249'
lido_accounting_oracle = '0x852deD011285fe67063a08005c71a85690503Cee'
lido_accounting_oracle_hash_consensus = '0xD624B08C83bAECF0807Dd2c6880C3154a5F0B288'

# integration addresses
vault_proxy_addr = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
# vault_impl_addr = '0x777CeE2a757bD958939d3Fbfd8af17AA5A34051D'
vault_impl_addr = '0x07BE9BB2B1789b8F5B2f9345F18378A8B036A171'
beth_token_addr = '0x707F9118e33A9B8998beA41dd0d46f38bb963FC8'
bridge_connector_addr = '0x2618e94a7F6118acED2E51e0a05da43D2e2eD40C'
rewards_liquidator_addr = '0xE3c8A4De3b8A484ff890a38d6D7B5D278d697Fb7'
insurance_connector_addr = '0x2BDfD3De0fF23373B621CDAD0aD3dF1580efE701'
dev_multisig_addr = '0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0'
vault_liquidations_admin_addr = '0x1A9967A7b0c3dd39962296E53F5cf56471385dF2'

# Terra addresses
terra_rewards_distributor_addr = '0x2c4ab12675bccba793170e21285f8793611135df'

# intergation params
rew_liq_max_steth_eth_price_difference_percent = 3
rew_liq_max_eth_usdc_price_difference_percent = 3
rew_liq_max_usdc_ust_price_difference_percent = 100
rew_liq_max_steth_ust_price_difference_percent = 100

# Wormhole migration addresses
wh_migrator_addr = '0x02454e9dd8D8d49d4A20Df27F5E1c3a51b4c1C27'
wh_migration_executor_addr = '0xe19fc582dd93FA876CF4061Eb5456F310144F57b'

ldo_vote_executors_for_tests = [
    '0x3e40d73eb977dc6a537af587d48316fee66e9c8c',
    '0xb8d83908aab38a159f3da47a59d84db8e1838712',
    '0xa2dfc431297aee387c05beef507e5335e684fbcd'
]

def get_is_live():
    return network.show_active() != "development"


def get_deployer_account(is_live):
    if is_live and "DEPLOYER" not in os.environ:
        raise EnvironmentError(
            "Please set DEPLOYER env variable to the deployer account name"
        )

    return accounts.load(os.environ['DEPLOYER']) if is_live else accounts[0]


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


def progress(_cur, _max):
    p = round(100*_cur/_max)
    b = f"Progress: {p}% - ["+"."*int(p/5)+" "*(20-int(p/5))+"]"
    print(b, end="\r")