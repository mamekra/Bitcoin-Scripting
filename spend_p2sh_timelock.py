import argparse
import json
import requests
import subprocess
from requests.auth import HTTPBasicAuth
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2pkhAddress, P2shAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, Sequence
from bitcoinutils.script import Script
from bitcoinutils.constants import TYPE_ABSOLUTE_TIMELOCK
from bitcoinutils.utils import to_satoshis

#RPC call helper function 
def call_rpc(method, params=None):
    """
    Performs a direct JSON-RPC call to the Bitcoin Core node's specified wallet endpoint
    and performs a command (ex 'getblockcount')
    """
    url = "http://127.0.0.1:18443/wallet/legwallet"  
    headers = {'content-type': 'application/json'}
    payload = {
        "method": method,
        "params": params or [],
        "jsonrpc": "2.0",
        "id": 0,
    }

    response = requests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth('user', 'pass'))
    response.raise_for_status()
    result = response.json()

    if 'error' in result and result['error']:
        raise Exception(result['error'])
    return result['result']

def get_fee_rate_sat_per_byte():
    """
    Get estimated fee rate (in sat/vB) using Bitcoin Core's estimatesmartfee RPC.
    """
    try:
        result = call_rpc("estimatesmartfee")
        fee_btc_per_kvbyte = result.get('feerate')
        if fee_btc_per_kvbyte is not None:
            fee_sat_per_byte = int(fee_btc_per_kvbyte * 1e8 / 1000)
            return max(fee_sat_per_byte, 1)  
    except Exception as e:
        print("Error getting fee estimate from node:", e)

    return 10 


def get_utxos(address):
    """
    Uses the scantxoutset RPC to scan for UTXOs for a given address.
    This allows retrieving UTXOs for non-wallet addresses (e.g. manually created P2SH)
    without needing the address to be imported or watched by a wallet.
    """
    try:        
        scan_objects = [{"desc": f"addr({address})"}]
        result = call_rpc("scantxoutset", ["start", scan_objects])

        utxos = result.get("unspents", [])
        print(f"Found {len(utxos)} UTXOs.")
        return utxos

    except Exception as e:
        print("Exception during UTXO fetch:", e)
        return []

#Estimate transaction fee based on size and fee rate
def estimate_fee(num_inputs, num_outputs=1, fee_rate_sat_per_byte=10):
    """
    Estimates the transaction fee in satoshis based on input/output count and fee rate.
    This is a rough estimate using typical input/output sizes for transactions.    
    """
    tx_size = 10 + (num_inputs * 148) + (num_outputs * 34)
    return int(tx_size * fee_rate_sat_per_byte)

def main():
    setup("regtest")

    #Parse command-line arguments for transaction details
    parser = argparse.ArgumentParser()
    parser.add_argument("--privkey", required=True, help="WIF private key")
    parser.add_argument("--timelock", required=True, type=int, help="Absolute block height")
    parser.add_argument("--p2sh", required=True, help="P2SH address")
    parser.add_argument("--destination", required=True, help="Destination P2PKH address")
    args = parser.parse_args()

    #Key and script setup
    priv = PrivateKey(args.privkey)
    pub = priv.get_public_key()
    pub_hex = pub.to_hex()
    pub_hash = pub.get_address().to_hash160()

    #Construct the redeem script 
    seq = Sequence(TYPE_ABSOLUTE_TIMELOCK, args.timelock)
    redeem_script = Script([
        seq.for_script(),
        "OP_CHECKLOCKTIMEVERIFY",
        "OP_DROP",
        "OP_DUP",
        "OP_HASH160",
        pub_hash,
        "OP_EQUALVERIFY",
        "OP_CHECKSIG"
    ])

    #Search for UTXOs at the P2SH address
    p2sh_address = P2shAddress(args.p2sh).to_string()
    utxos = get_utxos(p2sh_address)
    if not utxos:
        print("No UTXOs found at the P2SH address.")
        return

    #Calculate total available input 
    total_input = sum([to_satoshis(utxo["amount"]) for utxo in utxos])

    #calculate transaction fee
    fee_rate = get_fee_rate_sat_per_byte()
    fee = estimate_fee(len(utxos), 1, fee_rate_sat_per_byte=fee_rate)
    send_amount = total_input - fee
    print(f"Fee: {fee} satoshis | Total input: {total_input} | To send: {send_amount}")

    if send_amount <= 0:
        print("Not enough balance to cover fee.")
        return

    #Create transaction inputs 
    txins = []
    sequence_bytes = (0xfffffffe).to_bytes(4, byteorder='little')

    for i, utxo in enumerate(utxos):
        txid_str = utxo["txid"]
        vout = utxo["vout"]        
        #print(f"[Input {i}] txid: {txid_str}, vout: {vout}, sequence: {sequence_bytes.hex()}")
        txins.append(TxInput(txid_str, vout, sequence=sequence_bytes))

    #Create the output to the provided destination address
    to_address = P2pkhAddress(args.destination).to_script_pub_key()
    txouts = [TxOutput(send_amount, to_address)]

    #Construct the transaction with locktime set
    locktime_bytes = args.timelock.to_bytes(4, 'little')
    tx = Transaction(txins, txouts, locktime_bytes)
    print("Unsigned raw transaction:\n", tx.serialize())

    #Sign each input using the redeem script
    for i in range(len(txins)):
        sig = priv.sign_input(tx, i, redeem_script)
        txins[i].script_sig = Script([sig, pub_hex, redeem_script.to_hex()])

    #Finalize and broadcast the signed transaction
    signed_tx = tx.serialize()
    print("Signed raw transaction:\n", signed_tx)
    print("TXID:\n", tx.get_txid())
    
    #Submit to mempool for validation and broadcast if allowed
    try:
        result = call_rpc('testmempoolaccept', [[signed_tx]])[0]
        if result['allowed']:
            print("Transaction is valid. Broadcasting...")
            txid = call_rpc('sendrawtransaction', [signed_tx])
            print("Broadcasted TXID:\n", txid)
        else:
            reason = result.get("reject-reason", "Unknown")        
            print("Transaction rejected. Reason:", reason)
    except Exception as e:
        print(f"Error during RPC validation or broadcast: {e}")

if __name__ == "__main__":
    main()
