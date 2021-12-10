import os
import sys

from brownie import network, accounts

vault_proxy_address = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
vault_ropsten_address = '0xf72b5bc0a05f15cadb6731e59c7d99c1bfbb2fab'

token_bridge_wormhole_address = '0x3ee18B2214AFF97000D974cf647E7C347E8fa585'
token_bridge_wormhole_ropsten_address = '0xF174F9A837536C449321df1Ca093Bb96948D5386'

beth_token_address = '0x707F9118e33A9B8998beA41dd0d46f38bb963FC8'
beth_token_ropsten_address = '0xA60100d5e12E9F83c1B04997314cf11685A618fF'

ust_token_address = '0xa47c8bf37f92aBed4A126BDA807A7b7498661acD'
ust_token_ropsten_address = '0x6cA13a4ab78dd7D657226b155873A04DB929A3A4'

steth_token_address = '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84'
steth_token_ropsten_address = '0xd40EefCFaB888C9159a61221def03bF77773FC19'

bridge_connector_shuttle_address = '0x513251faB2542532753972B8FE9A7b60621affaD'
bridge_connector_shuttle_ropsten_address = '0x0f49D26b45D0a9880431D33eAf7CCCb1Ebd67961'

wormhole_address = '0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B'
wormhole_ropsten_address = '0x210c5F5e2AF958B4defFe715Dc621b7a3BA888c5'

gas_price = "90 gwei"

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

