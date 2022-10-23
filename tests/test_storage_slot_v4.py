import enum
import pytest
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
    slots = []
    
    slots.append(HexBytes(config.lido_dao_agent_address))          #slot0 admin
    slots.append(HexBytes(config.beth_token_addr))                 #slot1 beth_token
    slots.append(HexBytes(config.steth_token_addr))                #slot2 steth_token
    slots.append(HexBytes(config.bridge_connector_addr))           #slot3 bridge_connector
    slots.append(HexBytes(config.rewards_liquidator_addr))         #slot4 rewards_liquidator
    slots.append(HexBytes(config.insurance_connector_addr))        #slot5 insurance_connector
    slots.append(HexBytes(config.terra_rewards_distributor_addr))  #slot6 anchor_rewards_distributor
    slots.append(HexBytes(config.vault_liquidations_admin_addr))   #slot7 liquidations_admin
    slots.append(no_liquidation_interval)                          #slot8 no_liquidation_interval
    slots.append(restricted_liquidation_interval)                  #slot9 restricted_liquidation_interval
    slots.append(last_liquidation_time)                            #slot10 last_liquidation_time
    slots.append(last_liquidation_share_price)                     #slot11 last_liquidation_share_price
    slots.append(last_liquidation_shares_burnt)                    #slot12 last_liquidation_shares_burnt
    slots.append(version)                                          #slot13 version
    slots.append(HexBytes(config.dev_multisig_addr))               #slot14 emergency_admin
    slots.append(operations_allowed)                               #slot15 operations_allowed
    slots.append(total_beth_refunded)                              #slot16 total_beth_refunded

    #save previous storage slots
    prev_slots = []
    for index, slot in enumerate(slots):
        data = web3.eth.get_storage_at(config.vault_proxy_addr, index)
        prev_slots.append(data)

        assert slot == data

    #upgrade implementation    
    deploy_vault_and_pass_dao_vote()

    #check new storage slots
    for index, slot in enumerate(prev_slots):
        data = web3.eth.get_storage_at(config.vault_proxy_addr, index)

        if index == 13:
            assert slot == HexBytes(3) #previous version == 3
            assert data == HexBytes(4) #new version == 4
        else:
             #check previous value
            assert data == slot

            #check initial value
            assert data == slots[index]

       
        
