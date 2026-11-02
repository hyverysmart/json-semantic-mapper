
import os
import requests


# 从环境变量读取 API Key
api_key = os.environ.get("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("未设置 DEEPSEEK_API_KEY")


# 查询账户余额
response = requests.get(
    "https://api.deepseek.com/user/balance",
    headers={
        "Authorization": f"Bearer {api_key}"
    },
    timeout=30
)

response.raise_for_status()

balance = response.json()

print("是否有可用余额：", balance["is_available"])

for item in balance["balance_infos"]:
    print("货币：", item["currency"])
    print("总余额：", item["total_balance"])
    print("赠送余额：", item["granted_balance"])
    print("充值余额：", item["topped_up_balance"])
