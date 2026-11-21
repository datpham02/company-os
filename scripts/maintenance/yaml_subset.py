"""A small, strict YAML subset reader for this repository's registries and schemas (stdlib only, Phase 2).

Supported: block mappings and sequences by indentation (spaces only), `- key: value` items, flow sequences
`[a, b]` and flow mappings `{k: v}`, double- or single-quoted strings, integers, `true`/`false`, `null`/`~`,
plain strings, and `#` comments. Anything else (block scalars `|`/`>`, anchors, tags, multiple documents, tabs) is
refused with the line number: the reader never guesses.
"""
import re


class YamlError(ValueError):
    pass


_INT = re.compile(r"^-?\d+$")


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote and (quote == "'" or line[i - 1] != "\\"):
                quote = None
            continue
        if ch in "\"'" and (i == 0 or line[i - 1] in " \t[{,:"):
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(text, lineno):
    t = text.strip()
    if t == "" or t in ("null", "~"):
        return None
    if t in ("true", "false"):
        return t == "true"
    if t[0] == '"':
        if len(t) < 2 or t[-1] != '"':
            raise YamlError(f"line {lineno}: unterminated double-quoted string")
        body = t[1:-1]
        return re.sub(r'\\(["\\/nt])', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), body)
    if t[0] == "'":
        if len(t) < 2 or t[-1] != "'":
            raise YamlError(f"line {lineno}: unterminated single-quoted string")
        return t[1:-1].replace("''", "'")
    if t[0] in "|>&*!" or t.startswith("---"):
        raise YamlError(f"line {lineno}: unsupported YAML ({t[:12]!r})")
    if _INT.match(t):
        return int(t)
    return t


def _flow(text, lineno):
    pos = 0

    def ws():
        nonlocal pos
        while pos < len(text) and text[pos] == " ":
            pos += 1

    def value():
        nonlocal pos
        ws()
        if pos >= len(text):
            raise YamlError(f"line {lineno}: unexpected end of flow collection")
        ch = text[pos]
        if ch == "[":
            pos += 1
            items = []
            ws()
            if pos < len(text) and text[pos] == "]":
                pos += 1
                return items
            while True:
                items.append(value())
                ws()
                if pos < len(text) and text[pos] == ",":
                    pos += 1
                    continue
                if pos < len(text) and text[pos] == "]":
                    pos += 1
                    return items
                raise YamlError(f"line {lineno}: malformed flow sequence")
        if ch == "{":
            pos += 1
            obj = {}
            ws()
            if pos < len(text) and text[pos] == "}":
                pos += 1
                return obj
            while True:
                ws()
                key = token(":")
                if pos >= len(text) or text[pos] != ":":
                    raise YamlError(f"line {lineno}: flow mapping entry without ':'")
                pos += 1
                if key in obj:
                    raise YamlError(f"line {lineno}: duplicate key {key!r}")
                obj[key] = value()
                ws()
                if pos < len(text) and text[pos] == ",":
                    pos += 1
                    continue
                if pos < len(text) and text[pos] == "}":
                    pos += 1
                    return obj
                raise YamlError(f"line {lineno}: malformed flow mapping")
        return token(",]}")

    def token(stops):
        """A plain or quoted token up to one of `stops`. Keys (stops ':') come back as text; values as scalars."""
        nonlocal pos
        ws()
        start = pos
        if pos < len(text) and text[pos] in "\"'":
            q = text[pos]
            pos += 1
            while pos < len(text) and not (text[pos] == q and (q == "'" or text[pos - 1] != "\\")):
                pos += 1
            pos += 1
            return _scalar(text[start:pos], lineno)
        while pos < len(text) and text[pos] not in stops:
            pos += 1
        raw = text[start:pos].strip()
        return raw if stops == ":" else _scalar(raw, lineno)

    result = value()
    ws()
    if pos != len(text):
        raise YamlError(f"line {lineno}: unexpected text after flow collection")
    return result


def _split_key(content, lineno):
    if content[0] in "\"'":
        q = content[0]
        end = content.find(q, 1)
        if end < 0 or content[end + 1:end + 2] != ":":
            raise YamlError(f"line {lineno}: malformed quoted key")
        return content[1:end], content[end + 2:]
    m = re.match(r"^([^\s:][^:]*?):(\s|$)", content)
    if not m:
        raise YamlError(f"line {lineno}: expected 'key: value', got {content[:40]!r}")
    return m.group(1).strip(), content[m.end():] if m.group(2) else ""


def loads(text):
    lines = []
    for n, raw in enumerate(text.replace("\r\n", "\n").split("\n"), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {n}: tab indentation is not supported")
        stripped = _strip_comment(raw)
        if stripped.strip() == "":
            continue
        if stripped.strip() in ("---", "..."):
            raise YamlError(f"line {n}: multiple documents are not supported")
        lines.append((n, len(stripped) - len(stripped.lstrip(" ")), stripped.strip()))
    if not lines:
        return None
    value, i = _block(lines, 0, lines[0][1])
    if i != len(lines):
        raise YamlError(f"line {lines[i][0]}: unexpected indentation")
    return value


def _value_after(rest, lines, i, indent, lineno):
    rest = rest.strip()
    if rest == "":
        if i < len(lines) and lines[i][1] > indent:
            return _block(lines, i, lines[i][1])
        if i < len(lines) and lines[i][1] == indent and lines[i][2].startswith("- "):
            return _block(lines, i, indent)  # a sequence may sit at the key's own indentation
        return None, i
    if rest[0] in "[{":
        return _flow(rest, lineno), i
    return _scalar(rest, lineno), i


def _block(lines, i, indent):
    n, ind, content = lines[i]
    if content.startswith("- ") or content == "-":
        seq = []
        while i < len(lines) and lines[i][1] == indent and (lines[i][2].startswith("- ") or lines[i][2] == "-"):
            n, ind, content = lines[i]
            item = content[2:].strip() if content != "-" else ""
            i += 1
            if item == "":
                if i < len(lines) and lines[i][1] > indent:
                    v, i = _block(lines, i, lines[i][1])
                else:
                    v = None
            elif item[0] in "[{":
                v = _flow(item, n)
            elif re.match(r"^([^\s:\"'][^:]*?|\"[^\"]*\"|'[^']*'):(\s|$)", item):
                # an inline mapping item: its keys sit at indent + 2
                sub = [(n, indent + 2, item)]
                while i < len(lines) and lines[i][1] > indent:
                    sub.append(lines[i])
                    i += 1
                v, j = _block(sub, 0, indent + 2)
                if j != len(sub):
                    raise YamlError(f"line {sub[j][0]}: unexpected indentation in a sequence item")
            else:
                v = _scalar(item, n)
            seq.append(v)
        return seq, i
    obj = {}
    while i < len(lines) and lines[i][1] == indent and not lines[i][2].startswith("- "):
        n, ind, content = lines[i]
        key, rest = _split_key(content, n)
        if key in obj:
            raise YamlError(f"line {n}: duplicate key {key!r}")
        i += 1
        obj[key], i = _value_after(rest, lines, i, indent, n)
    if i < len(lines) and lines[i][1] > indent:
        raise YamlError(f"line {lines[i][0]}: unexpected indentation")
    return obj, i


def load(path):
    with open(path, encoding="utf-8") as f:
        return loads(f.read())
