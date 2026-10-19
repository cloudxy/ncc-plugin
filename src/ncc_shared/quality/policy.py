import json
from importlib.resources import files

from ncc_shared.serialization import digest

POLICY = json.loads(files("ncc_shared.quality").joinpath("resources/policy.json").read_text())
POLICY_HASH = digest(POLICY)
