import argparse

from src.multi_source_assembler import main as run_multi_source
from src.json_transformer import main as run_single_source

def main():
    parser=argparse.ArgumentParser(
        description="JSON Semantic Mapper"
    )

    #规定用户可以输入什么
    parser.add_argument(
        "--mode",
        choices=["multi","single"],
        default="multi",
        help="选择 JSON 转换模式"
    )

    #真正读取用户输入了什么
    args=parser.parse_args()

    if args.mode == "single":
        run_single_source()
    elif args.mode == "multi":
        run_multi_source()

if __name__ == "__main__":
    main()