from .json_transformer import transform_json
from .mapper_service import run_code_node

# 执行 JSON 字段映射和 Python 代码节点
def run_workflow(
    source_data,
    mapping_spec,
    source_schema,
    target_schema,
    code,
    return_logs=False
):
    # 执行原有 JSON 字段映射
    mapped_data = transform_json(
        source_data,
        mapping_spec,
        source_schema,
        target_schema
    )

    # 执行 Python 代码节点并获取日志
    result, logs = run_code_node(
        mapped_data,
        code,
        target_schema,
        return_logs=True
    )

    if return_logs:
        return result, logs

    return result