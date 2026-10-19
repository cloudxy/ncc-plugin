import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal


def jsonable(value):
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def canonical(value):
    return json.dumps(
        jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value):
    raw = (
        value
        if isinstance(value, bytes)
        else (value if isinstance(value, str) else canonical(value)).encode()
    )
    return hashlib.sha256(raw).hexdigest()


def search_tokens(text):
    words = re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]+", text.lower())
    tokens = []
    for word in words:
        if re.match(r"^[\u3400-\u9fff]", word):
            tokens.extend(word[i : i + 2] for i in range(max(1, len(word) - 1)))
        else:
            tokens.append(word)
    return " ".join(dict.fromkeys(tokens))
