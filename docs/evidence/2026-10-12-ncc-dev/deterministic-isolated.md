# Deterministic validation

Candidate: 843589922f691c02da8834f5a80fa0b053c93e0ee4b0a5cb2716dc1f52326599
Environment: macOS-26.6.2-arm64-arm-64bit / Python 3.9.6

## unit

Command: python3 -m unittest discover -s scripts -p test_*.py
Exit: 0; elapsed: 186.080s

```text
....................................................................................................................................................
----------------------------------------------------------------------
Ran 148 tests in 185.758s

OK
```

## plugin

Command: python3 scripts/check_plugin.py -v
Exit: 0; elapsed: 0.405s

```text
scout              1750 / 20000
worldbuilder      19708 / 20000
outliner          11216 / 20000
story-editor      15494 / 20000
scholar            8196 / 20000
writer             6166 / 20000
editor             1488 / 20000
continuity         8091 / 20000
pulse              8156 / 20000
reader             4081 / 20000
deconstructor      6490 / 20000
manager:new       34586 / 35000
manager:write     29735 / 35000
manager:review    26008 / 35000
manager:loop      25131 / 35000
manager:prepare   24195 / 35000
curator            6639 / 20000
PLUGIN OK
```

## docs

Command: python3 scripts/build_docs.py --check
Exit: 0; elapsed: 0.058s

```text
DOCS OK
```

## mech

Command: python3 scripts/ncc_eval.py mech
Exit: 0; elapsed: 0.195s

```text
PASS A01-古代时代错置与称谓
PASS A02-月相与行程
PASS A03-待核项写了数字
PASS A04-视角越权与超前泄密
PASS A05-场景卡翻转没发生
PASS A06-干净对照
```

## whitespace

Command: git diff --check
Exit: 0; elapsed: 0.027s

```text

```

## skill

Command: python3 /Users/xuyun/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/ncc-dev
Exit: 0; elapsed: 0.078s

```text
Skill is valid!
```

## Creative contract coverage

106 original creative skill, role and anchor files byte-identical. Registry differs only by commands.ncc-dev. No creative criteria/stages/gates changed.
