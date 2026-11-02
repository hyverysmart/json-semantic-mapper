
from .json_transformer import (
    transform_json,
    validate_result
)

from .multi_source_assembler import (
    assemble_sources,
    validate_mapping_spec,
    validate_schema_fingerprints
)


# 检查 MappingSpec 是否经过人工审核
def check_review_status(mapping_spec):
    if not isinstance(mapping_spec, dict):
        raise ValueError("MappingSpec 必须是字典")

    if mapping_spec.get("review_status") != "approved":
        raise ValueError("MappingSpec 尚未通过人工审核")


# 检查 Schema 数据格式
def check_schemas(schemas):
    if not isinstance(schemas, dict):
        raise ValueError("schemas 必须是字典")

    for source_id, schema in schemas.items():
        if not isinstance(schema, dict):
            raise ValueError(
                f"Schema 格式错误：{source_id}"
            )


# 单源 JSON 转换接口
def transform_single(
    source_data,
    mapping_spec,
    source_schema,
    target_schema
):
    check_review_status(mapping_spec)

    if not isinstance(source_schema, dict):
        raise ValueError("source_schema 必须是字典")

    if not isinstance(target_schema, dict):
        raise ValueError("target_schema 必须是字典")

    # 校验源数据
    validate_result(source_data, source_schema)

    # 复用 M04 的转换功能
    result = transform_json(
        source_data,
        mapping_spec,
        source_schema,
        target_schema
    )

    # 验证目标数据
    validate_result(result, target_schema)

    return result


# 多源 JSON 组装接口
def transform_multi(
    sources,
    mapping_spec,
    schemas,
    target_schema
):
    check_review_status(mapping_spec)

    if not isinstance(sources, dict):
        raise ValueError("sources 必须是字典")

    if not isinstance(target_schema, dict):
        raise ValueError("target_schema 必须是字典")

    check_schemas(schemas)

    source_ids = mapping_spec.get("source_ids")

    if not isinstance(source_ids, list) or not source_ids:
        raise ValueError("MappingSpec 缺少 source_ids")

    # 检查实际数据源与 MappingSpec 是否一致
    for source_id in source_ids:
        if source_id not in sources:
            raise ValueError(
                f"缺少数据源：{source_id}"
            )

        if source_id not in schemas:
            raise ValueError(
                f"缺少来源 Schema：{source_id}"
            )

    # 校验每个来源的 JSON 数据
    for source_id in source_ids:
        validate_result(
            sources[source_id],
            schemas[source_id]
        )

    # 检查多源 MappingSpec 规则格式和审核状态
    validate_mapping_spec(mapping_spec)

    # 检查来源和目标 Schema 指纹
    all_schemas = {
        source_id: schemas[source_id]
        for source_id in source_ids
    }

    all_schemas["target"] = target_schema

    validate_schema_fingerprints(
        mapping_spec,
        all_schemas
    )

    # 使用 M05 已有函数组装数据
    result = assemble_sources(
        sources,
        mapping_spec
    )

    # 校验最终目标 JSON
    validate_result(
        result,
        target_schema
    )

    return result