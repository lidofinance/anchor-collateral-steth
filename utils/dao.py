from utils.evm_script import encode_call_script, EMPTY_CALLSCRIPT
from brownie import interface, AnchorVault
from utils.config import (
    lido_dao_agent_address,
    vault_proxy_addr
)

from typing import (
    Tuple,
    Sequence,
)

def create_vote(voting, token_manager, vote_desc, evm_script, tx_params):
    new_vote_script = encode_call_script([(
        voting.address,
        voting.newVote.encode_input(
            evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
            vote_desc,
            False,
            False
        )
    )])
    tx = token_manager.forward(new_vote_script, tx_params)
    vote_id = tx.events['StartVote']['voteId']
    return (vote_id, tx)


def agent_forward(call_script: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    agent = interface.Agent(lido_dao_agent_address)
    return (
        lido_dao_agent_address,
        agent.forward.encode_input(
            encode_call_script(call_script)
        )
    )

def encode_proxy_upgrade(new_impl_address: str, setup_calldata: str) -> Tuple[str, str]:
    proxy = interface.AnchorVaultProxy(vault_proxy_addr)

    return agent_forward(
        [
            (
                proxy.address,
                proxy.proxy_upgradeTo.encode_input(new_impl_address, setup_calldata),
            )
        ]
    )

def encode_bump_version() -> Tuple[str, str]:
    vault = AnchorVault.at(vault_proxy_addr)

    return agent_forward(
        [
            (
                vault.address,
                vault.bump_version.encode_input(),
            )
        ]
    )
