from pathlib import Path
import yaml

TAXONOMY_PATH = Path("getnewcspapers/config/ccf_taxonomy.yaml")


def load_taxonomy():
    with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
