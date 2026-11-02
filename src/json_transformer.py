import json
import hashlib
import re

# 读取与保存 JSON 文件

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

#Schema 指纹

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


def verify_fingerprints(spec, source_schema, target_schema):
    fingerprints = spec.get("schema_fingerprints", {})

    if fingerprints.get("student_source") != schema_fingerprint(source_schema):
        raise ValueError("源 Schema 指纹不一致，请重新审核 MappingSpec")

    if fingerprints.get("target") != schema_fingerprint(target_schema):
        raise ValueError("目标 Schema 指纹不一致，请重新审核 MappingSpec")

#解析 JSON 路径

def parse_path(path):
    if not isinstance(path, str) or not path.startswith("$."):
        raise ValueError(f"无效 JSON 路径：{path}")

    tokens = []

    for part in path[2:].split("."):
        match = re.fullmatch(r"([^\[\].]+)(?:\[(\*|\d+)\])?", part)

        if match is None:
            raise ValueError(f"不支持的路径格式：{path}")

        tokens.append(match.group(1))

        if match.group(2) is not None:
            index = match.group(2)

            if index == "*":
                tokens.append("*")
            else:
                tokens.append(int(index))

    return tokens

#根据路径读取数据

def get_value(data, path):
    tokens = parse_path(path)
    current = data

    for token in tokens:
        if token == "*":
            raise ValueError("get_value 不支持直接读取通配符路径")

        if isinstance(token, str):
            if not isinstance(current, dict) or token not in current:
                raise ValueError(f"源字段不存在：{path}")

            current = current[token]

        else:
            if not isinstance(current, list) or token >= len(current):
                raise ValueError(f"数组索引不存在：{path}")

            current = current[token]

    return current

#根据路径写入数据

def set_value(data, path, value):
    tokens = parse_path(path)

    if "*" in tokens:
        raise ValueError(f"写入路径不能包含未展开的通配符：{path}")

    current = data

    for i, token in enumerate(tokens[:-1]):
        next_token = tokens[i + 1]

        if isinstance(token, str):
            if not isinstance(current, dict):
                raise ValueError(f"目标路径结构冲突：{path}")

            if token not in current:
                current[token] = [] if isinstance(next_token, int) else {}

            current = current[token]

        else:
            if not isinstance(current, list):
                raise ValueError(f"目标路径不是数组：{path}")

            while len(current) <= token:
                current.append(None)

            if current[token] is None:
                current[token] = [] if isinstance(next_token, int) else {}

            current = current[token]

    last_token = tokens[-1]

    if isinstance(last_token, str):
        if not isinstance(current, dict):
            raise ValueError(f"目标字段所在位置不是对象：{path}")

        if last_token in current:
            raise ValueError(f"目标字段重复写入：{path}")

        current[last_token] = value

    else:
        if not isinstance(current, list):
            raise ValueError(f"目标字段所在位置不是数组：{path}")

        while len(current) <= last_token:
            current.append(None)

        if current[last_token] is not None:
            raise ValueError(f"目标数组元素重复写入：{path}")

        current[last_token] = value

#数组通配符展开

def expand_source(data, path):
    tokens = parse_path(path)
    results = []

    def walk(current, position, indices):
        if position == len(tokens):
            results.append((indices, current))
            return

        token = tokens[position]

        if token == "*":
            if not isinstance(current, list):
                raise ValueError(f"数组路径对应的数据不是数组：{path}")

            for index, item in enumerate(current):
                walk(item, position + 1, indices + [index])

        elif isinstance(token, str):
            if not isinstance(current, dict) or token not in current:
                raise ValueError(f"源字段不存在：{path}")

            walk(current[token], position + 1, indices)

        else:
            if not isinstance(current, list) or token >= len(current):
                raise ValueError(f"数组索引不存在：{path}")

            walk(current[token], position + 1, indices)

    walk(data, 0, [])

    return results


def replace_wildcards(path, indices):
    result = path

    if result.count("[*]") != len(indices):
        raise ValueError(f"源和目标数组作用域不一致：{path}")

    for index in indices:
        result = result.replace("[*]", f"[{index}]", 1)

    return result

#检查 Schema 路径和类型

def schema_type_at(schema, path):
    tokens = parse_path(path)
    current = schema

    for token in tokens:
        schema_type = current.get("type")

        if isinstance(token, str) and token != "*":
            if schema_type != "object":
                raise ValueError(f"Schema 路径结构错误：{path}")

            properties = current.get("properties", {})

            if token not in properties:
                raise ValueError(f"Schema 中不存在字段：{path}")

            current = properties[token]

        else:
            if schema_type != "array":
                raise ValueError(f"Schema 中不是数组：{path}")

            current = current.get("items", {})

    return current.get("type")


