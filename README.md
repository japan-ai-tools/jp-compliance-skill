# jp-compliance — an Agent Skill for selling in Japan

Check Japanese ad copy, online-shop legal notices, checkout screens and invoices against Japanese law **before they
ship**. Deterministic script + verification workflow, machine-readable findings with line numbers, the law, and the
official source. Works with Claude Code, Codex CLI, Gemini CLI, Cursor and any agent that reads `SKILL.md`.

```
$ python scripts/jpcheck.py ad examples/ad_bad.txt
```
```json
{"rule": "KEIHYO_STEALTH_NO_DISCLOSURE", "severity": "error",
 "message_en": "Promotional content (affiliate link or sponsored wording) with no ad disclosure anywhere...",
 "law": "景品表示法 第5条第3号・ステルスマーケティング告示(2023-10-01 施行)",
 "source": "https://www.caa.go.jp/policies/policy/representation/fair_labeling/stealth_marketing/",
 "evidence": {"line": 7, "text": "購入はこちら → https://px.a8.net/svt/ejp?a8mat=3T9A2B+1C2D3E+0K34+5YJRM"}, "needs_review": true}
```

## What it checks

| command | law | finds |
|---|---|---|
| `ad` | 景品表示法 (Premiums and Representations Act) | stealth marketing (affiliate/sponsored text without 【PR】), #1/ranking claims without a survey note, absolute claims (絶対・必ず・100%), double pricing (通常価格・%OFF), scarcity wording, health claims (flagged as out of scope) |
| `tokusho` | 特定商取引法 (Specified Commercial Transactions Act) | missing items in 「特定商取引法に基づく表記」: seller, address, phone, price incl. shipping, other costs, unfilled template blanks, payment timing **and** method, delivery, returns; plus representative (`--corporate`), system requirements (`--digital`), recurring terms (`--subscription`) |
| `tokusho --final-screen` | 同 第12条の6 | the items a checkout's final confirmation screen must show (quantity, price, payment timing/method, delivery, application period, cancellation; plus count and later amounts for subscriptions) and wording that hides a paid order |
| `invoice` | 消費税法 (qualified invoice) | six required items, tax rounded once per rate, reduced-rate marks |
| `regno` | 同 | registration number format `T`+13 digits and the corporate check digit |

## Why it is built this way

- **Script first, judgement second.** Regexes and checklists never get tired and never skip a line; the agent then
  confirms each finding in context and marks it `confirmed`, `false_positive` or `needs_owner` (see `SKILL.md`).
- **Evidence on every finding.** Line number and the line itself, the article of law, and an official URL.
- **Honest scope.** Every run returns `not_checked`. The skill forbids the agent from saying "legal" or "compliant",
  and from inventing facts (addresses, surveys, prices) to make a check pass.
- **No dependencies, no network.** Python 3.9+ standard library. UTF-8 and Shift_JIS input. Full-width text is
  normalized (full-width letters and digits = half-width).
- **Tested and reviewed.** `python -m unittest discover -s tests` - 24 tests: good and bad examples for every check,
  regressions from an independent review (false alarms on everyday text, subscription traps, stealth-ad loopholes),
  CLI exit codes, Shift_JIS.

## Install

Copy this folder into your agent's skills directory, for example `~/.claude/skills/jp-compliance/`
(Claude Code), or point your agent at `SKILL.md`. The script also runs on its own:

```bash
python scripts/jpcheck.py tokusho legal.md --corporate --digital --subscription
python scripts/jpcheck.py tokusho checkout.txt --final-screen --subscription
python scripts/jpcheck.py invoice invoice.json --role receive
python scripts/jpcheck.py regno T7123456789012
```
Exit code: 0 = no errors, 1 = errors found, 2 = bad input.

## Limits

Automated keyword and pattern checks, not legal advice. **Zero findings does not mean the text is legal** - it means
none of these patterns matched. It does not check images, whether a survey or price history is real,
industry codes (公正競争規約), or the Pharmaceutical Act in detail. Whether an invoice number is registered today must be
checked with the National Tax Agency (its search screen must not be scraped).

---

# jp-compliance — 日本で売るためのエージェント用スキル

広告の文章・「特定商取引法に基づく表記」・申込みの最終確認画面・請求書を、**出す前に**日本の法律の決まりで確かめます。
スクリプトが「怪しい所」を行番号・条文・公式の出典つきで出し、AI エージェントが1件ずつ本文と照らして
「本当の問題/誤検知/持ち主に確かめる」に分け、直して、もう一度確かめます。

- 景品表示法: ステマ(【PR】なしのアフィリエイト・提供)、根拠のない「1位・一番」、「絶対」「必ず」、二重価格、先着・期限
- 特定商取引法: 表記に必要な事項の抜け(住所・電話・支払の時期と方法・引渡し時期・返品・動作環境・定期の条件など)、最終確認画面の6事項
- インボイス: 記載事項6つ、税率ごとに1回の端数処理、登録番号の形と検査用数字

「合法です」とは言いません。確かめた範囲と確かめていない範囲を必ず書きます。法律の助言ではありません。
大事な判断は弁護士・税理士・消費生活センターなどにご相談ください。

License: MIT. Made by NEXUS tools. Independent project; not affiliated with Anthropic, OpenAI, Google, Cursor, the Consumer Affairs Agency or the National Tax Agency.
独立したプロジェクトで、各社・消費者庁・国税庁とは関係ありません。
