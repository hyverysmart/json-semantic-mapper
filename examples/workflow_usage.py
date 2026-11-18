import json
from src.workflow_runner import run_workflow


# 读取 JSON 文件
def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# 读取原有的数据和配置
source_data = load_json("examples/student_input.json")
mapping_spec = load_json("outputs/mapping_spec.json")
source_schema = load_json("schemas/source_schema.json")
target_schema = load_json("schemas/target_schema.json")

# 用户编写的 Python 节点代码
code = """
output = dict(input_data)
output["grade"] = round(input_data["grade"])
"""

# 执行完整的数据处理流程
result = run_workflow(
    source_data,
    mapping_spec,
    source_schema,
    target_schema,
    code
)

# 显示最终结果
print("最终转换结果：")
print(json.dumps(result, ensure_ascii=False, indent=2))