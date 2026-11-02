
import argparse
import json
import os

from openai import OpenAI


# 读取 JSON 文件
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 保存 JSON 文件
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


# 根据字段目录生成语义映射 Prompt
def build_prompt(source_fields, target_fields):
    prompt = f"""
你是一个 JSON Schema 字段语义映射助手。

请根据提供的源字段与目标字段，生成候选字段映射。

匹配规则：
1. 根据字段名称、数据类型和描述判断语义是否相同。
2. 只能使用提供的源字段和目标字段，不能编造字段路径。
3. 源字段和目标字段的数据类型必须兼容。
4. 每个候选映射必须提供判断理由。
5. 同一个目标字段最多只能匹配一次。
6. 如果无法确定对应关系，将目标字段放入 unresolved。
7. 每个目标字段必须出现在 mappings 或 unresolved 中。
8. 不要因为字段名称相似就直接认定语义相同。
9. 只返回合法 JSON，不要输出 Markdown 或其他解释。

输出 JSON 格式示例：
{{
  "mappings": [
    {{
      "source": "$.studentId",
      "target": "$.id",
      "reason": "两个字段的描述都表示学生唯一标识"
    }}
  ],
  "unresolved": []
}}

注意：上面只是格式示例，不代表实际映射答案。
必须根据下面的字段信息独立判断。

源字段：
{json.dumps(source_fields, ensure_ascii=False, indent=2)}

待匹配目标字段：
{json.dumps(target_fields, ensure_ascii=False, indent=2)}
"""
    return prompt


# 返回用于测试的模拟 LLM 结果
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


# 调用真实 DeepSeek API
def call_deepseek(prompt):
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError("未设置 DEEPSEEK_API_KEY 环境变量")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=60.0,
        max_retries=1
    )

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是 JSON Schema 字段语义映射助手。"
                    "必须输出合法 JSON 对象。"
                    "不要编造字段路径，不要输出 Markdown。"
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
        stream=False
    )

    if not response.choices:
        raise ValueError("DeepSeek 没有返回候选结果")

    choice = response.choices[0]

    if choice.finish_reason == "length":
        raise ValueError("DeepSeek 输出被截断，请增加 max_tokens")

    if choice.finish_reason != "stop":
        raise ValueError(
            f"DeepSeek 未正常完成生成：{choice.finish_reason}"
        )

    content = choice.message.content

    if not content or not content.strip():
        raise ValueError("DeepSeek 返回了空内容")

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"DeepSeek 返回的内容不是合法 JSON：{e}") from e

    return result


# 验证单条映射的路径和类型
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

    compatible = (
        source_type == target_type
        or (source_type == "integer" and target_type == "number")
    )

    if not compatible:
        raise ValueError(
            f"类型不兼容：{source_path}({source_type}) "
            f"不能映射到 {target_path}({target_type})"
        )

    return True


# 验证 LLM 返回结果的完整性
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

        validate_mapping(
            mapping,
            source_fields,
            target_fields
        )

        target_path = mapping["target"]

        if target_path in matched_targets:
            raise ValueError(f"目标字段重复映射：{target_path}")

        matched_targets.add(target_path)

    target_paths = {
        field["path"] for field in target_fields
    }

    unresolved_set = set()

    for target_path in result["unresolved"]:
        if not isinstance(target_path, str):
            raise ValueError("unresolved 中的路径必须是字符串")

        if target_path not in target_paths:
            raise ValueError(
                f"未解决目标字段不存在：{target_path}"
            )

        if target_path in unresolved_set:
            raise ValueError(
                f"未解决目标字段重复：{target_path}"
            )

        if target_path in matched_targets:
            raise ValueError(
                f"字段不能同时已匹配和未解决：{target_path}"
            )

        unresolved_set.add(target_path)

    if matched_targets | unresolved_set != target_paths:
        raise ValueError("存在未报告的目标字段")

    return True


# 执行字段映射生成和校验
def run_mapper(mode):
    source_catalog = load_json(
        "outputs/source_catalog.json"
    )

    unmatched_targets = load_json(
        "outputs/unmatched_targets.json"
    )

    print("可用源字段：")
    for field in source_catalog:
        print(
            field["path"],
            field["type"],
            field.get("description", "")
        )

    print("\n待匹配目标字段：")
    for field in unmatched_targets:
        print(
            field["path"],
            field["type"],
            field.get("description", "")
        )

    prompt = build_prompt(
        source_catalog,
        unmatched_targets
    )

    if mode == "mock":
        print("\n使用 Mock 模式")
        llm_result = mock_llm_response()

    elif mode == "deepseek":
        print("\n正在调用 DeepSeek API")
        llm_result = call_deepseek(prompt)

    else:
        raise ValueError(f"不支持的映射模式：{mode}")

    print("\nLLM 候选映射：")
    print(json.dumps(
        llm_result,
        ensure_ascii=False,
        indent=2
    ))

    # 只有通过程序校验的候选结果才允许保存
    validate_llm_result(
        llm_result,
        source_catalog,
        unmatched_targets
    )

    print("\nLLM 候选映射校验通过")

    candidates = {
        "generation_method": mode,
        "review_status": "pending",
        "mappings": llm_result["mappings"],
        "unresolved": llm_result["unresolved"]
    }

    if mode == "mock":
        output_path = "outputs/mock_llm_candidates.json"
    else:
        output_path = "outputs/deepseek_llm_candidates.json"

    save_json(output_path, candidates)

    print(f"候选映射已保存到 {output_path}")
    print("候选映射仍需人工审核，尚未写入正式 MappingSpec")

    return candidates


# 命令行入口
def main():
    parser = argparse.ArgumentParser(
        description="JSON Semantic Mapper - LLM 字段映射"
    )

    parser.add_argument(
        "--mode",
        choices=["mock", "deepseek"],
        default="mock",
        help="选择 Mock 或真实 DeepSeek API 模式"
    )

    args = parser.parse_args()

    run_mapper(args.mode)


if __name__ == "__main__":
    main()
