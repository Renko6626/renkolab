"""build_abcard.py 纯函数单测（不依赖 local/ 里的解包数据）。  python3 -m pytest tests/test_build_abcard.py -q"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "assets"))
import build_abcard as b  # noqa: E402

BLANK_SPEC = """entry entry3 {
    version: 8,
    name: "ability/dummy.png",
    format: 1,
    width: 64,
    height: 128,
    memoryPriority: 0,
    lowResScale: 0,
    hasData: 1,
    THTXSize: 32768,
    THTXFormat: 1,
    THTXWidth: 64,
    THTXHeight: 128,
    THTXZero: 0,
    sprites: {
        sprite3: { x: 0, y: 0, w: 64, h: 80 }
    }
}

entry entry4 {
    version: 8,
    name: "ability/BLANK_max.png",
    format: 1,
    width: 256,
    height: 512,
    memoryPriority: 0,
    lowResScale: 0,
    hasData: 1,
    THTXSize: 327680,
    THTXFormat: 1,
    THTXWidth: 256,
    THTXHeight: 320,
    THTXZero: 0,
    sprites: {
        sprite4: { x: 0, y: 0, w: 256, h: 320 }
    }
}

script script0 {
-1:
    sprite(sprite4);
    stop();
}
"""


def test_parse_entries_finds_blocks_in_order():
    es = b.parse_entries(BLANK_SPEC)
    assert [e["idx"] for e in es] == [3, 4]
    assert es[1]["name"] == "ability/BLANK_max.png"
    assert es[1]["fields"]["THTXHeight"] == "320"
    assert es[1]["sprite"] == {"x": "0", "y": "0", "w": "256", "h": "320"}
    assert es[1]["block"].startswith("entry entry4 {") and es[1]["block"].rstrip().endswith("}")


def test_make_entry_copies_template_except_name_and_index():
    tpl = b.parse_entries(BLANK_SPEC)[1]
    out = b.make_entry(tpl, 118, "ability/SPADE_10_max.png")
    got = b.parse_entries(out)[0]
    assert got["idx"] == 118
    assert got["name"] == "ability/SPADE_10_max.png"
    assert got["fields"] == tpl["fields"]  # fields 不含 name
    assert got["sprite"] == tpl["sprite"]
    assert "sprite118:" in out


def test_expected_sprites_two_per_card_from_base():
    assert b.expected_sprites(["A", "B"], base=118) == {"A": (118, 119), "B": (120, 121)}
    assert b.expected_sprites([], base=118) == {}


def test_check_cards_js_rules():
    exp = {"A": (118, 119)}
    ok_retail = {"1": {"internal_name": "X", "sprite_large": 116, "sprite_small": 117}}
    ok_new = {"58": {"internal_name": "A", "sprite_large": 118, "sprite_small": 119}}
    bad_pair = {"58": {"internal_name": "A", "sprite_large": 116, "sprite_small": 117}}
    bad_range = {"9": {"internal_name": "Z", "sprite_large": 130, "sprite_small": 131}}
    bad_unlisted = {"9": {"internal_name": "Z", "sprite_large": 118, "sprite_small": 119}}
    assert b.check_cards_js(ok_retail, exp, n_entries=120, base=118) == []
    assert b.check_cards_js(ok_new, exp, n_entries=120, base=118) == []
    assert len(b.check_cards_js(bad_pair, exp, n_entries=120, base=118)) == 1
    assert len(b.check_cards_js(bad_range, exp, n_entries=120, base=118)) >= 1
    assert len(b.check_cards_js(bad_unlisted, exp, n_entries=120, base=118)) == 1


def test_insert_entries_goes_after_last_entry_before_first_script():
    new_block = "entry entry118 {\n    version: 8,\n    name: \"x.png\",\n    sprites: {\n        sprite118: { x: 0, y: 0, w: 1, h: 1 }\n    }\n}\n"
    out = b.insert_entries(BLANK_SPEC, [new_block])
    assert out.index("entry entry4 {") < out.index("entry entry118 {") < out.index("script script0 {")
    assert [e["idx"] for e in b.parse_entries(out)] == [3, 4, 118]
