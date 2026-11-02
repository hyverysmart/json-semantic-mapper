import json
import hashlib

def load_json(file_path):
    with open(file_path,"r",encoding='utf-8') as file:
        return json.load(file)

rule_candidates=load_json(
    "outputs/candidate_mappings.json"
)
mock_result=load_json(
    "outputs/mock_llm_candidates.json"
)

mock_candidates=mock_result["mappings"]
all_candidates=rule_candidates+mock_candidates
print("待审核的候选映射：")

for index,mapping in enumerate(all_candidates,start=1):
    print(
        index,
        mapping["source"],
        "→",
        mapping["target"],
        "原因:",
        mapping["reason"]
    )

approved_mappings=[]
rejected_mappings=[]
approved_targets=set()

for mapping in all_candidates:
    print("\n待匹配")
    print(mapping["source"],"→",mapping["target"])
    print("匹配原因：",mapping["reason"])

    decision=input("是否批准?(y/n):").strip().lower()


    if decision == "y":
        target_path = mapping["target"]
        if target_path in approved_targets:
            print(f"冲突：目标字段 {target_path} 已经存在批准的映射")
            rejected_mappings.append(mapping)
            print("本条因冲突被拒绝")
        else:
            approved_mappings.append(mapping)
            approved_targets.add(target_path)
            print("已批准")
    elif decision =="n":
        rejected_mappings.append(mapping)
        print("已拒绝")
    else:
        print("输入无效，本条暂不批准")
print("\n审核结果：")
print("批准数量：",len(approved_mappings))
print("拒绝数量:",len(rejected_mappings))


review_result = {
    "generation_method": "mock",
    "approved": approved_mappings,
    "rejected": rejected_mappings
}

with open("outputs/mapping_review.json", "w", encoding="utf-8") as file:
    json.dump(review_result, file, ensure_ascii=False, indent=2)
print("人工审核结果已保存")

review_data = load_json("outputs/mapping_review.json")
approved = review_data["approved"]
print("\n准备生成 MappingSpec，批准映射数量：", len(approved))

source_catalog = load_json("outputs/source_catalog.json")
target_catalog = load_json("outputs/target_catalog.json")

mapping_rules = []
for mapping in approved:
    rule = {
        "source_id": "student_source",
        "source_path": mapping["source"],
        "target_path": mapping["target"],
        "operation": "copy",
        "array_scope": None
    }

    mapping_rules.append(rule)


def schema_fingerprint(schema):
    schema_text = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        schema_text.encode("utf-8")
    ).hexdigest()

source_schema = load_json("schemas/source_schema.json")
target_schema = load_json("schemas/target_schema.json")

source_hash = schema_fingerprint(source_schema)
target_hash = schema_fingerprint(target_schema)


mapping_spec = {
    "version": "1.0",
    "source_ids": ["student_source"],
    "schema_fingerprints": {
        "student_source": source_hash,
        "target": target_hash
    },
    "review_status": "approved",
    "generation_method": "rule_and_mock",
    "mappings": mapping_rules
}

with open("outputs/mapping_spec.json", "w", encoding="utf-8") as file:
    json.dump(mapping_spec, file, ensure_ascii=False, indent=2)

print("\nMappingSpec 已生成：outputs/mapping_spec.json")
print("规则数量：", len(mapping_rules))

def verify_schema_fingerprints(mapping_spec, source_schema, target_schema):

    saved_hashes = mapping_spec["schema_fingerprints"]

    current_source_hash = schema_fingerprint(source_schema)
    current_target_hash = schema_fingerprint(target_schema)

    if saved_hashes["student_source"] != current_source_hash:
        raise ValueError("源 Schema 已发生变化，MappingSpec 需要重新审核")

    if saved_hashes["target"] != current_target_hash:
        raise ValueError("目标 Schema 已发生变化，MappingSpec 需要重新审核")

    return True

saved_spec = load_json("outputs/mapping_spec.json")

verify_schema_fingerprints(
    saved_spec,
    source_schema,
    target_schema
)

print("MappingSpec 的 Schema 指纹验证通过")

def validate_approved_mappings(approved, source_catalog, target_catalog):
    source_dict = {}
    target_dict = {}

    for field in source_catalog:
        source_dict[field["path"]] = field

    for field in target_catalog:
        target_dict[field["path"]] = field

    used_targets = set()

    for mapping in approved:
        source_path = mapping["source"]
        target_path = mapping["target"]

        if source_path not in source_dict:
            raise ValueError(f"源字段不存在：{source_path}")

        if target_path not in target_dict:
            raise ValueError(f"目标字段不存在：{target_path}")

        source_type = source_dict[source_path]["type"]
        target_type = target_dict[target_path]["type"]

        if source_type != target_type:
            raise ValueError(
                f"类型不兼容：{source_path} → {target_path}"
            )

        if target_path in used_targets:
            raise ValueError(
                f"目标字段重复映射：{target_path}"
            )

        used_targets.add(target_path)

    return True

validate_approved_mappings(
    approved,
    source_catalog,
    target_catalog
)

print("全部批准映射校验通过")

mapped_targets = set()

for mapping in approved:
    mapped_targets.add(mapping["target"])

for field in target_catalog:
    if field["required"] and field["path"] not in mapped_targets:
        raise ValueError(
            f"必填目标字段缺少映射：{field['path']}"
        )

print("必填目标字段覆盖检查通过")
