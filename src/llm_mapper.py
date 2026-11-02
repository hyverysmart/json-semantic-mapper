import json

def load_json(file_path):
    with open(file_path,"r",encoding="utf-8")as file:
        return json.load(file)

source_catalog=load_json("outputs/source_catalog.json")
unmatched_targets=load_json("outputs/unmatched_targets.json")

print("可用源字段：")
for field in source_catalog:
    print(field["path"],field["type"],field["description"])

print("\n待匹配目标字段：")
for field in unmatched_targets:
    print(field["path"],field["type"],field["description"])

def build_prompt(source_fields,target_fields):
    prompt=f"""
你是一个JSON Schema字段语义映射助手。

匹配规则：
1. 根据字段名称、数据类型和描述判断语义是否相同。
2. 只能使用提供的源字段和目标字段，不能编造字段路径。
3. 源字段和目标字段的数据类型必须兼容。
4. 每个候选映射必须提供判断理由。
5. 如果无法确定对应关系，将目标字段放入 unresolved。
6. 只返回 JSON，不要输出其他解释或 Markdown。


输出格式：
{{
  "mappings": [
    {{
      "source": "$.studentId",
      "target": "$.id",
      "reason": "两者都表示学生的唯一标识"
    }}
  ],
  "unresolved": []
}}

注意：上面只是输出格式示例，
必须根据实际输入字段判断，不能直接照抄示例。


源字段：
{json.dumps(source_fields,ensure_ascii=False,indent=2)}

待匹配目标字段：
{json.dumps(target_fields,ensure_ascii=False,indent=2)}
"""
    return prompt

prompt=build_prompt(source_catalog,unmatched_targets)
print("\n生成的Prompt：")
print(prompt)


def mock_llm_response():
    return {
        "mappings": [
            {
                "source": "$.studentId",
                "target": "$.id",
                "reason": "两个字段都表示学生的唯一标识"
            }
        ],
        "unresolved": []
    }


llm_result = mock_llm_response()

print("\n模拟 LLM 返回结果：")
print(json.dumps(llm_result, ensure_ascii=False, indent=2))


def validate_mapping(mapping, source_fields, target_fields):

    source_path = mapping["source"]
    target_path = mapping["target"]

    source_dict = {}
    target_dict = {}

    for field in source_fields:
        source_dict[field["path"]] = field

    for field in target_fields:
        target_dict[field["path"]] = field

    if source_path not in source_dict:
        raise ValueError(f"源字段不存在：{source_path}")

    if target_path not in target_dict:
        raise ValueError(f"目标字段不存在：{target_path}")

    source_type = source_dict[source_path]["type"]
    target_type = target_dict[target_path]["type"]

    if source_type != target_type:
        raise ValueError(
            f"类型不兼容：{source_path}({source_type})"
            f"不能映射到{target_path}({target_type})"
        )
    return True

for mapping in llm_result["mappings"]:
    validate_mapping(
        mapping,
        source_catalog,
        unmatched_targets
    )

print("模拟 LLM 候选映射路径校验通过")


def validate_llm_result(result, source_fields, target_fields):

    if not isinstance(result, dict):
        raise ValueError("LLM 结果必须是对象")

    if not isinstance(result.get("mappings"), list):
        raise ValueError("mappings 必须是数组")

    if not isinstance(result.get("unresolved"), list):
        raise ValueError("unresolved 必须是数组")

    matched_targets = set()

    for mapping in result["mappings"]:

        if not isinstance(mapping, dict):
            raise ValueError("每条映射必须是对象")

        for key in ("source", "target", "reason"):
            if not isinstance(mapping.get(key), str):
                raise ValueError(f"映射字段 {key} 必须是字符串")

            if not mapping[key].strip():
                raise ValueError(f"映射字段 {key} 不能为空")

        validate_mapping(mapping, source_fields, target_fields)

        target_path = mapping["target"]

        if target_path in matched_targets:
            raise ValueError(f"目标字段重复映射：{target_path}")

        matched_targets.add(target_path)

    target_paths = {field["path"] for field in target_fields}
    unresolved_set = set()

    for target_path in result["unresolved"]:

        if not isinstance(target_path, str):
            raise ValueError("unresolved 中的路径必须是字符串")

        if target_path not in target_paths:
            raise ValueError(f"未解决目标字段不存在：{target_path}")

        if target_path in unresolved_set:
            raise ValueError(f"未解决目标字段重复：{target_path}")

        if target_path in matched_targets:
            raise ValueError(f"字段不能同时已匹配和未解决：{target_path}")

        unresolved_set.add(target_path)

    if matched_targets | unresolved_set != target_paths:
        raise ValueError("存在未报告的目标字段")
    return True

validate_llm_result(
    llm_result,
    source_catalog,
    unmatched_targets
)

print("模拟 LLM 结果完整校验通过")

mock_candidates = {
    "generation_method": "mock",
    "mappings": llm_result["mappings"],
    "unresolved": llm_result["unresolved"]
}

with open("outputs/mock_llm_candidates.json", "w", encoding="utf-8") as file:
    json.dump(mock_candidates, file, ensure_ascii=False, indent=2)

print("模拟候选映射已保存")

