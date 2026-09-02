{
  "codecaves": {
    "th18_card_table": {
      "size": "0xbc8",
      "access": "RW",
      "title": "zTableCardData[] 搬迁目标（58 行 × 0x34）"
    },
    "th18_card_table_patch_init": {
      "code": "fc60bf<codecave:th18_card_table>be<Rxc53c0>b9f2020000f3a561c3",
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "81fe<codecave:th18_card_table+bc8>",
      "expected": "81fe885f4c00",
      "title": "end | cmp esi, K | +0xbc8"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
      "code": "3d<codecave:th18_card_table+bcc>",
      "expected": "3d8c5f4c00",
      "title": "end | cmp eax, K | +0xbcc"
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
    }
  }
}
