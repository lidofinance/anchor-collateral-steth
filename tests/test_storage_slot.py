from brownie.network import web3
from hexbytes import HexBytes
import utils.config as config

def test_storage_slots(deploy_vault_and_pass_dao_vote):

    no_liquidation_interval = HexBytes('0x')
    restricted_liquidation_interval = HexBytes(26 * 60 * 60)
    last_liquidation_time = web3.eth.get_storage_at(config.vault_proxy_addr, 10)
    last_liquidation_share_price = web3.eth.get_storage_at(config.vault_proxy_addr, 11)
    last_liquidation_shares_burnt = HexBytes('0x')
    version = HexBytes(3)
    operations_allowed = HexBytes(True)
    total_beth_refunded = HexBytes(443561118570000000000)

    #storage slots
    #we are added the to_32bytes function, because now the get_storage_at method returns 32 bytes
    slots = []

    slots.append(to_32bytes(HexBytes(config.lido_dao_agent_address)))          #slot0 admin
    slots.append(to_32bytes(HexBytes(config.beth_token_addr)))                 #slot1 beth_token
    slots.append(to_32bytes(HexBytes(config.steth_token_addr)))                #slot2 steth_token
    slots.append(to_32bytes(HexBytes(config.bridge_connector_addr)))           #slot3 bridge_connector
    slots.append(to_32bytes(HexBytes(config.rewards_liquidator_addr)))         #slot4 rewards_liquidator
    slots.append(to_32bytes(HexBytes(config.insurance_connector_addr)))        #slot5 insurance_connector
    slots.append(to_32bytes(HexBytes(config.terra_rewards_distributor_addr)))  #slot6 anchor_rewards_distributor
    slots.append(to_32bytes(HexBytes(config.vault_liquidations_admin_addr)))   #slot7 liquidations_admin
    slots.append(to_32bytes(no_liquidation_interval))                          #slot8 no_liquidation_interval
    slots.append(to_32bytes(restricted_liquidation_interval))                  #slot9 restricted_liquidation_interval
    slots.append(to_32bytes(last_liquidation_time))                            #slot10 last_liquidation_time
    slots.append(to_32bytes(last_liquidation_share_price))                     #slot11 last_liquidation_share_price
    slots.append(to_32bytes(last_liquidation_shares_burnt))                    #slot12 last_liquidation_shares_burnt
    slots.append(to_32bytes(version))                                          #slot13 version
    slots.append(to_32bytes(HexBytes(config.dev_multisig_addr)))               #slot14 emergency_admin
    slots.append(to_32bytes(operations_allowed))                               #slot15 operations_allowed
    slots.append(to_32bytes(total_beth_refunded))                              #slot16 total_beth_refunded

    #slots which we are change during the upgrade
    new_slots = {
        3: { 'old': slots[3], 'new': to_32bytes(HexBytes('0x')) },
        4: { 'old': slots[4], 'new': to_32bytes(HexBytes('0x')) },
        5: { 'old': slots[5], 'new': to_32bytes(HexBytes('0x')) },
        6: { 'old': slots[6], 'new': to_32bytes(HexBytes('0x')) },
        7: { 'old': slots[7], 'new': to_32bytes(HexBytes('0x')) },
        8: { 'old': slots[8], 'new': to_32bytes(HexBytes('0x')) },
        9: { 'old': slots[9], 'new': to_32bytes(HexBytes('0x')) },
        10: { 'old': slots[10], 'new': to_32bytes(HexBytes('0x')) },
        11: { 'old': slots[11], 'new': to_32bytes(HexBytes('0x')) },
        12: { 'old': slots[12], 'new': to_32bytes(HexBytes('0x')) },
        13: {'old': slots[13], 'new': to_32bytes(HexBytes(4)) },
        14: {'old': slots[14], 'new': to_32bytes(HexBytes('0x'))}
    }

    #save previous storage slots
    prev_slots = []
    for index, slot in enumerate(slots):
        data = web3.eth.get_storage_at(config.vault_proxy_addr, index)
        prev_slots.append(data)

        assert data == slot , "invalid previous slot"

    #upgrade implementation
    deploy_vault_and_pass_dao_vote()

    #check new storage slots
    for index, slot in enumerate(prev_slots):
        data = web3.eth.get_storage_at(config.vault_proxy_addr, index)

        #we will change  slots after upgrade
        if index in list(new_slots.keys()):
            assert slot == new_slots[index]['old']
            assert data == new_slots[index]['new']
        else:
             #check previous value
            assert data == slot, "invalid previous slot after upgrade"

            #check initial value
            assert data == slots[index], "invalid initial value"

def to_32bytes(value: HexBytes):
    if len(value) == 0:
        return HexBytes("0x")
    return HexBytes("0x" + value.hex()[2:].zfill(64))