def types_compatible(source_type, target_type):
    if source_type == target_type:
        return True

    # 整数可以写入 number 类型字段
    return source_type == "integer" and target_type == "number"


def validate_rules(spec, source_schema, target_schema):
    if spec.get("review_status") != "approved":
        raise ValueError("MappingSpec 尚未通过人工审核")

    if spec.get("source_ids") != ["student_source"]:
        raise ValueError("当前 M04 仅支持 student_source 单数据源")

    rules = spec.get("mappings")

    if not isinstance(rules, list) or not rules:
        raise ValueError("MappingSpec 中没有有效规则")

    targets = []

    for rule in rules:
        if rule.get("source_id") != "student_source":
            raise ValueError("规则使用了未知数据源")

        if rule.get("operation") != "copy":
            raise ValueError("目前仅支持 copy 操作")

        source_path = rule["source_path"]
        target_path = rule["target_path"]

        source_type = schema_type_at(source_schema, source_path)
        target_type = schema_type_at(target_schema, target_path)

        if not types_compatible(source_type, target_type):
            raise ValueError(
                f"字段类型不兼容：{source_path} → {target_path}"
            )

        if source_path.count("[*]") != target_path.count("[*]"):
            raise ValueError("源和目标的数组通配符数量不一致")

        if target_path in targets:
            raise ValueError(f"目标规则重复：{target_path}")

        targets.append(target_path)

#目标 JSON 数据类型校验

def validate_result(data, schema, path="$"):
    schema_type = schema.get("type")

    if schema_type == "object":
        if not isinstance(data, dict):
            raise ValueError(f"{path} 应该是 object")

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for name in required:
            if name not in data:
                raise ValueError(f"缺少必填字段：{path}.{name}")

        for name, value in data.items():
            if name not in properties:
                raise ValueError(f"目标 Schema 未定义字段：{path}.{name}")

            validate_result(value, properties[name], f"{path}.{name}")

    elif schema_type == "array":
        if not isinstance(data, list):
            raise ValueError(f"{path} 应该是 array")

        items_schema = schema.get("items")

        if not isinstance(items_schema, dict):
            raise ValueError(f"{path} 缺少有效 items 定义")

        for index, item in enumerate(data):
            validate_result(item, items_schema, f"{path}[{index}]")

    elif schema_type == "string":
        if not isinstance(data, str):
            raise ValueError(f"{path} 应该是 string")

    elif schema_type == "integer":
        if type(data) is not int:
            raise ValueError(f"{path} 应该是 integer")

    elif schema_type == "number":
        if type(data) not in (int, float):
            raise ValueError(f"{path} 应该是 number")

    elif schema_type == "boolean":
        if type(data) is not bool:
            raise ValueError(f"{path} 应该是 boolean")

    else:
        raise ValueError(f"{path} 使用了不支持的类型：{schema_type}")

    return True

#核心：确定性转换

def transform_json(source_data, mapping_spec, source_schema, target_schema):
    verify_fingerprints(mapping_spec, source_schema, target_schema)

    validate_result(source_data, source_schema)

    validate_rules(mapping_spec, source_schema, target_schema)

    target_data = {}

    for mapping in mapping_spec["mappings"]:
        source_path = mapping["source_path"]
        target_path = mapping["target_path"]

        # 处理数组投影
        if "[*]" in source_path:
            expanded = expand_source(source_data, source_path)

            for indices, value in expanded:
                actual_target_path = replace_wildcards(
                    target_path, indices
                )
                set_value(target_data, actual_target_path, value)

        # 处理普通字段及嵌套对象
        else:
            value = get_value(source_data, source_path)
            set_value(target_data, target_path, value)

    # 检查转换后的 JSON 是否符合目标 Schema
    validate_result(target_data, target_schema)

    return target_data

#主程序

def main():
    source_data = load_json("examples/student_input.json")

    mapping_spec = load_json("outputs/mapping_spec.json")

    source_schema = load_json("schemas/source_schema.json")
    target_schema = load_json("schemas/target_schema.json")

    print("当前 MappingSpec 规则：")

    for mapping in mapping_spec["mappings"]:
        print(
            mapping["source_path"],
            "→",
            mapping["target_path"]
        )

    result = transform_json(
        source_data,
        mapping_spec,
        source_schema,
        target_schema
    )

    print("\n转换结果：")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    save_json(result, "outputs/transformed_student.json")

    print("\n目标 Schema 校验通过")
    print("转换结果已保存到 outputs/transformed_student.json")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as e:
        print(f"转换失败：{e}")
        raise SystemExit(1)
