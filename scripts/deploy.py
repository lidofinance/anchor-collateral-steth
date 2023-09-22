import sys
from brownie import accounts
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
    publish_source = config.get_is_live()

    print("Deployer\t", deployer)
    print("Publish source\t", publish_source)

    sys.stdout.write("Proceed? [y/n]: ")
    if not config.prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer}

    if config.get_is_live():
        tx_params["priority_fee"] = "2 gwei"

    anchor_new_vault = deploy(tx_params, publish_source)

    print("Vault address\t", anchor_new_vault)
    print("Vault petrified\t", anchor_new_vault.version() == 2**256-1)


def deploy(tx_params, publish_source=False):
    vault = AnchorVault.deploy(tx_params, publish_source=publish_source)
    return vault
