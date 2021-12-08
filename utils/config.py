import os
import sys

from brownie import network, accounts

vault_proxy_address = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
token_bridge_wormhole_address = '0x3ee18B2214AFF97000D974cf647E7C347E8fa585'

vault_ropsten_address = '0xf72b5bc0a05f15cadb6731e59c7d99c1bfbb2fab'
token_bridge_wormhole_ropsten_address = '0xF174F9A837536C449321df1Ca093Bb96948D5386'

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

