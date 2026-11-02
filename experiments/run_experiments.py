
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path


# 将项目根目录加入 Python 模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_mapper import (
    build_prompt,
    call_deepseek,
    validate_llm_result
)


# 读取 JSON 文件
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# 保存 JSON 文件
def save_json(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


# 获取字段名称
def get_field_name(field):
    return field["path"].split(".")[-1]


# 判断字段类型是否兼容
def types_compatible(source_type, target_type):
    return (
        source_type == target_type
        or (
            source_type == "integer"
            and target_type == "number"
        )
    )


# 字段名称完全匹配
def exact_name_matching(source_fields, target_fields):
    mappings = []
    used_sources = set()

    for target in target_fields:
        target_name = get_field_name(target)

        for source in source_fields:
            source_name = get_field_name(source)

            if source["path"] in used_sources:
                continue

            if (
                source_name == target_name
                and types_compatible(
                    source["type"],
                    target["type"]
                )
            ):
                mappings.append({
                    "source": source["path"],
                    "target": target["path"],
                    "reason": "字段名称相同且类型兼容"
                })

                used_sources.add(source["path"])
                break

    return mappings


# 根据名称、描述和类型进行规则匹配
def rule_based_matching(source_fields, target_fields):
    mappings = []
    used_sources = set()

    for target in target_fields:
        target_name = get_field_name(target)
        target_description = target.get("description", "").strip()

        candidates = []

        for source in source_fields:
            if source["path"] in used_sources:
                continue

            if not types_compatible(
                source["type"],
                target["type"]
            ):
                continue

            source_name = get_field_name(source)
            source_description = source.get(
                "description", ""
            ).strip()

            score = 0
            reason = ""

            if source_name == target_name:
                score = 2
                reason = "字段名称相同且类型兼容"

            elif (
                source_description
                and target_description
                and source_description == target_description
            ):
                score = 1
                reason = "字段描述相同且类型兼容"

            if score > 0:
                candidates.append((score, source, reason))

        if not candidates:
            continue

        candidates.sort(key=lambda item: item[0], reverse=True)

        best_score = candidates[0][0]
        best_candidates = [
            item for item in candidates
            if item[0] == best_score
        ]

        # 多个候选字段得分相同，视为歧义，不自动匹配
        if len(best_candidates) != 1:
            continue

        _, best_source, reason = best_candidates[0]

        mappings.append({
            "source": best_source["path"],
            "target": target["path"],
            "reason": reason
        })

        used_sources.add(best_source["path"])

    return mappings


# 将映射列表转换为集合
def mapping_pairs(mappings):
    return {
        (mapping["source"], mapping["target"])
        for mapping in mappings
    }


# 计算映射评价指标
def evaluate_mappings(predicted, expected):
    predicted_pairs = mapping_pairs(predicted)
    expected_pairs = mapping_pairs(expected)

    correct = len(predicted_pairs & expected_pairs)

    false_positive = len(predicted_pairs - expected_pairs)
    false_negative = len(expected_pairs - predicted_pairs)

    precision = (
        correct / len(predicted_pairs)
        if predicted_pairs else
        (1.0 if not expected_pairs else 0.0)
    )

    recall = (
        correct / len(expected_pairs)
        if expected_pairs else 1.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0 else 0.0
    )

    exact_match = int(predicted_pairs == expected_pairs)

    return {
        "correct": correct,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "exact_match": exact_match
    }


# 使用真实 DeepSeek 进行字段语义映射
def deepseek_matching(source_fields, target_fields):
    prompt = build_prompt(source_fields, target_fields)

    result = call_deepseek(prompt)

    validate_llm_result(
        result,
        source_fields,
        target_fields
    )

    return result["mappings"]


# 使用固定模拟响应验证实验流程
def mock_matching(source_fields, target_fields):
    mappings = []

    for target in target_fields:
        target_description = target.get("description", "")

        if target["path"] == "$.id":
            for source in source_fields:
                if source["path"] == "$.studentId":
                    mappings.append({
                        "source": source["path"],
                        "target": target["path"],
                        "reason": "模拟映射结果"
                    })
                    break

    return mappings


# 执行单个实验方法
def run_method(method_name, method, source_fields, target_fields, expected):
    start_time = time.perf_counter()

    try:
        predicted = method(source_fields, target_fields)

        elapsed_ms = (
            time.perf_counter() - start_time
        ) * 1000

        metrics = evaluate_mappings(
            predicted,
            expected
        )

        return {
            "method": method_name,
            "status": "success",
            "predicted_mappings": predicted,
            "elapsed_ms": round(elapsed_ms, 3),
            **metrics
        }

    except Exception as e:
        elapsed_ms = (
            time.perf_counter() - start_time
        ) * 1000

        return {
            "method": method_name,
            "status": "error",
            "error": str(e),
            "predicted_mappings": [],
            "elapsed_ms": round(elapsed_ms, 3),
            "correct": None,
            "false_positive": None,
            "false_negative": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "exact_match": None
        }


# 汇总实验结果
def summarize_results(all_results):
    methods = {}

    for case_result in all_results:
        for result in case_result["results"]:
            name = result["method"]

            if name not in methods:
                methods[name] = []

            methods[name].append(result)

    summary = {}

    for method_name, results in methods.items():
        successful = [
            result for result in results
            if result["status"] == "success"
        ]

        if not successful:
            summary[method_name] = {
                "total_cases": len(results),
                "successful_cases": 0,
                "failed_cases": len(results),
                "precision": None,
                "recall": None,
                "f1": None,
                "exact_match_rate": None,
                "avg_elapsed_ms": None
            }
            continue

        total_correct = sum(
            result["correct"] for result in successful
        )

        total_fp = sum(
            result["false_positive"] for result in successful
        )

        total_fn = sum(
            result["false_negative"] for result in successful
        )

        precision_denominator = total_correct + total_fp
        recall_denominator = total_correct + total_fn

        precision = (
            total_correct / precision_denominator
            if precision_denominator else 1.0
        )

        recall = (
            total_correct / recall_denominator
            if recall_denominator else 1.0
        )

        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0 else 0.0
        )

        exact_match_rate = sum(
            result["exact_match"] for result in successful
        ) / len(successful)

        avg_elapsed_ms = sum(
            result["elapsed_ms"] for result in successful
        ) / len(successful)

        summary[method_name] = {
            "total_cases": len(results),
            "successful_cases": len(successful),
            "failed_cases": len(results) - len(successful),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "exact_match_rate": round(exact_match_rate, 4),
            "avg_elapsed_ms": round(avg_elapsed_ms, 3)
        }

    return summary


