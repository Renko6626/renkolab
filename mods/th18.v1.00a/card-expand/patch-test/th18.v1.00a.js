{
  "codecaves": {
    "th18_ce_test_deck58": {
      "code": "0fb6843008f6050083f8387505b83a000000c3",
      "access": "RX",
      "title": "测试：初始卡组的空槽(56) → id 58"
    }
  },
  "binhacks": {
    "test_deck58_407ee3": {
      "addr": "0x407ee3",
      "code": "e8[codecave:th18_ce_test_deck58]909090",
      "expected": "0fb6843008f60500",
      "title": "测试：reset_cards 读到空槽时改发 id 58"
    }
  },
  "breakpoints": {
    "ce_trace_alloc": {
      "addr": "0x411469",
      "cavesize": 7,
      "expected": "817f2800010000",
      "title": "测试：记录每次 allocate_new_card(id, mode)"
    }
  }
}
