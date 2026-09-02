/* cards.c —— 新卡注册表：哪些 id ≥ 57 是「真的有」的卡。
 *
 * 图鉴条目数、显示顺序表的追加段、（以后）商店池与卡表行，都以这份注册表为准——
 * 255 行 codecave 里其余的行是 NULL 副本，**不算卡**。
 *
 * 现在是编译进 DLL 的一张表（步骤 2 会改成从文件读，仓库里只放新卡自己的数据）。
 */
#include "card_expand.h"

static const uint32_t s_new_ids[] = { 58 };

unsigned ce_new_card_count(void)
{
    return sizeof s_new_ids / sizeof s_new_ids[0];
}

uint32_t ce_new_card_id(unsigned i)
{
    return s_new_ids[i];
}
