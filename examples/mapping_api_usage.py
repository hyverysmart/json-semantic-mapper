
import json

from src.mapping_spec import (
    propose_mappings,
    approve_mappings
)


# 读取 JSON 文件
def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# 读取已有字段目录和 Schema
source_fields = load_json("outputs/source_catalog.json")
target_fields = load_json("outputs/target_catalog.json")

source_schema = load_json("schemas/source_schema.json")
target_schema = load_json("schemas/target_schema.json")


# 生成待审核候选规则
candidates = propose_mappings(
    source_fields=source_fields,
    target_fields=target_fields,
    provider="deepseek"
)

print("待审核映射：")
print(json.dumps(candidates, ensure_ascii=False, indent=2))


# 模拟人工在其他程序中提交审核结果
# 只批准当前候选列表中存在的映射
approved_pairs = []

for mapping in candidates["mappings"]:
    print(
        "\n候选映射：",
        mapping["source"],
        "→",
        mapping["target"]
    )

    print("匹配原因：", mapping["reason"])

    while True:
        decision = input("是否批准？(y/n)：").strip().lower()

        if decision in ("y", "n"):
            break

        print("请输入 y 或 n")

    if decision == "y":
        approved_pairs.append({
            "source": mapping["source"],
            "target": mapping["target"]
        })

# 生成正式 MappingSpec
mapping_spec = approve_mappings(
    candidates=candidates,
    approved_pairs=approved_pairs,
    source_fields=source_fields,
    target_fields=target_fields,
    source_schema=source_schema,
    target_schema=target_schema
)

print("\n生成的 MappingSpec：")
print(json.dumps(mapping_spec, ensure_ascii=False, indent=2))
