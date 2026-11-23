# 特定商取引法 (Act on Specified Commercial Transactions) - online selling

Sources: Consumer Affairs Agency, 特定商取引法ガイド 通信販売 https://www.no-trouble.caa.go.jp/what/mailorder/ ;
Act and Ordinance (current, after the 2023 amendment of the Ordinance) https://www.japaneselawtranslation.go.jp/en/laws/view/4865/ja

## Mail-order ad / 「特定商取引法に基づく表記」 (法 第11条・施行規則 第23条)
| item | ja | flag |
|---|---|---|
| price, **including shipping** | 販売価格(送料を含む) | always (法11条1号) |
| payment timing **and** method | 支払の時期及び方法 | always (2号) |
| delivery / service start timing | 引渡時期・提供時期 | always (3号) |
| application period (if any) | 申込みの期間の定め | if limited (4号) |
| cancellation / returns (incl. return policy) | 申込みの撤回・解除(返品特約) | always (5号) |
| seller name, address, phone | 販売業者の氏名・名称、住所、電話番号 | always (施行規則23条) |
| representative or responsible person | 代表者又は責任者の氏名 | company (`--corporate`) |
| costs besides price and shipping | 送料以外の負担金 | if any |
| system requirements | 利用に必要なコンピュータの仕様・性能 | software/data (`--digital`) |
| recurring-contract terms | 2回以上継続する契約の条件(金額・期間) | subscriptions (`--subscription`) |
| other sales conditions, email address for email ads | その他の販売条件・メールアドレス | if any |

- **Omission on request (法 第11条ただし書)**: any seller - not only individuals - may leave some items out of the ad
  if the ad says the full information will be sent in writing or electronically **without delay on request**, and they
  really do so. jpcheck lowers the identity items to `info` when such a sentence exists.
- Exaggerated ads are banned separately (法 第12条; the regulator can demand evidence, 第12条の2).
- "No returns" is allowed for mail order only when stated clearly in the ad (返品特約, 第15条の3). Defects are a
  different matter (契約不適合責任).

## Final confirmation screen (法 第12条の6) - the last screen before the order button
On that screen show: **分量** (quantity; for subscriptions also the number of deliveries / contract period),
**price** (for subscriptions the amount from the 2nd time or the total), **payment timing and method**, **delivery
timing**, **application period** if the offer is limited, and **cancellation terms**. Do not make the click look
like it is not a paid order, and do not hide or mislead on these items (第12条の6第2項).

jpcheck looks for these as keywords and simple patterns (amounts, dates). It cannot tell whether the screen design
is clear, whether the amounts are correct, or whether wording is hidden in small print - an agent or person must look.
