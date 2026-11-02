
import json
import hashlib


# 读取 JSON 文件
def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# 计算 Schema 指纹
def fingerprint(schema):
    content = json.dumps(
        schema,
        sort_keys=True,
        ensure_ascii=False
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# 读取来源和目标 Schema
info_schema = load_json("schemas/student_info_schema.json")
score_schema = load_json("schemas/student_score_schema.json")
target_schema = load_json("schemas/target_schema.json")

# 读取已有的多源 MappingSpec
spec_path = "outputs/multi_source_mapping_spec.json"
spec = load_json(spec_path)

# 生成并记录 Schema 指纹
spec["schema_fingerprints"] = {
    "student_info": fingerprint(info_schema),
    "student_score": fingerprint(score_schema),
    "target": fingerprint(target_schema)
}

# 记录规则生成方式
spec["generation_method"] = "manual_demo"

# 保存 MappingSpec
with open(spec_path, "w", encoding="utf-8") as file:
    json.dump(spec, file, ensure_ascii=False, indent=2)

print("Schema 指纹生成成功")
