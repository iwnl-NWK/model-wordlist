import re

_COMPLIANT = re.compile(r"^\S{1,64}$")
_NUMBERING = re.compile(r"^\s*\d+[\.\)]\s*")
_BULLET = re.compile(r"^[-*]\s+")
_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)


def parse_candidates(text):
    text = _THINK.sub("", text)
    text = text.replace("```", "")
    out = []
    for line in text.splitlines():
        s = line.strip()
        s = _NUMBERING.sub("", s)
        s = _BULLET.sub("", s)
        s = s.strip()
        if s:
            out.append(s)
    return out


def is_compliant(s):
    return bool(_COMPLIANT.match(s))


def count_nonconforming(items):
    return sum(1 for x in items if not is_compliant(x))
