import sys
from brownie import ZERO_ADDRESS
from utils import config

try:
    from brownie import AnchorVault, interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface, AnchorVault=AnchorVault)")

from utils.dao import (
    create_vote,
    encode_proxy_upgrade,
    encode_bump_version,
    encode_call_script
)

from utils.config import (
    lido_dao_voting_addr,
    lido_dao_token_manager_address
)

def set_console_globals(**kwargs):
    global AnchorVault
    global interface
    AnchorVault = kwargs['AnchorVault']
    interface = kwargs['interface']


def main():
    deployer = config.get_deployer_account(config.get_is_live())
    
    print("Deployer:", deployer)

    sys.stdout.write("Proceed? [y/n]: ")
    if not config.prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer, "max_fee": "100 gwei", "priority_fee": "2 gwei"}

    (vault_address, vote_id) = deploy_and_start_dao_vote(
        tx_params
    )

    print("Vault impl", vault_address)
    print("Vote id", vote_id)



def deploy_and_start_dao_vote(tx_params):
    voting = interface.Voting(lido_dao_voting_addr)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    anchor_new_vault = deploy(tx_params)

    evm_script = encode_call_script([
        encode_proxy_upgrade(
            new_impl_address=anchor_new_vault,
            setup_calldata=b''
        ),
        encode_bump_version()
    ])

    (vote_id, tx) = create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f"1. Update anchor vault {anchor_new_vault}\n2. Increase vault version",
        evm_script=evm_script,
        tx_params=tx_params
    )

    return (anchor_new_vault, vote_id)


def deploy(tx_params): 
    vault = AnchorVault.deploy(
        tx_params
    )
    vault.petrify_impl()

    return vault
