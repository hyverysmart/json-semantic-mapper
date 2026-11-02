
import argparse
import hashlib
import json


# 读取 JSON 文件
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 保存 JSON 文件
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


# 计算 Schema 指纹
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


# 检查 MappingSpec 中保存的 Schema 指纹
def verify_schema_fingerprints(mapping_spec, source_schema, target_schema):
    saved_hashes = mapping_spec["schema_fingerprints"]

    current_source_hash = schema_fingerprint(source_schema)
    current_target_hash = schema_fingerprint(target_schema)

    if saved_hashes["student_source"] != current_source_hash:
        raise ValueError("源 Schema 已发生变化，MappingSpec 需要重新审核")

    if saved_hashes["target"] != current_target_hash:
        raise ValueError("目标 Schema 已发生变化，MappingSpec 需要重新审核")

    return True


# 校验批准的映射规则
def validate_approved_mappings(approved, source_catalog, target_catalog):
    source_dict = {
        field["path"]: field for field in source_catalog
    }

    target_dict = {
        field["path"]: field for field in target_catalog
    }

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

        compatible = (
            source_type == target_type
            or (source_type == "integer" and target_type == "number")
        )

        if not compatible:
            raise ValueError(
                f"类型不兼容：{source_path} → {target_path}"
            )

        if target_path in used_targets:
            raise ValueError(
                f"目标字段重复映射：{target_path}"
            )

        used_targets.add(target_path)

    return True


# 检查必填目标字段是否都有映射
def validate_required_targets(approved, target_catalog):
    mapped_targets = {
        mapping["target"] for mapping in approved
    }

    for field in target_catalog:
        if field["required"] and field["path"] not in mapped_targets:
            raise ValueError(
                f"必填目标字段缺少映射：{field['path']}"
            )

    return True


# 根据选择的模型来源读取候选映射
def load_candidates(provider):
    rule_candidates = load_json(
        "outputs/candidate_mappings.json"
    )

    candidate_files = {
        "mock": "outputs/mock_llm_candidates.json",
        "deepseek": "outputs/deepseek_llm_candidates.json"
    }

    llm_result = load_json(candidate_files[provider])

    if llm_result.get("generation_method") != provider:
        raise ValueError(
            f"候选文件的生成方式与所选 provider 不一致：{provider}"
        )

    llm_candidates = llm_result["mappings"]

    if not isinstance(rule_candidates, list):
        raise ValueError("规则候选映射必须是数组")

    if not isinstance(llm_candidates, list):
        raise ValueError("LLM 候选映射必须是数组")

    return rule_candidates + llm_candidates


# 人工审核每条候选映射
def review_candidates(all_candidates):
    approved_mappings = []
    rejected_mappings = []
    approved_targets = set()

    print("\n待审核的候选映射：")

    for index, mapping in enumerate(all_candidates, start=1):
        print(
            index,
            mapping["source"],
            "→",
            mapping["target"],
            "原因：",
            mapping["reason"]
        )

    for mapping in all_candidates:
        print("\n待审核映射：")
        print(mapping["source"], "→", mapping["target"])
        print("匹配原因：", mapping["reason"])

        while True:
            decision = input("是否批准？(y/n)：").strip().lower()

            if decision in ("y", "n"):
                break

            print("请输入 y 或 n")

        if decision == "y":
            target_path = mapping["target"]

            if target_path in approved_targets:
                print(f"冲突：目标字段 {target_path} 已存在批准的映射")
                rejected_mappings.append(mapping)
                print("本条因冲突被拒绝")
            else:
                approved_mappings.append(mapping)
                approved_targets.add(target_path)
                print("已批准")
        else:
            rejected_mappings.append(mapping)
            print("已拒绝")

    return approved_mappings, rejected_mappings


# 将人工批准的候选映射转换成声明式规则
def build_mapping_rules(approved):
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

    return mapping_rules


