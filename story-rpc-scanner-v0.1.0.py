import requests
from requests import RequestException, Timeout
from multiprocessing.dummy import Pool as ThreadPool
import yaml
import ipaddress
import re
import json
from tabulate import tabulate
from pathlib import Path
import os
from datetime import datetime
import csv
import html
import requests
import json

if not os.path.exists('results'):
    os.makedirs('results')


def filter_private_ip(ip_lst) -> set:
    print("FILTERING PRIVATE IPs")
    return {ip for ip in ip_lst if not ipaddress.ip_address(ip).is_private}


def write_to_file(file_name_: str, write_this, mode: str = "a"):
    with open(file_name_, mode) as file_:
        if isinstance(write_this, (list, set)):
            file_.write("\n".join(write_this) + "\n")
        else:
            file_.write(write_this + "\n")

def request_get(url_: str):
    headers_ = {"accept": "application/json"}
    try:
        req = requests.get(url=url_, headers=headers_, timeout=provider_timeout)
        if req.status_code == 200:
            return req.text
    except (RequestException, Timeout, Exception):
        return "request_get error"

def get_genesis_ips():
    if not Path(genesis_file_name).is_file():
        print(f'-> {genesis_file_name} NOT FOUND - trying to download it from {genesis_file_url}')
        genesis_ips = request_get(genesis_file_url)
        ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", str(genesis_ips))
        filtered = filter_private_ip(ips)
        result = {f'http://{n}:26657' for n in filtered}
        write_to_file(genesis_file_name, result, 'w')
    else:
        print(f'-> READING IPs from genesis file {genesis_file_name}')
        with open(genesis_file_name, 'r') as gen_file:
            result = set(gen_file.read().splitlines())
    return result

def get_peers_via_rpc(provider_url_: str):
    try:
        peers = request_get(f'{provider_url_}/net_info')
        if "error" in str(peers):
            return set()
        peers = json.loads(peers)["result"]["peers"]
        return {f'http://{p["remote_ip"]}:{p["node_info"]["other"]["rpc_address"].split(":")[-1] or "26657"}' 
                for p in peers if p["node_info"]["network"] == "iliad-0"}
    except Exception:
        return set()

def get_vuln_validators(validator_url_: str):
    try:
        node_data = json.loads(request_get(f'{validator_url_}/status'))
        if 'error' in str(node_data) or 'jsonrpc' not in str(node_data):
            return 'rpc_not_available'
        
        node_data = node_data["result"]
        if node_data["node_info"]["network"] != "iliad-0":
            return 'rpc_not_available'
        
        voting_power = int(node_data["validator_info"]["voting_power"])
        moniker = str(node_data["node_info"]["moniker"])
        current_block = int(node_data["sync_info"]["latest_block_height"])
        
        indexer_status = json.loads(request_get(f'{validator_url_}/status'))["result"]["node_info"]["other"]["tx_index"]
        earliest_block = json.loads(request_get(f'{validator_url_}/block?height=1'))["result"]["block"]["header"]["height"]
        
        block_range = f"{earliest_block}-{current_block}"
        return f'{moniker},{validator_url_},{block_range},{voting_power},{indexer_status}'
    except:
        return 'rpc_not_available'

def format_node_data(node, index):
    moniker, endpoint, block_height, voting_power, tx_index = node[:5]
    is_validator = int(voting_power) > 0
    validator_status = "Yes (❗️)" if is_validator else "No"
    indexer_status = "✅ on" if tx_index.lower() == 'on' else "off"
    scan_time = datetime.utcnow().strftime("%m/%d %H:%M")
    return [index, moniker, endpoint, block_height, voting_power, indexer_status, validator_status, scan_time]

if __name__ == "__main__":
    print("==== STORY RPC Scanner | J•Node | www.josephtran.xyz | Version: v0.1.0 ====")

    c = yaml.safe_load(open('config.yml', encoding='utf8'))
    rpc_file_name = str(c["rpc_file_name"])
    genesis_file_url = str(c["genesis_file_url"])
    genesis_file_name = 'genesis_ips.txt'
    threads_count = int(c["threads_count"])
    provider_timeout = int(c["provider_timeout"])

    rpc_provider_lst = set(open(rpc_file_name, "r").read().splitlines()) | get_genesis_ips()

    print(f'--> SEARCHING FOR PEER IPs AND THEIR RPC PORTs')
    pool = ThreadPool(threads_count)
    new_rpc = set()
    while True:
        new_peers = pool.map(get_peers_via_rpc, rpc_provider_lst)
        new_peers = set().union(*new_peers) - rpc_provider_lst
        if not new_peers:
            break
        new_rpc |= new_peers
        rpc_provider_lst |= new_peers

    rpc_provider_lst |= new_rpc
    print(f'Found {len(rpc_provider_lst)} peers')

    print(f'---> SEARCHING FOR VULNERABLE VALIDATORS (where RPC port is opened and voting power > 0)')
    valid_rpc = set(pool.map(get_vuln_validators, rpc_provider_lst)) - {'rpc_not_available'}

    sorted_validators = sorted(
        [node.split(',') for node in valid_rpc],
        key=lambda x: (-int(x[3]), x[4] != 'on')  
    )

    all_rpc_data = [format_node_data(node, index) for index, node in enumerate(sorted_validators, start=1)]

    headers = ['No.', 'Moniker', 'Endpoint', 'Block Height', 'Voting Power', 'TX Index', 'Validator', 'Scan Time']
    print(tabulate(all_rpc_data, headers=headers, tablefmt="grid", numalign="left"))

    validator_data = [row for row in all_rpc_data if row[6] == "Yes (❗️)"]
    total_affected_stake = sum(int(row[4]) for row in validator_data)
    total_validators = len(validator_data)
    total_nodes = len(all_rpc_data)

    print(f'TOTAL VULNERABLE VALIDATORS: {total_validators} | TOTAL AFFECTED STAKE: {total_affected_stake}')
    print(f'TOTAL RPC NODES: {total_nodes}')

    with open('results/vulnerable_validators.csv', 'w', newline='') as csvfile:
        csv.writer(csvfile).writerows([headers] + validator_data)

    with open('results/valid_rpc.csv', 'w', newline='') as csvfile:
        csv.writer(csvfile).writerows([headers] + all_rpc_data)

    print(f"-----------------------------------------------------------------------------------------")
    print(f"All valid RPC endpoints have been saved to: {os.path.join('results', 'valid_rpc.csv')}")
    print("DONE")
