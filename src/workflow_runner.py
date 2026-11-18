from .json_transformer import transform_json
from .mapper_service import run_code_node


# 根据工作流配置执行节点
def run_workflow(
    source_data,
    mapping_spec,
    source_schema,
    target_schema,
    code,
    return_logs=False,
    workflow_spec=None
):
    # 没有提供配置时，使用原来的执行顺序
    if workflow_spec is None:
        workflow_spec = {
            "steps": [
                {"id": "mapping_1", "type": "mapping"},
                {"id": "python_1", "type": "code"}
            ]
        }

    # 检查工作流配置
    if not isinstance(workflow_spec, dict):
        raise ValueError("工作流配置必须是 JSON 对象")

    steps = workflow_spec.get("steps")

    if not isinstance(steps, list) or len(steps) != 2:
        raise ValueError("当前工作流必须包含两个节点")

    types = [
        step.get("type") if isinstance(step, dict) else None
        for step in steps
    ]

    if set(types) != {"mapping", "code"}:
        raise ValueError("工作流必须包含一个 mapping 节点和一个 code 节点")

    # 保存当前数据和运行日志
    current_data = source_data
    logs = ""
    mapping_done = False

    # 按照配置顺序执行节点
    for step in steps:

        # JSON 字段映射节点
        if step["type"] == "mapping":
            current_data = transform_json(
                current_data,
                mapping_spec,
                source_schema,
                target_schema
            )
            mapping_done = True

        # Python 代码处理节点
        elif step["type"] == "code":
            schema = target_schema if mapping_done else source_schema

            current_data, node_logs = run_code_node(
                current_data,
                code,
                schema,
                return_logs=True
            )

            logs += node_logs

    # 根据需要返回执行结果和日志
    if return_logs:
        return current_data, logs

    return current_data