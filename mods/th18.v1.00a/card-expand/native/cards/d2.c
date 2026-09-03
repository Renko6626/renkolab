/* 方片 2 —— 商店一次性购买：买下后金钱翻倍（先扣购买价，再翻倍）。本身不进卡组（同强欲之壶）。
 *
 * 成交顺序（05-shop-and-money.md「成交」0x4185c7）：allocate_new_card(mode 2) → ctor → …→ price = 价格表[tier]
 * → if (price <= MONEY) MONEY -= price; else 用火力补差价并 MONEY = 0。
 * ctor 跑在扣款之前，所以这里写 MONEY = 2·M − price：游戏随后扣掉 price，落地正好是 2·(M − price)。
 * M < price（走火力补差价）时游戏会把 MONEY 清零，0 翻倍还是 0，这里不动。
 * 多出来的钱记进 MONEY_TOTAL（只记收入的统计量，与金钱道具入账一致）。 */
#include "sdk.h"

static int ctor(ce_card_t *c)
{
    uint8_t *e = ce_table_entry(ce_card_id(c));            /* ctor 里 card+0x4c 还没写，走注册表 */
    int32_t price = ce_price_for_tier(ce_entry_tier(e));
    int32_t m = CE_MONEY();
    if (m >= price) {
        int32_t gain = m - price;                          /* 扣完价后剩下的那份，翻倍就是再加这么多 */
        CE_MONEY() = m + gain;                             /* = 2·M − price */
        CE_MONEY_TOTAL() += gain;
        ce_log("d2: money %d -> after purchase %d (price %d, +%d)", m, 2 * gain, price, gain);
    } else {
        ce_log("d2: money %d < price %d, power makes up the rest -> 0, nothing to double", m, price);
    }
    return 1;                                              /* 即时卡：当场销毁，不进卡组 */
}

CE_CARD(65, .ctor = ctor);
