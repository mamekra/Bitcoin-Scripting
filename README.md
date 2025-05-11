Assignment on Bitcoin Scripting for the course 'Descentralized Technologies' in my master's degree program.

# ⛓️ Bitcoin P2SH Timelock Script (Regtest)

This project demonstrates how to create and spend from a P2SH (Pay-to-Script-Hash) Bitcoin address that includes an absolute timelock using `OP_CHECKLOCKTIMEVERIFY`, all tested on Bitcoin Core's `regtest` mode.

##  Overview

- **Script 1**: Creates a timelocked P2SH address using a given public key and locktime.
- **Script 2**: Spends from the P2SH address once the specified block height has been reached.

##  Requirements

- Bitcoin Core (≥ 0.21) with `bitcoind` and `bitcoin-cli`
- Python ≥ 3.10
- [`bitcoinutils`](https://github.com/karask/python-bitcoin-utils)
- `requests` (Python library)

---

##  Setup Instructions

### 1. Start Bitcoin in Regtest Mode

Start `bitcoind` in regtest mode:

```bash
bitcoind -regtest -daemon

### 2. Create and Load a Legacy Wallet
bitcoin-cli -regtest createwallet "legwallet" false false "" false false true
bitcoin-cli -regtest -rpcwallet=legwallet getwalletinfo

### 3. Generate a P2PKH Legacy Address
bitcoin-cli -regtest -rpcwallet=legwallet getnewaddress "" legacy
Save this address and use it as your destination address in Script 2.

### 4. Get Private and Public Key of the Address
# Replace (address) with the one you got above
bitcoin-cli -regtest -rpcwallet=legwallet dumpprivkey (address)
bitcoin-cli -regtest -rpcwallet=legwallet getaddressinfo (address)

# How to Use the Scripts
### Step 1: Run Script 1 (create_p2sh_timelock.py)
python create_p2sh_timelock.py --timelock <absolute_block_height> --pubkey <public_key>
Outputs the timelocked P2SH address.

Send funds to this address using:
bitcoin-cli -regtest -rpcwallet=legwallet sendtoaddress <P2SH_address> 0.001

### Step 2: Generate Blocks
bitcoin-cli -regtest -rpcwallet=legwallet generatetoaddress <number> <your_P2PKH_address>
Make sure current block height >= locktime set in Script 1

### Step 3: Run Script 2 (spend_p2sh_timelock.py)
python spend_p2sh_timelock.py \
  --privkey <WIF_private_key> \
  --timelock <same_timelock_used_in_script_1> \
  --p2sh <timelocked_P2SH_address> \
  --destination <your_P2PKH_address>

If the locktime has passed and fees are adequate, the transaction will be broadcasted to the network.

