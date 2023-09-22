import brownie
import utils.config as config
from brownie import reverts

"""
Vault finalize test
"""
def test_finalize_upgrade_v4_cannot_be_called_on_v4_vault(deploy_vault_and_pass_dao_vote, lido_dao_agent, stranger):
    vault = brownie.Contract.from_abi(
        "AnchorVault", config.vault_proxy_addr, brownie.AnchorVault.abi
    )

    # check vault version
    assert vault.version() == 3, "version matches"

    # there no `finalize_upgrade_v4` yet
    with reverts():
        vault.finalize_upgrade_v4({'from': lido_dao_agent})

    deploy_vault_and_pass_dao_vote()
    assert vault.version() == 4

    with reverts():
        vault.finalize_upgrade_v4({'from': stranger})

    with reverts("unexpected contract version"):
        vault.finalize_upgrade_v4({'from': lido_dao_agent})

"""
Change admin test
"""
def test_change_admin(deploy_vault_and_pass_dao_vote, stranger, admin, helpers, lido_dao_agent):
    vault = brownie.Contract.from_abi(
        "AnchorVault", config.vault_proxy_addr, brownie.AnchorVault.abi
    )
    assert vault.version() == 3
    deploy_vault_and_pass_dao_vote()
    assert vault.version() == 4

    assert vault.admin() == lido_dao_agent

    with reverts():
        vault.change_admin(stranger, {"from": stranger})

    with reverts():
        vault.change_admin(stranger, {"from": admin})

    vault.change_admin(stranger, {"from": lido_dao_agent})

    assert vault.admin() == stranger
    assert lido_dao_agent != stranger