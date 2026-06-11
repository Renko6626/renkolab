; =============================================================================
; tick_tracking_burst_starter.asm  —  cave 实体(NASM,32-bit,position-independent)
; 对应 tick_tracking_burst_starter.c。所有外部调用走 "mov eax,ABS / call eax"(绝对地址,
; 与 cave 落地址无关),数据引用全绝对 → 可直接放进 thcrap codecave,无需 rel32 重定位。
; 调用约定:__fastcall,ECX=self(子弹槽)。返回值 EAX。
; 汇编:nasm -f bin tick_tracking_burst_starter.asm -o cave.bin ; 再 hexdump 贴进 codecave。
; ★ 手写汇编,务必汇编后比对 + 游戏内验证(见 thcrap_patch.md §5)。仅 TH16 v1.00a。
; =============================================================================
BITS 32
%define BURST_FRAMES 24

tick_tracking_burst_starter:
    push    ebp
    mov     ebp, esp
    sub     esp, 0x20
    push    esi
    push    edi
    mov     esi, ecx                  ; esi = self

    ; (0) 爆发寿命:slot+0x10 > BURST_FRAMES → 了结
    cmp     dword [esi+0x10], BURST_FRAMES
    jle     .alive
    mov     eax, [esi+0xb0]           ; 伤害源 link
    test    eax, eax
    jz      .no_src
    imul    eax, eax, 0x94
    add     eax, [0x4a6ef8]           ; PLAYER_PTR
    and     dword [eax+0xd080], 0xfffffffe   ; 伤害源 active bit0 清
.no_src:
    push    dword [esi+0x08]          ; anm id
    mov     eax, 0x46f1c0
    call    eax                       ; anm_unload —— STDCALL(RET 4),callee 清栈,勿 add esp
    mov     dword [esi+0x08], 0
    mov     dword [esi+0x8c], 0       ; 释放槽
    mov     eax, 1                    ; 返回非 0 → tick_bullets 跳过默认运动
    jmp     .ret

.alive:
    mov     eax, [0x4a6dc0]           ; ENEMY_MANAGER
    test    eax, eax
    jnz     .have_mgr
    mov     dword [esi+0x90], 0
    jmp     .move
.have_mgr:
    cmp     dword [esi+0x90], 0
    jnz     .check
    ; --- 锁最近敌人:find_nearest_enemy(out, &refpos), XMM3=半径256 ---
    mov     eax, [esi+0x48]
    mov     [ebp-0x0c], eax           ; refpos.x
    mov     eax, [esi+0x4c]
    mov     [ebp-0x08], eax           ; refpos.y
    mov     dword [ebp-0x04], 0       ; out = 0
    movss   xmm3, [0x494680]          ; 半径 = 256.0
    lea     eax, [ebp-0x0c]
    push    eax                       ; arg2 = &refpos  (cdecl 右→左)
    lea     eax, [ebp-0x04]
    push    eax                       ; arg1 = &out
    mov     eax, 0x425240
    call    eax                       ; find_nearest_enemy —— STDCALL(RET 8),callee 清栈,勿 add esp
    mov     eax, [ebp-0x04]
    mov     [esi+0x90], eax           ; 句柄存目标槽
.check:
    mov     eax, [esi+0x90]
    test    eax, eax
    jz      .move
    push    eax
    mov     eax, 0x41a980
    call    eax                       ; is_enemy_alive —— STDCALL(RET 4),callee 清栈,勿 add esp
    test    eax, eax
    jnz     .alive_ok
    mov     dword [esi+0x90], 0       ; 死了 → 清目标
    jmp     .move
.alive_ok:
    lea     ecx, [esi+0x90]           ; ECX = &句柄
    mov     eax, 0x41b540
    call    eax                       ; handle_to_enemy → EAX = 敌 ptr
    test    dword [eax+0x526c], 0xc000021
    jnz     .move                     ; 不可锁 → 不瞄
    ; --- 硬瞄:angle(+0x64) = atan2(dy, dx) ---
    movss   xmm0, [eax+0x1254]        ; enemy.y
    subss   xmm0, [esi+0x4c]          ; dy
    cvtps2pd xmm0, xmm0
    movsd   [ebp-0x14], xmm0
    fld     qword [ebp-0x14]          ; ST0 = dy
    movss   xmm0, [eax+0x1250]        ; enemy.x
    subss   xmm0, [esi+0x48]          ; dx
    cvtps2pd xmm0, xmm0
    movsd   [ebp-0x14], xmm0
    fld     qword [ebp-0x14]          ; ST0 = dx, ST1 = dy
    mov     eax, 0x487aaa
    call    eax                       ; crt_atan2 → ST0 = atan2(dy,dx),消耗 2 参
    fstp    dword [esi+0x64]          ; slot 角 = 结果
.move:
    xor     eax, eax                  ; 返回 0 → 引擎按 slot+0x60 速度 / +0x64 角自动飞
.ret:
    pop     edi
    pop     esi
    mov     esp, ebp
    pop     ebp
    ret                               ; __fastcall 无栈参 → 普通 ret
