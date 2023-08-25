import sys
from brownie import accounts
from utils import config

try:
    from brownie import AnchorVault, interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface, AnchorVault=AnchorVault)")

from utils.dao import (
    create_vote,
    encode_proxy_upgrade,
    encode_finalize_upgrade_v4,
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
    # deployer = config.get_deployer_account(config.get_is_live())
    deployer = accounts.at('0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266', force=True)

    print("Deployer:", deployer)

    sys.stdout.write("Proceed? [y/n]: ")
    if not config.prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer, "max_fee": "100 gwei", "priority_fee": "2 gwei"}

    anchor_new_vault = deploy(tx_params)

    print("Vault impl", anchor_new_vault)

    # (vault_address, vote_id) = deploy_and_start_dao_vote(
    #     tx_params
    # )

    # print("Vault impl", vault_address)
    # print("Vote id", vote_id)



def deploy_and_start_dao_vote(tx_params):
    voting = interface.Voting(lido_dao_voting_addr)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    anchor_new_vault = deploy(tx_params)

    evm_script = encode_call_script([
        encode_proxy_upgrade(
            new_impl_address=anchor_new_vault,
            setup_calldata=b''
        ),
        encode_finalize_upgrade_v4()
    ])

    (vote_id, tx) = create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f"1. Update anchor vault implementation {anchor_new_vault}\n2. Increase vault version to v4",
        evm_script=evm_script,
        tx_params=tx_params
    )

    return (anchor_new_vault, vote_id)


def deploy(tx_params):
    vault = AnchorVault.deploy(
        tx_params
    )
    vault.petrify_impl(tx_params)

    return vault

def upgrade(new_address, tx_params):
    vault_proxy_addr = '0xD7fE7881cD50fc155Bc310224352A812214e1E50'
    calldata = b''
    proxy = interface.AnchorVaultProxy(vault_proxy_addr)
    proxy.proxy_upgradeTo(new_address, calldata, tx_params)

    vault = AnchorVault.at(vault_proxy_addr)
    vault.finalize_upgrade_v4(tx_params)

def transfer():
    acc1 = accounts.at('0xE3aa8298739DAa2dfa263BC6E0c2080655B0E368', True)
    lido = interface.Lido('0xd40EefCFaB888C9159a61221def03bF77773FC19')
    lido.transferFrom('0xE3aa8298739DAa2dfa263BC6E0c2080655B0E368', '0x78d6eeB8639C639316516DC004a311BF756C3640', 10000000000000000000, {'from': acc1 })
