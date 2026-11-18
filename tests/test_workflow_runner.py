import json
import unittest
from pathlib import Path

from src.workflow_runner import run_workflow


# 读取项目中的 JSON 文件
def load_json(path):
    root = Path(__file__).resolve().parents[1]

    with open(root / path, "r", encoding="utf-8") as file:
        return json.load(file)


# 测试完整 JSON 数据处理流程
class TestWorkflowRunner(unittest.TestCase):

    def setUp(self):
        self.source_data = load_json("examples/student_input.json")
        self.mapping_spec = load_json("outputs/mapping_spec.json")
        self.source_schema = load_json("schemas/source_schema.json")
        self.target_schema = load_json("schemas/target_schema.json")

    # 测试输出缺少必填字段
    def test_missing_required_field(self):
        code = 'output = dict(input_data)\ndel output["id"]'

        with self.assertRaisesRegex(ValueError, "缺少必填字段"):
            run_workflow(
                self.source_data,
                self.mapping_spec,
                self.source_schema,
                self.target_schema,
                code
            )

    # 测试输出字段类型错误
    def test_invalid_output_type(self):
        code = """
output = dict(input_data)\n
output["grade"] = "ninety"
"""

        with self.assertRaisesRegex(ValueError, "应该是 number"):
            run_workflow(
                self.source_data,
                self.mapping_spec,
                self.source_schema,
                self.target_schema,
                code
            )

    # 测试字段映射与 Python 转换
    def test_full_workflow(self):
        code = """
output = dict(input_data)
output["grade"] = round(input_data["grade"])
"""

        result = run_workflow(
            self.source_data,
            self.mapping_spec,
            self.source_schema,
            self.target_schema,
            code
        )

        self.assertEqual(result["id"], 1001)
        self.assertEqual(result["name"], "Tom")
        self.assertEqual(result["grade"], 96)

    # 测试完整工作流能否返回日志
    def test_workflow_logs(self):
        code = """
print("开始处理学生数据")
output = dict(input_data)
print("处理完成")
"""

        result, logs = run_workflow(
            self.source_data,
            self.mapping_spec,
            self.source_schema,
            self.target_schema,
            code,
            return_logs=True
        )

        self.assertEqual(result["grade"], 95.5)
        self.assertIn("开始处理学生数据", logs)
        self.assertIn("处理完成", logs)


if __name__ == "__main__":
    unittest.main()