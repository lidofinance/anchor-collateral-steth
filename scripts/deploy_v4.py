import sys
from brownie import ZERO_ADDRESS
from utils import config

try:
    from brownie import AnchorVault, interface
except ImportError:
    print("You're probably running inside Brownie console. Please call:")
    print("set_console_globals(interface=interface, AnchorVault=AnchorVault)")


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

    vault = AnchorVault.deploy(
        tx_params
    )
    vault.petrify_impl()
