import json
import hashlib

try:
    from .json_transformer import get_value, set_value, validate_result
except ImportError:
    from json_transformer import get_value, set_value, validate_result

# 读取 JSON 文件
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 保存 JSON 文件
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


# 计算 Schema 的 SHA-256 指纹
def schema_fingerprint(schema):
    content = json.dumps(
        schema,
        sort_keys=True,
        ensure_ascii=False
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# 检查 MappingSpec 是否经过审核，以及规则格式是否正确
def validate_mapping_spec(mapping_spec):
    if mapping_spec.get("review_status") != "approved":
        raise ValueError("MappingSpec 尚未通过人工审核")

    mappings = mapping_spec.get("mappings")

    if not isinstance(mappings, list) or not mappings:
        raise ValueError("MappingSpec 没有有效映射规则")

    source_ids = mapping_spec.get("source_ids")

    if not isinstance(source_ids, list) or not source_ids:
        raise ValueError("MappingSpec 缺少 source_ids")

    if len(source_ids) != len(set(source_ids)):
        raise ValueError("source_ids 中存在重复 ID")

    # 检查每条映射规则
    for index, mapping in enumerate(mappings, start=1):
        if not isinstance(mapping, dict):
            raise ValueError(f"第 {index} 条映射规则格式错误")

        for field in ("source_id", "source_path", "target_path"):
            if not isinstance(mapping.get(field), str) or not mapping[field]:
                raise ValueError(
                    f"第 {index} 条映射规则缺少有效的 {field}"
                )

        if mapping["source_id"] not in source_ids:
            raise ValueError(
                f"未声明的数据源：{mapping['source_id']}"
            )

        if mapping.get("operation") != "copy":
            raise ValueError("M05 当前只支持 copy 操作")

        if not mapping["source_path"].startswith("$."):
            raise ValueError("源路径格式错误")

        if not mapping["target_path"].startswith("$."):
            raise ValueError("目标路径格式错误")


# 检查 Schema 指纹是否与 MappingSpec 中记录的一致
def validate_schema_fingerprints(mapping_spec, schemas):
    expected = mapping_spec.get("schema_fingerprints")

    if not isinstance(expected, dict):
        raise ValueError("MappingSpec 缺少 schema_fingerprints")

    required_ids = mapping_spec["source_ids"] + ["target"]

    for schema_id in required_ids:
        if schema_id not in schemas:
            raise ValueError(f"缺少 Schema：{schema_id}")

        expected_hash = expected.get(schema_id)

        if not isinstance(expected_hash, str) or not expected_hash:
            raise ValueError(
                f"MappingSpec 缺少 Schema 指纹：{schema_id}"
            )

        actual_hash = schema_fingerprint(schemas[schema_id])

        if actual_hash != expected_hash:
            raise ValueError(
                f"Schema 指纹不一致：{schema_id}"
            )


# 检查两个目标路径是否冲突
def paths_conflict(path1, path2):
    if path1 == path2:
        return True

    # 检查父子字段路径冲突
    if path1.startswith(path2 + "."):
        return True

    if path2.startswith(path1 + "."):
        return True

    return False


# 根据 MappingSpec 从多个数据源组装目标 JSON
def assemble_sources(sources, mapping_spec):
    target_data = {}
    written_targets = set()

    # 遍历每条映射规则
    for mapping in mapping_spec["mappings"]:
        source_id = mapping["source_id"]
        source_path = mapping["source_path"]
        target_path = mapping["target_path"]

        # 检查数据源是否存在
        if source_id not in sources:
            raise ValueError(f"数据源不存在：{source_id}")

        # 防止多个源字段写入冲突的目标路径
        for written_path in written_targets:
            if paths_conflict(target_path, written_path):
                raise ValueError(
                    f"目标字段冲突：{target_path} 与 {written_path}"
                )

        # 根据 source_id 选择对应的数据源
        source_data = sources[source_id]

        # 从源 JSON 中读取字段值
        try:
            value = get_value(source_data, source_path)
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"源字段不存在：{source_id} → {source_path}"
            ) from e

        # 将字段值写入目标 JSON
        try:
            set_value(target_data, target_path, value)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ValueError(
                f"目标字段写入失败：{target_path}，原因：{e}"
            ) from e

        # 记录已写入的目标路径
        written_targets.add(target_path)

    return target_data


def main():
    # 读取两个来源的 JSON 数据
    student_info = load_json("examples/student_info.json")
    student_score = load_json("examples/student_score.json")

    # 使用 source_id 管理不同数据源
    sources = {
        "student_info": student_info,
        "student_score": student_score
    }

    # 读取多源映射规则
    mapping_spec = load_json(
        "outputs/multi_source_mapping_spec.json"
    )

    # 读取来源 Schema 和目标 Schema
    info_schema = load_json(
        "schemas/student_info_schema.json"
    )

    score_schema = load_json(
        "schemas/student_score_schema.json"
    )

    target_schema = load_json(
        "schemas/target_schema.json"
    )

    schemas = {
        "student_info": info_schema,
        "student_score": score_schema,
        "target": target_schema
    }

    # 检查映射规则是否有效且已审核
    validate_mapping_spec(mapping_spec)
    print("MappingSpec 审核检查通过")

    # 验证 Schema 是否发生变化
    validate_schema_fingerprints(mapping_spec, schemas)
    print("Schema 指纹校验通过")

    # 按照映射规则执行多源组装
    result = assemble_sources(sources, mapping_spec)

    # 检查组装结果是否符合目标 Schema
    validation_result = validate_result(result, target_schema)

    if validation_result is False:
        raise ValueError("目标 Schema 校验失败")

    print("目标 Schema 校验通过")

    # 显示组装结果
    print("多源组装结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 将结果保存到 JSON 文件
    save_json("outputs/multi_source_result.json", result)

    print("M05 多源组装成功，结果已保存")


if __name__ == "__main__":
    main()
