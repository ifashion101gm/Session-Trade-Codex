"""Run the pure SSPF refined-hybrid research validator on a JSON payload."""

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session_strategy.refined_hybrid_validator import validate


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    config = yaml.safe_load((ROOT / "config" / "no_trade_research.yaml").read_text())
    result = validate(payload, config)
    rendered = json.dumps(result, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
