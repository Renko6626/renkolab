{
  "codecaves": {
    "th18_card_table": {
      "size": "0x33cc",
      "access": "RW",
      "title": "zTableCardData[] 搬迁目标（255 行 × 0x34）"
    },
    "th18_card_jumptable": {
      "size": "0x3fc",
      "access": "RW",
      "title": "allocate_new_card 跳转表搬迁目标（255 项）"
    },
    "th18_card_unlocked": {
      "size": "0x100",
      "access": "RW",
      "title": "unlocked_cards 影子数组（256 字节，下标 = card id；DLL 填）"
    },
    "th18_card_order": {
      "size": "0x3fc",
      "access": "RW",
      "title": "显示顺序表搬迁目标（255 项；DLL 重排并追加新卡）"
    },
    "th18_card_table_patch_init": {
      "code": "fc60bf<codecave:th18_card_table>be<Rxc53c0>b9f2020000f3a5bbc5000000be<codecave:th18_card_table+b60>b90d000000f3a54b75f1bf<codecave:th18_card_jumptable>be<Rx12dac>b939000000f3a5b8<Rx11489>b9c6000000f3abbf<codecave:th18_card_order>be<Rxb3600>b939000000f3a5b839000000b9c6000000f3ab61c3",
      "export": true,
      "access": "RX",
      "title": "开机把零售表（与跳转表）拷进 codecave；DLL 的 post_init 是权威，这里是保险"
    }
  },
  "binhacks": {
    "cardtable_start_407d72": {
      "addr": "0x407d72",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_407d7f": {
      "addr": "0x407d7f",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_407d86": {
      "addr": "0x407d86",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_407d8f": {
      "addr": "0x407d8f",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_409321": {
      "addr": "0x409321",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_40932f": {
      "addr": "0x40932f",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_409336": {
      "addr": "0x409336",
      "code": "c7450c<codecave:th18_card_table+b90>",
      "expected": "c7450c505f4c00",
      "title": "fallback | mov [ebp+0xc], K | +0xb90"
    },
    "cardtable_hit_409342": {
      "addr": "0x409342",
      "code": "05<codecave:th18_card_table+30>",
      "expected": "05f0534c00",
      "title": "hit | add eax, K | +0x30"
    },
    "cardtable_start_414412": {
      "addr": "0x414412",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_414428": {
      "addr": "0x414428",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_41442f": {
      "addr": "0x41442f",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_414439": {
      "addr": "0x414439",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_414457": {
      "addr": "0x414457",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_414468": {
      "addr": "0x414468",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_41446f": {
      "addr": "0x41446f",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_414483": {
      "addr": "0x414483",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_end_41449d": {
      "addr": "0x41449d",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4144a4": {
      "addr": "0x4144a4",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_4144ae": {
      "addr": "0x4144ae",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_4144c9": {
      "addr": "0x4144c9",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4144d9": {
      "addr": "0x4144d9",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4144e0": {
      "addr": "0x4144e0",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_4144ea": {
      "addr": "0x4144ea",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_4149b4": {
      "addr": "0x4149b4",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4149c8": {
      "addr": "0x4149c8",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4149cf": {
      "addr": "0x4149cf",
      "code": "b8<codecave:th18_card_table+b80>",
      "expected": "b8405f4c00",
      "title": "fallback | mov eax, K | +0xb80"
    },
    "cardtable_hit_4149d9": {
      "addr": "0x4149d9",
      "code": "05<codecave:th18_card_table+20>",
      "expected": "05e0534c00",
      "title": "hit | add eax, K | +0x20"
    },
    "cardtable_start_4149fc": {
      "addr": "0x4149fc",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_414a09": {
      "addr": "0x414a09",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_414a10": {
      "addr": "0x414a10",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_414a1a": {
      "addr": "0x414a1a",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_414a62": {
      "addr": "0x414a62",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_414a6f": {
      "addr": "0x414a6f",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_414a76": {
      "addr": "0x414a76",
      "code": "b8<codecave:th18_card_table+b60>",
      "expected": "b8205f4c00",
      "title": "fallback | mov eax, K | +0xb60"
    },
    "cardtable_hit_414a80": {
      "addr": "0x414a80",
      "code": "05<codecave:th18_card_table>",
      "expected": "05c0534c00",
      "title": "hit | add eax, K | +0x0"
    },
    "cardtable_start_41612f": {
      "addr": "0x41612f",
      "code": "be<codecave:th18_card_table>",
      "expected": "bec0534c00",
      "title": "start | mov esi, K | +0x0"
    },
    "cardtable_end_41616d": {
      "addr": "0x41616d",
      "code": "81fe<codecave:th18_card_table+33cc>",
      "expected": "81fe885f4c00",
      "title": "end | cmp esi, K | +0x33cc"
    },
    "cardtable_fallback_416175": {
      "addr": "0x416175",
      "code": "bb<codecave:th18_card_table+b64>",
      "expected": "bb245f4c00",
      "title": "fallback | mov ebx, K | +0xb64"
    },
    "cardtable_hit_41617f": {
      "addr": "0x41617f",
      "code": "81c3<codecave:th18_card_table+4>",
      "expected": "81c3c4534c00",
      "title": "hit | add ebx, K | +0x4"
    },
    "cardtable_start_416960": {
      "addr": "0x416960",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_41696d": {
      "addr": "0x41696d",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_416974": {
      "addr": "0x416974",
      "code": "b8<codecave:th18_card_table+b6c>",
      "expected": "b82c5f4c00",
      "title": "fallback | mov eax, K | +0xb6c"
    },
    "cardtable_hit_41697e": {
      "addr": "0x41697e",
      "code": "8d80<codecave:th18_card_table+c>",
      "expected": "8d80cc534c00",
      "title": "hit | lea eax, [eax+K] | +0xc"
    },
    "cardtable_start_416fad": {
      "addr": "0x416fad",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_416fba": {
      "addr": "0x416fba",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_416fc1": {
      "addr": "0x416fc1",
      "code": "b8<codecave:th18_card_table+b7c>",
      "expected": "b83c5f4c00",
      "title": "fallback | mov eax, K | +0xb7c"
    },
    "cardtable_hit_416fcb": {
      "addr": "0x416fcb",
      "code": "8d80<codecave:th18_card_table+1c>",
      "expected": "8d80dc534c00",
      "title": "hit | lea eax, [eax+K] | +0x1c"
    },
    "cardtable_start_416fdc": {
      "addr": "0x416fdc",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_416fe9": {
      "addr": "0x416fe9",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_416ff0": {
      "addr": "0x416ff0",
      "code": "b9<codecave:th18_card_table+b60>",
      "expected": "b9205f4c00",
      "title": "fallback | mov ecx, K | +0xb60"
    },
    "cardtable_hit_416ffa": {
      "addr": "0x416ffa",
      "code": "81c1<codecave:th18_card_table>",
      "expected": "81c1c0534c00",
      "title": "hit | add ecx, K | +0x0"
    },
    "cardtable_start_417010": {
      "addr": "0x417010",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_41701d": {
      "addr": "0x41701d",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_417024": {
      "addr": "0x417024",
      "code": "b8<codecave:th18_card_table+b70>",
      "expected": "b8305f4c00",
      "title": "fallback | mov eax, K | +0xb70"
    },
    "cardtable_hit_41702e": {
      "addr": "0x41702e",
      "code": "8d80<codecave:th18_card_table+10>",
      "expected": "8d80d0534c00",
      "title": "hit | lea eax, [eax+K] | +0x10"
    },
    "cardtable_start_417044": {
      "addr": "0x417044",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_417058": {
      "addr": "0x417058",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_41705f": {
      "addr": "0x41705f",
      "code": "b8<codecave:th18_card_table+b70>",
      "expected": "b8305f4c00",
      "title": "fallback | mov eax, K | +0xb70"
    },
    "cardtable_hit_417069": {
      "addr": "0x417069",
      "code": "8d80<codecave:th18_card_table+10>",
      "expected": "8d80d0534c00",
      "title": "hit | lea eax, [eax+K] | +0x10"
    },
    "cardtable_start_41707c": {
      "addr": "0x41707c",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_417089": {
      "addr": "0x417089",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_417090": {
      "addr": "0x417090",
      "code": "b8<codecave:th18_card_table+b74>",
      "expected": "b8345f4c00",
      "title": "fallback | mov eax, K | +0xb74"
    },
    "cardtable_hit_41709a": {
      "addr": "0x41709a",
      "code": "8d80<codecave:th18_card_table+14>",
      "expected": "8d80d4534c00",
      "title": "hit | lea eax, [eax+K] | +0x14"
    },
    "cardtable_start_4170ab": {
      "addr": "0x4170ab",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4170b8": {
      "addr": "0x4170b8",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4170bf": {
      "addr": "0x4170bf",
      "code": "b8<codecave:th18_card_table+b74>",
      "expected": "b8345f4c00",
      "title": "fallback | mov eax, K | +0xb74"
    },
    "cardtable_hit_4170c9": {
      "addr": "0x4170c9",
      "code": "8d80<codecave:th18_card_table+14>",
      "expected": "8d80d4534c00",
      "title": "hit | lea eax, [eax+K] | +0x14"
    },
    "cardtable_start_41745d": {
      "addr": "0x41745d",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_41746a": {
      "addr": "0x41746a",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_417471": {
      "addr": "0x417471",
      "code": "b8<codecave:th18_card_table+b7c>",
      "expected": "b83c5f4c00",
      "title": "fallback | mov eax, K | +0xb7c"
    },
    "cardtable_hit_41747b": {
      "addr": "0x41747b",
      "code": "8d80<codecave:th18_card_table+1c>",
      "expected": "8d80dc534c00",
      "title": "hit | lea eax, [eax+K] | +0x1c"
    },
    "cardtable_start_41748c": {
      "addr": "0x41748c",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_417499": {
      "addr": "0x417499",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4174a0": {
      "addr": "0x4174a0",
      "code": "b9<codecave:th18_card_table+b60>",
      "expected": "b9205f4c00",
      "title": "fallback | mov ecx, K | +0xb60"
    },
    "cardtable_hit_4174aa": {
      "addr": "0x4174aa",
      "code": "81c1<codecave:th18_card_table>",
      "expected": "81c1c0534c00",
      "title": "hit | add ecx, K | +0x0"
    },
    "cardtable_start_4174bc": {
      "addr": "0x4174bc",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4174c9": {
      "addr": "0x4174c9",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4174d0": {
      "addr": "0x4174d0",
      "code": "b8<codecave:th18_card_table+b74>",
      "expected": "b8345f4c00",
      "title": "fallback | mov eax, K | +0xb74"
    },
    "cardtable_hit_4174da": {
      "addr": "0x4174da",
      "code": "8d80<codecave:th18_card_table+14>",
      "expected": "8d80d4534c00",
      "title": "hit | lea eax, [eax+K] | +0x14"
    },
    "cardtable_start_4174e7": {
      "addr": "0x4174e7",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4174f8": {
      "addr": "0x4174f8",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4174ff": {
      "addr": "0x4174ff",
      "code": "b9<codecave:th18_card_table+b60>",
      "expected": "b9205f4c00",
      "title": "fallback | mov ecx, K | +0xb60"
    },
    "cardtable_hit_417509": {
      "addr": "0x417509",
      "code": "81c1<codecave:th18_card_table>",
      "expected": "81c1c0534c00",
      "title": "hit | add ecx, K | +0x0"
    },
    "cardtable_start_41754d": {
      "addr": "0x41754d",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_41755a": {
      "addr": "0x41755a",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_417561": {
      "addr": "0x417561",
      "code": "b8<codecave:th18_card_table+b7c>",
      "expected": "b83c5f4c00",
      "title": "fallback | mov eax, K | +0xb7c"
    },
    "cardtable_hit_41756b": {
      "addr": "0x41756b",
      "code": "8d80<codecave:th18_card_table+1c>",
      "expected": "8d80dc534c00",
      "title": "hit | lea eax, [eax+K] | +0x1c"
    },
    "cardtable_start_417578": {
      "addr": "0x417578",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_417588": {
      "addr": "0x417588",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_41758f": {
      "addr": "0x41758f",
      "code": "b9<codecave:th18_card_table+b60>",
      "expected": "b9205f4c00",
      "title": "fallback | mov ecx, K | +0xb60"
    },
    "cardtable_hit_417599": {
      "addr": "0x417599",
      "code": "81c1<codecave:th18_card_table>",
      "expected": "81c1c0534c00",
      "title": "hit | add ecx, K | +0x0"
    },
    "cardtable_start_4175ab": {
      "addr": "0x4175ab",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4175b8": {
      "addr": "0x4175b8",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4175bf": {
      "addr": "0x4175bf",
      "code": "b9<codecave:th18_card_table+b60>",
      "expected": "b9205f4c00",
      "title": "fallback | mov ecx, K | +0xb60"
    },
    "cardtable_hit_4175c9": {
      "addr": "0x4175c9",
      "code": "81c1<codecave:th18_card_table>",
      "expected": "81c1c0534c00",
      "title": "hit | add ecx, K | +0x0"
    },
    "cardtable_start_418e0e": {
      "addr": "0x418e0e",
      "code": "ba<codecave:th18_card_table+4>",
      "expected": "bac4534c00",
      "title": "start | mov edx, K | +0x4"
    },
    "cardtable_start_4636b2": {
      "addr": "0x4636b2",
      "code": "b8<codecave:th18_card_table+4>",
      "expected": "b8c4534c00",
      "title": "start | mov eax, K | +0x4"
    },
    "cardtable_end_4636bf": {
      "addr": "0x4636bf",
      "code": "3d<codecave:th18_card_table+33d0>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0x33d0"
    },
    "cardtable_fallback_4636c6": {
      "addr": "0x4636c6",
      "code": "b8<codecave:th18_card_table+b84>",
      "expected": "b8445f4c00",
      "title": "fallback | mov eax, K | +0xb84"
    },
    "cardtable_hit_4636d0": {
      "addr": "0x4636d0",
      "code": "05<codecave:th18_card_table+24>",
      "expected": "05e4534c00",
      "title": "hit | add eax, K | +0x24"
    },
    "alloc_bound_411479": {
      "addr": "0x411479",
      "code": "83fbfe",
      "expected": "83fb38",
      "title": "allocate_new_card: cmp ebx, 0x38 → 0xfe（可分配 id 上界）"
    },
    "alloc_jumptable_411482": {
      "addr": "0x411482",
      "code": "ff249d<codecave:th18_card_jumptable>",
      "expected": "ff249dac2d4100",
      "title": "allocate_new_card: jmp [0x412dac+ebx*4] → 新跳转表"
    },
    "grow_4082d6": {
      "addr": "0x4082d6",
      "code": "686c110000",
      "expected": "68700d0000",
      "title": "zAbilityManager operator_new 分配：0xd70 → 0x116c"
    },
    "grow_4082ec": {
      "addr": "0x4082ec",
      "code": "686c110000",
      "expected": "68700d0000",
      "title": "zAbilityManager operator_new 的 memset：0xd70 → 0x116c"
    },
    "grow_40860a": {
      "addr": "0x40860a",
      "code": "686c110000",
      "expected": "68700d0000",
      "title": "zAbilityManager sized delete：0xd70 → 0x116c"
    },
    "grow_407eb0": {
      "addr": "0x407eb0",
      "code": "8dbb700d0000",
      "expected": "8dbb840c0000",
      "title": "reset_cards：lea edi,[mgr+owned]"
    },
    "grow_407eb6": {
      "addr": "0x407eb6",
      "code": "b9ff000000",
      "expected": "b938000000",
      "title": "reset_cards：rep stosd 项数 56 → 255"
    },
    "grow_412d42": {
      "addr": "0x412d42",
      "code": "c78487700d000001000000",
      "expected": "c78487840c000001000000",
      "title": "allocate_new_card 尾段：owned[id] = 1"
    },
    "grow_416f8f": {
      "addr": "0x416f8f",
      "code": "b9700d0000",
      "expected": "b9840c0000",
      "title": "商店循环起点 → +0xd70"
    },
    "grow_41744a": {
      "addr": "0x41744a",
      "code": "bb700d0000",
      "expected": "bb840c0000",
      "title": "商店循环起点 → +0xd70"
    },
    "grow_417535": {
      "addr": "0x417535",
      "code": "bb700d0000",
      "expected": "bb840c0000",
      "title": "商店循环起点 → +0xd70"
    },
    "grow_41716b": {
      "addr": "0x41716b",
      "code": "81f9500e0000",
      "expected": "81f9640d0000",
      "title": "商店循环上界 → +0xe50（仍只看前 56 个 id）"
    },
    "grow_417527": {
      "addr": "0x417527",
      "code": "81fb500e0000",
      "expected": "81fb640d0000",
      "title": "商店循环上界 → +0xe50（仍只看前 56 个 id）"
    },
    "grow_4175e7": {
      "addr": "0x4175e7",
      "code": "81fb500e0000",
      "expected": "81fb640d0000",
      "title": "商店循环上界 → +0xe50（仍只看前 56 个 id）"
    },
    "unlock_41440b": {
      "addr": "0x41440b",
      "code": "388a<codecave:th18_card_unlocked>90",
      "expected": "388c1088f50500",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,r8 [eax+edx+0x5f588] → [edx+SHADOW]（eax = 存档指针）"
    },
    "unlock_4149ec": {
      "addr": "0x4149ec",
      "code": "80be<codecave:th18_card_unlocked>0090",
      "expected": "80bc0688f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [esi+eax+0x5f588] → [esi+SHADOW]（eax = 存档指针）"
    },
    "unlock_416590": {
      "addr": "0x416590",
      "code": "80bb<codecave:th18_card_unlocked>0090",
      "expected": "80bc1888f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [eax+ebx+0x5f588] → [ebx+SHADOW]（eax = 存档指针）"
    },
    "unlock_41694e": {
      "addr": "0x41694e",
      "code": "80ba<codecave:th18_card_unlocked>0090",
      "expected": "80bc1088f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [eax+edx+0x5f588] → [edx+SHADOW]（eax = 存档指针）"
    },
    "unlock_416e3d": {
      "addr": "0x416e3d",
      "code": "3882<codecave:th18_card_unlocked>90",
      "expected": "38840a88f50500",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,r8 [edx+ecx+0x5f588] → [edx+SHADOW]（ecx = 存档指针）"
    },
    "unlock_417125": {
      "addr": "0x417125",
      "code": "80be<codecave:th18_card_unlocked>0090",
      "expected": "80bc3088f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [eax+esi+0x5f588] → [esi+SHADOW]（eax = 存档指针）"
    },
    "unlock_417ea3": {
      "addr": "0x417ea3",
      "code": "80b9<codecave:th18_card_unlocked>0090",
      "expected": "80bc0188f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [ecx+eax+0x5f588] → [ecx+SHADOW]（eax = 存档指针）"
    },
    "unlock_418df6": {
      "addr": "0x418df6",
      "code": "80bf<codecave:th18_card_unlocked>0090",
      "expected": "80bc3e88f5050000",
      "title": "unlocked_cards 读 → 影子数组：cmp m8,imm8 [esi+edi+0x5f588] → [edi+SHADOW]（esi = 存档指针）"
    },
    "unlock_418e15": {
      "addr": "0x418e15",
      "code": "8a80<codecave:th18_card_unlocked>90",
      "expected": "8a840688f50500",
      "title": "unlocked_cards 读 → 影子数组：mov r8,m8 [esi+eax+0x5f588] → [eax+SHADOW]（esi = 存档指针）"
    },
    "order_414401": {
      "addr": "0x414401",
      "code": "8b1495<codecave:th18_card_order>",
      "expected": "8b149500364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "order_4145f8": {
      "addr": "0x4145f8",
      "code": "8b0c8d<codecave:th18_card_order>",
      "expected": "8b0c8d00364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "order_414639": {
      "addr": "0x414639",
      "code": "ff3485<codecave:th18_card_order>",
      "expected": "ff348500364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "order_41499f": {
      "addr": "0x41499f",
      "code": "b8<codecave:th18_card_order>",
      "expected": "b800364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "order_414b54": {
      "addr": "0x414b54",
      "code": "3d<codecave:th18_card_order+3fc>",
      "expected": "3de4364b00",
      "title": "显示顺序表 → codecave（尾界 = 255 项）"
    },
    "order_415681": {
      "addr": "0x415681",
      "code": "8b0c85<codecave:th18_card_order>",
      "expected": "8b0c8500364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "order_4156b6": {
      "addr": "0x4156b6",
      "code": "ff3485<codecave:th18_card_order>",
      "expected": "ff348500364b00",
      "title": "显示顺序表 → codecave（引用）"
    },
    "menu_413817": {
      "addr": "0x413817",
      "code": "68f8170000",
      "expected": "68fc130000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_413831": {
      "addr": "0x413831",
      "code": "68f8170000",
      "expected": "68fc130000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_413abb": {
      "addr": "0x413abb",
      "code": "68f8170000",
      "expected": "68fc130000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_41495c": {
      "addr": "0x41495c",
      "code": "bfff000000",
      "expected": "bf38000000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_4145d2": {
      "addr": "0x4145d2",
      "code": "8986100c0000",
      "expected": "898618fbffff",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_414b3f": {
      "addr": "0x414b3f",
      "code": "89b010080000",
      "expected": "89b018f7ffff",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_414b81": {
      "addr": "0x414b81",
      "code": "8d87fc130000",
      "expected": "8d8704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_414beb": {
      "addr": "0x414beb",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_414e9f": {
      "addr": "0x414e9f",
      "code": "8b8c8ffc130000",
      "expected": "8b8c8f04030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_414eba": {
      "addr": "0x414eba",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_415049": {
      "addr": "0x415049",
      "code": "8d87fc130000",
      "expected": "8d8704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_415115": {
      "addr": "0x415115",
      "code": "8a8c8ffc130000",
      "expected": "8a8c8f04030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_415129": {
      "addr": "0x415129",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_41514a": {
      "addr": "0x41514a",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_4151ef": {
      "addr": "0x4151ef",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_41520c": {
      "addr": "0x41520c",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_4152b4": {
      "addr": "0x4152b4",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_4152d5": {
      "addr": "0x4152d5",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_415868": {
      "addr": "0x415868",
      "code": "ffb487fc130000",
      "expected": "ffb48704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    },
    "menu_415e83": {
      "addr": "0x415e83",
      "code": "8d87fc130000",
      "expected": "8d8704030000",
      "title": "zAbilityMenu 扩容 / __card_ids → +0x13fc"
    }
  },
  "breakpoints": {
    "ce_gate": {
      "addr": "0x4637d0",
      "cavesize": 5,
      "expected": "558bec6aff",
      "title": "自检门：ScoreFile__load 入口 → BP_ce_gate（填表 + 回读验证 + 写日志）"
    },
    "ce_unlock_write": {
      "addr": "0x418e04",
      "cavesize": 8,
      "expected": "c6843e88f5050001",
      "title": "mark_obtained 的写 → BP_ce_unlock_write：影子[id]=1；id<57 放行原指令写零售存档，否则写 side-car"
    },
    "ce_save_loaded": {
      "addr": "0x46398a",
      "cavesize": 6,
      "expected": "8db3b8f40500",
      "title": "ScoreFile__load 尾段 → BP_ce_save_loaded：影子[0..56] ← 零售存档，[57..] ← side-car"
    },
    "ce_unlock_all": {
      "addr": "0x4648fe",
      "cavesize": 6,
      "expected": "8d8388f50500",
      "title": "ScoreFile__unlock_all → BP_ce_unlock_all：影子[0..55]=1（镜像紧接着的 memset）"
    },
    "ce_text_name": {
      "addr": "0x416694",
      "cavesize": 6,
      "expected": "69cbc0010000",
      "title": "文案重定向 → BP_ce_text_name：id<57 照算 id*0x1c0，否则指向 DLL 的扩展文案缓冲（FUN_00416540 卡名：imul ecx, ebx, 0x1c0）"
    },
    "ce_text_desc": {
      "addr": "0x416779",
      "cavesize": 7,
      "expected": "69450cc0010000",
      "title": "文案重定向 → BP_ce_text_desc：id<57 照算 id*0x1c0，否则指向 DLL 的扩展文案缓冲（FUN_00416540 说明 6 行：imul eax, [ebp+0xc], 0x1c0）"
    },
    "ce_text_notify": {
      "addr": "0x41926a",
      "cavesize": 6,
      "expected": "69c3c0010000",
      "title": "文案重定向 → BP_ce_text_notify：id<57 照算 id*0x1c0，否则指向 DLL 的扩展文案缓冲（获得通知：imul eax, ebx, 0x1c0）"
    }
  }
}
