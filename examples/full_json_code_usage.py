import json

from src.mapper_service import run_code_node


# 用户提供的完整 JSON 数据
input_data = {
    "studentId": 2002,
    "studentName": "Amy",
    "score": 88.5
}


# 用户自己编写的数据转换代码
code = """
output = {
    "id": input_data["studentId"],
    "name": input_data["studentName"],
    "grade": round(input_data["score"])
}
"""

# 读取目标 JSON Schema
with open("schemas/target_schema.json", "r", encoding="utf-8") as file:
    target_schema = json.load(file)

# 执行用户编写的 Python 转换代码
result = run_code_node(
    input_data=input_data,
    code=code,
    target_schema=target_schema
)

# 显示最终转换结果
print("代码节点执行结果：")
print(json.dumps(result, ensure_ascii=False, indent=2))
