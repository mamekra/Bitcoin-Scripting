from bitcoinutils.setup import setup
from bitcoinutils.transactions import Sequence
from bitcoinutils.constants import TYPE_ABSOLUTE_TIMELOCK
from bitcoinutils.keys import PublicKey, P2shAddress
from bitcoinutils.script import Script
import argparse

def main():
    
    #Parse input arguments
    parser = argparse.ArgumentParser(description='Create a P2SH address with absolute timelock + P2PKH script.')
    parser.add_argument('--timelock', required=True, type=int, help='Absolute block height for CHECKLOCKTIMEVERIFY')
    parser.add_argument('--pubkey', required=True, help='Public key in hex')
    args = parser.parse_args()

    setup("regtest")

    #Prepare public key and pubKeyHash
    pub = PublicKey(args.pubkey)
    p2pkh_hash160 = pub.get_address().to_hash160()

    #Use Sequence to encode CLTV-compatible locktime
    seq = Sequence(TYPE_ABSOLUTE_TIMELOCK, args.timelock)

    #Build redeem script
    redeem_script = Script([
        seq.for_script(),
        "OP_CHECKLOCKTIMEVERIFY",
        "OP_DROP",
        "OP_DUP",
        "OP_HASH160",
        p2pkh_hash160,
        "OP_EQUALVERIFY",
        "OP_CHECKSIG"
    ])

    #Build P2SH address from redeem script
    p2sh_addr = P2shAddress.from_script(redeem_script)

    #info
    print("=== P2SH Time-Locked Address ===")
    print("Lock until block height:", args.timelock)
    print("Redeem script (Hex):", redeem_script.to_hex())
    print("P2SH Address:", p2sh_addr.to_string())

if __name__ == "__main__":
    main()
