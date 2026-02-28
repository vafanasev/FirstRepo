from __future__ import annotations

import argparse
from pathlib import Path

from exporters import export_to_excel, export_to_json
from promethease_parser import parse_promethease_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="promethease_ru", description="Локальный парсер отчётов Promethease")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Распарсить отчёт и сохранить результат")
    parse_cmd.add_argument("input", help="Путь к .html/.htm/.zip")
    parse_cmd.add_argument("--out", required=True, help="Путь к .xlsx или .json")
    parse_cmd.add_argument("--min-mag", type=float, default=0.0, help="Минимальная magnitude")
    parse_cmd.add_argument("--repute", default="", help="Фильтр по repute: bad,good,neutral,unknown")
    return parser


def cmd_parse(args: argparse.Namespace) -> int:
    df = parse_promethease_report(args.input)
    if args.repute:
        allowed = {x.strip().lower() for x in args.repute.split(",") if x.strip()}
        df = df[df["repute"].isin(allowed)]
    df = df[df["magnitude"] >= args.min_mag]

    out = Path(args.out)
    if out.suffix.lower() == ".xlsx":
        export_to_excel(df, out)
    elif out.suffix.lower() == ".json":
        export_to_json(df, out)
    else:
        raise ValueError("--out должен быть .xlsx или .json")

    print(f"Сохранено записей: {len(df)} -> {out}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        return cmd_parse(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