# 生成正式 MappingSpec
def build_mapping_spec(mapping_rules, source_schema, target_schema, provider):
    return {
        "version": "1.0",
        "source_ids": ["student_source"],
        "schema_fingerprints": {
            "student_source": schema_fingerprint(source_schema),
            "target": schema_fingerprint(target_schema)
        },
        "review_status": "approved",
        "generation_method": f"rule_and_{provider}",
        "mappings": mapping_rules
    }


# 执行映射审核和规则生成
def run_review(provider):
    source_catalog = load_json(
        "outputs/source_catalog.json"
    )

    target_catalog = load_json(
        "outputs/target_catalog.json"
    )

    source_schema = load_json(
        "schemas/source_schema.json"
    )

    target_schema = load_json(
        "schemas/target_schema.json"
    )

    all_candidates = load_candidates(provider)

    # 在人工审核之前检查所有候选规则
    for mapping in all_candidates:
        if not isinstance(mapping, dict):
            raise ValueError("候选映射格式错误")

        for key in ("source", "target", "reason"):
            if not isinstance(mapping.get(key), str) or not mapping[key].strip():
                raise ValueError(f"候选映射缺少有效字段：{key}")

    approved, rejected = review_candidates(all_candidates)

    # 保存人工审核记录
    review_result = {
        "generation_method": f"rule_and_{provider}",
        "approved": approved,
        "rejected": rejected
    }

    save_json(
        "outputs/mapping_review.json",
        review_result
    )

    print("\n审核结果：")
    print("批准数量：", len(approved))
    print("拒绝数量：", len(rejected))
    print("人工审核结果已保存")

    # 先校验规则，再生成正式 MappingSpec
    validate_approved_mappings(
        approved,
        source_catalog,
        target_catalog
    )

    print("全部批准映射校验通过")

    validate_required_targets(
        approved,
        target_catalog
    )

    print("必填目标字段覆盖检查通过")

    mapping_rules = build_mapping_rules(approved)

    mapping_spec = build_mapping_spec(
        mapping_rules,
        source_schema,
        target_schema,
        provider
    )

    verify_schema_fingerprints(
        mapping_spec,
        source_schema,
        target_schema
    )

    print("MappingSpec 的 Schema 指纹验证通过")

    # 全部检查通过后，才保存正式规则
    save_json(
        "outputs/mapping_spec.json",
        mapping_spec
    )

    print("\nMappingSpec 已生成：outputs/mapping_spec.json")
    print("规则数量：", len(mapping_rules))
    print("生成方式：", mapping_spec["generation_method"])


# 命令行参数
def main():
    parser = argparse.ArgumentParser(
        description="JSON Semantic Mapper - MappingSpec 人工审核"
    )

    parser.add_argument(
        "--provider",
        choices=["mock", "deepseek"],
        default="mock",
        help="选择 Mock 或 DeepSeek 候选映射来源"
    )

    args = parser.parse_args()

    run_review(args.provider)

# 生成字段映射候选，不执行人工审核
def propose_mappings(source_fields, target_fields, provider="deepseek"):
    if provider not in ("deepseek", "rules"):
        raise ValueError(f"不支持的候选生成方式：{provider}")

    from .llm_mapper import (
        build_prompt,
        call_deepseek,
        validate_llm_result
    )

    candidates = []
    unresolved_targets = []

    # 根据名称与描述生成规则候选
    for target in target_fields:
        possible_matches = []

        for source in source_fields:
            compatible = (
                source["type"] == target["type"]
                or (
                    source["type"] == "integer"
                    and target["type"] == "number"
                )
            )

            if not compatible:
                continue

            source_name = source["path"].split(".")[-1]
            target_name = target["path"].split(".")[-1]

            if source_name == target_name:
                possible_matches.append({
                    "source": source["path"],
                    "target": target["path"],
                    "reason": "字段名称相同且类型兼容"
                })

            elif (
                source.get("description")
                and source.get("description") != "无描述"
                and source.get("description") == target.get("description")
            ):
                possible_matches.append({
                    "source": source["path"],
                    "target": target["path"],
                    "reason": "字段描述相同且类型兼容"
                })

        # 候选唯一时直接列为待审核规则
        if len(possible_matches) == 1:
            candidates.extend(possible_matches)
        else:
            unresolved_targets.append(target)

    # 规则模式不调用 LLM
    if provider == "rules":
        return {
            "generation_method": provider,
            "review_status": "pending",
            "mappings": candidates,
            "unresolved": [
                field["path"] for field in unresolved_targets
            ]
        }

    # 对规则无法唯一确定的字段调用 DeepSeek
    if unresolved_targets:
        prompt = build_prompt(source_fields, unresolved_targets)
        llm_result = call_deepseek(prompt)

        validate_llm_result(
            llm_result,
            source_fields,
            unresolved_targets
        )

        candidates.extend(llm_result["mappings"])
        unresolved = llm_result["unresolved"]
    else:
        unresolved = []

    return {
        "generation_method": provider,
        "review_status": "pending",
        "mappings": candidates,
        "unresolved": unresolved
    }


