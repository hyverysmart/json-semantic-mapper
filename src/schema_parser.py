
import json
import os

# 当前项目支持的 JSON Schema 类型和关键字
ALLOWED_TYPES = {
    "object",
    "array",
    "string",
    "integer",
    "number",
    "boolean"
}

ALLOWED_KEYWORDS = {
    "type",
    "properties",
    "required",
    "items",
    "description",
    "title"
}


# 1. 读取 JSON Schema 文件
def load_schema(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            schema = json.load(file)
        return schema

    except FileNotFoundError:
        raise ValueError(
            f"Schema 文件不存在：{file_path}"
        )

    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON 格式错误：{file_path}，{e}"
        )


# 2. 校验 JSON Schema
def validate_schema(schema, path="$"):

    # 检查 Schema 本身是否为字典
    if not isinstance(schema, dict):
        raise ValueError(
            f"位置 {path}：Schema 必须是对象"
        )

    # 检查是否包含不支持的关键字
    for keyword in schema:
        if keyword not in ALLOWED_KEYWORDS:
            raise ValueError(
                f"位置 {path}：不支持的关键字 {keyword}"
            )

    # 获取并检查 type
    schema_type = schema.get("type")

    if schema_type not in ALLOWED_TYPES:
        raise ValueError(
            f"位置 {path}：不支持或无效的类型 {schema_type}"
        )

    # 检查 description 和 title
    for keyword in ("description", "title"):
        if keyword in schema:
            if not isinstance(schema[keyword], str):
                raise ValueError(
                    f"位置 {path}：{keyword} 必须是字符串"
                )

    # object 类型检查
    if schema_type == "object":

        if "items" in schema:
            raise ValueError(
                f"位置 {path}：object 不能使用 items"
            )

        properties = schema.get("properties", {})

        if not isinstance(properties, dict):
            raise ValueError(
                f"位置 {path}：properties 必须是对象"
            )

        required = schema.get("required",[])

        if not isinstance(required, list):
            raise ValueError(
                f"位置 {path}：required 必须是数组"
            )

        # required 中的元素必须是字符串
        for field_name in required:
            if not isinstance(field_name, str):
                raise ValueError(
                    f"位置 {path}：required 中的字段名必须是字符串"
                )

        # required 中不能有重复字段
        if len(required) != len(set(required)):
            raise ValueError(
                f"位置 {path}：required 中存在重复字段"
            )

        # required 中的字段必须在 properties 中定义
        for field_name in required:
            if field_name not in properties:
                raise ValueError(
                    f"位置 {path}：必填字段 {field_name} 未在 properties 中定义"
                )

        # 递归校验子字段
        for field_name, field_info in properties.items():

            if not isinstance(field_name, str):
                raise ValueError(
                    f"位置 {path}：字段名称必须是字符串"
                )

            field_path = f"{path}.{field_name}"

            validate_schema(field_info, field_path)

    # array 类型检查
    elif schema_type == "array":

        if "properties" in schema or "required" in schema:
            raise ValueError(
                f"位置 {path}：array 不能直接使用 properties 或 required"
            )

        items_schema = schema.get("items")

        if items_schema is None:
            raise ValueError(
                f"位置 {path}：数组缺少 items"
            )

        if not isinstance(items_schema, dict):
            raise ValueError(
                f"位置 {path}：items 必须是对象"
            )

        items_path = f"{path}[*]"

        validate_schema(items_schema, items_path)

    # 基本数据类型不允许使用结构关键字
    else:
        for keyword in ("properties", "required", "items"):
            if keyword in schema:
                raise ValueError(
                    f"位置 {path}：类型 {schema_type} 不能使用 {keyword}"
                )

    return True


# 3. 解析 Schema，生成字段目录
def parse_schema(schema, path="$", field_catalog=None):

    if field_catalog is None:
        field_catalog = []

    schema_type = schema.get("type")

    # 解析对象
    if schema_type == "object":

        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        for field_name, field_info in properties.items():

            field_path = f"{path}.{field_name}"
            field_type = field_info["type"]

            field_description = field_info.get(
                "description", "无描述"
            )

            is_required = field_name in required_fields

            field_record = {
                "name": field_name,
                "path": field_path,
                "type": field_type,
                "description": field_description,
                "required": is_required
            }

            field_catalog.append(field_record)

            print(f"字段名称：{field_name}")
            print(f"字段路径：{field_path}")
            print(f"字段类型：{field_type}")
            print(f"字段描述：{field_description}")
            print(f"是否必填：{is_required}\n")

            # 递归解析嵌套对象
            if field_type == "object":
                parse_schema(
                    field_info,
                    field_path,
                    field_catalog
                )

            # 递归解析数组元素
            elif field_type == "array":
                items_schema = field_info["items"]
                items_path = f"{field_path}[*]"

                parse_schema(
                    items_schema,
                    items_path,
                    field_catalog
                )

    # 支持直接解析根数组或嵌套数组
    elif schema_type == "array":

        items_schema = schema["items"]
        items_path = f"{path}[*]"

        parse_schema(
            items_schema,
            items_path,
            field_catalog
        )

    return field_catalog


# 4. 保存字段目录
def save_catalog(catalog, file_path):

    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True
    )

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            catalog,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"字段目录已保存：{file_path}")


# 5. 主程序
def main():

    print("当前工作目录：", os.getcwd())

    # 读取 Schema
    source_schema = load_schema(
        "schemas/source_schema.json"
    )

    target_schema = load_schema(
        "schemas/target_schema.json"
    )

    array_schema = load_schema(
        "schemas/array_schema.json"
    )

    # 先校验 Schema
    validate_schema(source_schema)
    validate_schema(target_schema)
    validate_schema(array_schema)

    print("全部 Schema 校验通过\n")

    # 解析源 Schema
    print("========== 源 Schema ==========")
    source_catalog = parse_schema(source_schema)

    # 解析目标 Schema
    print("========== 目标 Schema ==========")
    target_catalog = parse_schema(target_schema)

    # 解析数组 Schema
    print("========== 数组 Schema ==========")
    array_catalog = parse_schema(array_schema)

    # 保存结果
    save_catalog(
        source_catalog,
        "outputs/source_catalog.json"
    )

    save_catalog(
        target_catalog,
        "outputs/target_catalog.json"
    )

    save_catalog(
        array_catalog,
        "outputs/array_catalog.json"
    )

    print("\nM01 Schema 解析与基础校验执行完成")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as e:
        print(f"错误：{e}")
        raise SystemExit(1)
