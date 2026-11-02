
# JSON Semantic Mapper

一个基于 JSON Schema、LLM 辅助语义映射和声明式规则的 JSON 数据转换工具。

本项目旨在解决不同 JSON 接口之间的字段名称、数据类型和数据结构不一致的问题，并提供可供其他 Python 项目调用的转换接口。

## 项目功能

- 解析 JSON Schema，提取字段名称、路径、类型和描述
- 根据字段名称、描述和类型生成候选映射
- 使用 DeepSeek API 辅助识别语义相同的字段
- 对 LLM 生成的候选映射进行程序校验
- 通过人工审核确认映射规则
- 生成声明式 MappingSpec
- 根据 MappingSpec 执行确定性 JSON 转换
- 支持单源 JSON 转换及多源 JSON 组装
- 校验 Schema 指纹、字段类型和必填字段
- 提供 Python API，便于其他项目集成
- 使用 pytest 进行自动化测试

## 核心设计

本项目将字段映射规则的生成和实际数据转换分开处理。

整体流程：

1. 解析源 JSON Schema 和目标 JSON Schema
2. 使用规则生成候选字段映射
3. 使用 LLM 补充语义映射候选
4. 对候选映射进行程序校验
5. 人工确认映射规则
6. 生成 MappingSpec
7. 根据 MappingSpec 执行 JSON 数据转换
8. 校验转换结果

LLM 只参与映射规则生成阶段。

实际业务数据转换时，不需要为每条数据重复调用 LLM，而是执行已经审核确认的 MappingSpec。

## 环境要求

- Python 3.12
- Windows 11（当前开发环境）
- pip
- pytest
- openai（调用 DeepSeek API）

## 安装方法

克隆项目：

```bash
git clone https://github.com/hyverysmart/json-semantic-mapper.git
cd json-semantic-mapper
```

创建虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
python -m pip install -r requirements.txt
```

## DeepSeek API 配置

项目支持使用 DeepSeek 生成候选语义映射。

在 PowerShell 中设置环境变量：

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
```

真实 DeepSeek 模式：

```bash
python src/llm_mapper.py --mode deepseek
```

模拟模式：

```bash
python src/llm_mapper.py --mode mock
```

注意：

- API Key 不应写入源代码或提交到 GitHub
- 使用真实 DeepSeek API 可能产生费用
- LLM 生成的是候选映射，不能直接视为审核通过的规则

## MappingSpec 人工审核

使用 DeepSeek 候选映射：

```bash
python src/mapping_spec.py --provider deepseek
```

使用 Mock 候选映射：

```bash
python src/mapping_spec.py --provider mock
```

程序会展示候选映射，使用者确认后生成 MappingSpec。

MappingSpec 记录字段来源、目标路径、规则和 Schema 指纹等信息。

## 命令行使用方法

### 单源 JSON 转换

```bash
python main.py --mode single
```

程序读取示例输入及已审核的 MappingSpec，并执行确定性转换。

输出：

`outputs/transformed_student.json`

### 多源 JSON 组装

```bash
python main.py --mode multi
```

程序使用学生基本信息和成绩两个来源，组装成目标 JSON。

输出：

`outputs/multi_source_result.json`

## Python API

项目通过 `src/mapper_service.py` 提供 Python 调用接口。

### 单源转换

```python
import json

from src.mapper_service import transform_single


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


source_data = {
    "studentId": 2002,
    "studentName": "Amy",
    "score": 88.5
}

mapping_spec = load_json("outputs/mapping_spec.json")
source_schema = load_json("schemas/source_schema.json")
target_schema = load_json("schemas/target_schema.json")

result = transform_single(
    source_data=source_data,
    mapping_spec=mapping_spec,
    source_schema=source_schema,
    target_schema=target_schema
)

print(result)
```

转换结果：

```json
{
  "id": 2002,
  "name": "Amy",
  "grade": 88.5
}
```

### 多源组装

```python
import json

from src.mapper_service import transform_multi


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


sources = {
    "student_info": {
        "studentId": 2002,
        "studentName": "Amy"
    },
    "student_score": {
        "score": 88.5
    }
}

schemas = {
    "student_info": load_json(
        "schemas/student_info_schema.json"
    ),
    "student_score": load_json(
        "schemas/student_score_schema.json"
    )
}

mapping_spec = load_json(
    "outputs/multi_source_mapping_spec.json"
)

target_schema = load_json("schemas/target_schema.json")

result = transform_multi(
    sources=sources,
    mapping_spec=mapping_spec,
    schemas=schemas,
    target_schema=target_schema
)

print(result)
```

### 运行完整 API 示例

```bash
python -m examples.api_usage
```

研究生可以参考 `examples/api_usage.py`，将示例数据替换成自己的 JSON 数据和对应的 Schema、MappingSpec。

## 自动化测试

运行全部测试：

```bash
python -m pytest -v
```

测试 Python API：

```bash
python -m pytest tests/test_mapper_service.py -v
```

测试多源组装：

```bash
python -m pytest tests/test_multi_source_assembler.py -v
```

测试数据校验：

```bash
python -m pytest tests/test_validation.py -v
```

## 项目结构

```text
json-semantic-mapper/
├── main.py
├── README.md
├── requirements.txt
├── src/
│   ├── schema_parser.py
│   ├── field_mapper.py
│   ├── llm_mapper.py
│   ├── mapping_spec.py
│   ├── json_transformer.py
│   ├── multi_source_assembler.py
│   ├── generate_multi_source_spec.py
│   └── mapper_service.py
├── schemas/
├── examples/
│   └── api_usage.py
├── outputs/
└── tests/
    ├── test_validation.py
    ├── test_multi_source_assembler.py
    └── test_mapper_service.py
```

## 当前限制

- 当前仅支持项目已实现的 JSON Schema 类型与结构校验子集
- 复杂数组、嵌套结构和多源组装仍需结合具体业务场景验证
- LLM 映射需要人工确认，暂不提供完整的非交互式审核 API
- Schema 更新后，需要重新确认 MappingSpec 与 Schema 指纹的一致性
- 当前主要完成本地 Python 调用，尚未提供 HTTP 服务接口

## 使用说明

本项目适用于需要进行 JSON 字段语义映射、数据转换与多源组装的研究原型及 Python 集成场景。

建议在接入实际业务之前，先使用自身 Schema 和测试数据完成验证。