# 根据外部提交的人工审核结果生成 MappingSpec
def approve_mappings(
    candidates,
    approved_pairs,
    source_fields,
    target_fields,
    source_schema,
    target_schema,
    source_id="student_source"
):
    if not isinstance(candidates, dict):
        raise ValueError("候选结果必须是字典")

    if candidates.get("review_status") != "pending":
        raise ValueError("候选结果状态必须是 pending")

    if not isinstance(approved_pairs, list):
        raise ValueError("approved_pairs 必须是列表")

    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source_id 不能为空")

    if source_id == "target":
        raise ValueError("source_id 不能使用保留名称 target")

    if not isinstance(source_schema, dict):
        raise ValueError("source_schema 必须是字典")

    if not isinstance(target_schema, dict):
        raise ValueError("target_schema 必须是字典")

    candidate_list = candidates.get("mappings")

    if not isinstance(candidate_list, list):
        raise ValueError("候选映射必须是列表")

    # 建立允许批准的候选映射集合
    allowed_pairs = set()

    for mapping in candidate_list:
        if not isinstance(mapping, dict):
            raise ValueError("候选映射格式错误")

        source = mapping.get("source")
        target = mapping.get("target")

        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError("候选映射路径格式错误")

        allowed_pairs.add((source, target))

    approved = []
    seen_pairs = set()

    # 只接受候选列表中存在的人工批准映射
    for pair in approved_pairs:
        if not isinstance(pair, dict):
            raise ValueError("批准项必须是字典")

        source = pair.get("source")
        target = pair.get("target")

        if (source, target) not in allowed_pairs:
            raise ValueError(
                f"批准的映射不在候选列表中：{source} → {target}"
            )

        if (source, target) in seen_pairs:
            raise ValueError(
                f"重复批准映射：{source} → {target}"
            )

        seen_pairs.add((source, target))

        approved.append({
            "source": source,
            "target": target
        })

    # 检查源字段、目标字段及类型
    validate_approved_mappings(
        approved,
        source_fields,
        target_fields
    )

    # 检查所有必填目标字段是否已覆盖
    validate_required_targets(
        approved,
        target_fields
    )

    # 转换为声明式 MappingSpec 规则
    mapping_rules = []

    for mapping in approved:
        mapping_rules.append({
            "source_id": source_id,
            "source_path": mapping["source"],
            "target_path": mapping["target"],
            "operation": "copy",
            "array_scope": None
        })

    mapping_spec = {
        "version": "1.0",
        "source_ids": [source_id],
        "schema_fingerprints": {
            source_id: schema_fingerprint(source_schema),
            "target": schema_fingerprint(target_schema)
        },
        "review_status": "approved",
        "generation_method": (
            "rule_and_" + candidates.get("generation_method", "unknown")
        ),
        "mappings": mapping_rules
    }

    return mapping_spec

if __name__ == "__main__":
    main()