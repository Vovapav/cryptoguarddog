import requests
import time
from web3 import Web3
from typing import List
import yaml

class CryptoGuardDog:
    def __init__(self, config_path='config.yaml'):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        self.addresses = [Web3.to_checksum_address(a) for a in config['addresses']]
        self.whitelist = [Web3.to_checksum_address(a) for a in config['whitelist']]
        self.eth_threshold = config['eth_threshold']
        self.telegram_token = config['telegram_bot_token']
        self.telegram_chat_id = config['telegram_chat_id']
        self.poll_interval = config.get('poll_interval', 30)
        self.web3 = Web3(Web3.HTTPProvider(config['infura_url']))
        self.last_block = self.web3.eth.block_number

    def send_alert(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            'chat_id': self.telegram_chat_id,
            'text': message
        }
        requests.post(url, data=data)

    def check_new_transactions(self):
        current_block = self.web3.eth.block_number
        for block_num in range(self.last_block + 1, current_block + 1):
            block = self.web3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                if tx['to'] in self.addresses or tx['from'] in self.addresses:
                    self.analyze_transaction(tx)
        self.last_block = current_block

    def analyze_transaction(self, tx):
        from_addr = tx['from']
        to_addr = tx['to']
        value_eth = self.web3.from_wei(tx['value'], 'ether')
        gas_price_gwei = self.web3.from_wei(tx['gasPrice'], 'gwei')

        alerts = []

        if value_eth > self.eth_threshold:
            alerts.append(f"🚨 Высокая сумма: {value_eth:.4f} ETH")

        if to_addr and to_addr not in self.whitelist:
            alerts.append(f"⚠️ Адрес получателя не в белом списке: {to_addr}")

        if tx['input'] != '0x':
            alerts.append("⚙️ Транзакция взаимодействует со смарт-контрактом")

        if gas_price_gwei > 100:
            alerts.append(f"⛽ Высокая комиссия: {gas_price_gwei:.2f} GWEI")

        if alerts:
            msg = f"💸 Обнаружена транзакция:\n" \
                  f"From: {from_addr}\nTo: {to_addr}\nValue: {value_eth:.4f} ETH\n" \
                  f"Tx Hash: https://etherscan.io/tx/{tx['hash'].hex()}\n\n" + "\n".join(alerts)
            self.send_alert(msg)

    def run(self):
        print("🔍 CryptoGuardDog начал наблюдение...")
        while True:
            try:
                self.check_new_transactions()
            except Exception as e:
                print(f"[!] Ошибка: {e}")
            time.sleep(self.poll_interval)
