# JSON Semantic Mapper

一个基于 Schema 和声明式映射规则的 JSON 数据转换工具。

## 项目功能

- 解析 JSON Schema，提取字段信息
- 生成候选字段映射规则
- 人工审核 MappingSpec
- 支持单源 JSON 数据转换
- 支持多源 JSON 数据组装
- 检查字段类型、必填字段和映射冲突
- 使用 pytest 进行自动化测试

## 环境要求

- Python 3.12
- Windows 10/11（当前测试环境）
- pip
- pytest（运行自动化测试时使用）


## 安装方法

克隆项目：

```bash
git clone <你的仓库地址>
cd json-semantic-mapper
```

创建虚拟环境：

```bash
python -m venv .venv
```

Windows 激活虚拟环境：

```powershell
.venv\Scripts\activate
```

安装测试依赖：

```bash
python -m pip install pytest
```


## 使用方法

### 单源 JSON 转换

```bash
python main.py --mode single
```

程序读取单源 JSON 数据和 MappingSpec，根据映射规则执行转换。

输出文件：

`outputs/transformed_student.json`

### 多源 JSON 组装

```bash
python main.py --mode multi
```

程序读取学生信息和成绩两个数据源，按 MappingSpec 进行组装，并完成目标 Schema 校验。

输出文件：

`outputs/multi_source_result.json`

### 查看命令行帮助

```bash
python main.py --help
```


## 自动化测试

运行全部测试：

```bash
python -m pytest -v
```

单独运行多源组装测试：

```bash
python -m pytest tests/test_multi_source_assembler.py -v
```

单独运行数据校验测试：

```bash
python -m pytest tests/test_validation.py -v
```


## 字段映射说明

项目支持基于字段名称、描述和类型生成候选映射。

同时实现了 LLM 候选映射结果的模拟、规则校验及人工审核流程。

当前演示使用模拟 LLM 响应（Mock），尚未接入真实 LLM API。因此，演示结果不代表真实模型的映射效果。

数据转换与组装阶段不需要实时调用 LLM，而是执行已经确认的 MappingSpec。