# 将每个案例的实验结果保存为 CSV
def save_csv(file_path, all_results):
    rows = []

    for case_result in all_results:
        for result in case_result["results"]:
            rows.append({
                "case_id": case_result["case_id"],
                "method": result["method"],
                "status": result["status"],
                "correct": result["correct"],
                "false_positive": result["false_positive"],
                "false_negative": result["false_negative"],
                "precision": result["precision"],
                "recall": result["recall"],
                "f1": result["f1"],
                "exact_match": result["exact_match"],
                "elapsed_ms": result["elapsed_ms"],
                "error": result.get("error", "")
            })

    fieldnames = [
        "case_id",
        "method",
        "status",
        "correct",
        "false_positive",
        "false_negative",
        "precision",
        "recall",
        "f1",
        "exact_match",
        "elapsed_ms",
        "error"
    ]

    with open(file_path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# 运行全部实验案例
def run_experiments(provider):
    cases = load_json(
        "experiments/experiment_cases.json"
    )

    if not isinstance(cases, list) or not cases:
        raise ValueError("实验数据必须是非空数组")

    methods = {
        "exact_name": exact_name_matching,
        "rule_based": rule_based_matching
    }

    if provider == "deepseek":
        methods["deepseek"] = deepseek_matching

    elif provider == "mock":
        methods["mock"] = mock_matching

    all_results = []

    print("实验案例数量：", len(cases))
    print("LLM 模式：", provider)

    for case in cases:
        case_id = case["case_id"]
        source_fields = case["source_fields"]
        target_fields = case["target_fields"]
        expected = case["expected_mappings"]

        print(f"\n正在测试：{case_id}")

        case_results = []

        for method_name, method in methods.items():
            result = run_method(
                method_name,
                method,
                source_fields,
                target_fields,
                expected
            )

            case_results.append(result)

            if result["status"] == "success":
                print(
                    f"{method_name}: "
                    f"Precision={result['precision']:.4f}, "
                    f"Recall={result['recall']:.4f}, "
                    f"F1={result['f1']:.4f}, "
                    f"Time={result['elapsed_ms']:.3f}ms"
                )
            else:
                print(
                    f"{method_name}: ERROR - {result['error']}"
                )

        all_results.append({
            "case_id": case_id,
            "expected_mappings": expected,
            "results": case_results
        })

    summary = summarize_results(all_results)

    experiment_output = {
        "provider": provider,
        "case_count": len(cases),
        "summary": summary,
        "cases": all_results
    }

    json_path = f"experiments/results_{provider}.json"
    csv_path = f"experiments/results_{provider}.csv"

    save_json(json_path, experiment_output)
    save_csv(csv_path, all_results)

    print("\n实验汇总：")

    for method_name, metrics in summary.items():
        print(f"\n方法：{method_name}")
        print("成功案例：", metrics["successful_cases"])
        print("失败案例：", metrics["failed_cases"])
        print("Precision：", metrics["precision"])
        print("Recall：", metrics["recall"])
        print("F1：", metrics["f1"])
        print("完全匹配率：", metrics["exact_match_rate"])
        print("平均耗时(ms)：", metrics["avg_elapsed_ms"])

    print("\n实验完成")
    print("JSON 结果：", json_path)
    print("CSV 结果：", csv_path)


# 命令行入口
def main():
    parser = argparse.ArgumentParser(
        description="JSON Semantic Mapper 字段映射对比实验"
    )

    parser.add_argument(
        "--provider",
        choices=["mock", "deepseek"],
        default="mock",
        help="选择模拟实验或真实 DeepSeek 实验"
    )

    args = parser.parse_args()

    run_experiments(args.provider)


if __name__ == "__main__":
    main()
