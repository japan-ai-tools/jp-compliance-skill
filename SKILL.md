---
name: jp-compliance
description: Check Japanese business text against Japanese law before it ships - ad and landing-page copy (Premiums and Representations Act, stealth-marketing rule, #1/ranking claims, double pricing), online-shop legal notices and order-confirmation screens (Specified Commercial Transactions Act), and qualified invoices and invoice registration numbers (consumption tax). Use when writing, reviewing or publishing anything sold or advertised to people in Japan, or when the user mentions 景品表示法, ステマ, 特商法, 特定商取引法の表記, 最終確認画面, インボイス, 適格請求書 or 登録番号.
---

# jp-compliance

Deterministic checks first, your judgement second, evidence always.
The script finds candidate problems with a line number and the law behind them. You confirm each one against the
text, fix what is real, and report what you did not check. You never declare anything "legal" or "compliant".

## When to use

- Writing or reviewing Japanese ad copy, LPs, SNS posts, affiliate articles, app-store text → `ad`
- Writing or reviewing an online shop's 「特定商取引法に基づく表記」 page → `tokusho`
- Building a checkout / subscription confirmation screen → `tokusho --final-screen`
- Generating or checking invoices for Japanese customers → `invoice`, `regno`

## Workflow

1. **Pick the check and flags.** For `tokusho`, decide from the business itself (ask if unknown):
   `--corporate` (seller is a company), `--digital` (software / downloads / online service), `--subscription` (recurring).
2. **Run the script** (Python 3.9+, standard library only, no network):
   ```bash
   python scripts/jpcheck.py ad page.md
   python scripts/jpcheck.py tokusho legal.md --corporate --digital --subscription
   python scripts/jpcheck.py tokusho checkout.txt --final-screen --subscription
   python scripts/jpcheck.py invoice invoice.json --role issue
   python scripts/jpcheck.py regno T7123456789012
   ```
   Input can be a file or `-` (stdin). UTF-8 or Shift_JIS. Exit 0 = no error-level findings, 1 = errors, 2 = bad input.
   Pass the text the customer actually sees (rendered text, not HTML source, when you can).
3. **Verify every finding yourself.** Open the evidence line. For each finding decide one of:
   - `confirmed` - the problem is real in context
   - `false_positive` - the pattern matched but the meaning is different (say why in one line)
   - `needs_owner` - only the business can answer (e.g. "is this survey real?", "did we sell at this price for 8 weeks?")
   Do not skip this step. The script is a keyword/pattern matcher: it over-reports on purpose, and it can also
   miss things (a word being present is not the same as the item being clearly shown). Zero findings is not "legal".
4. **Fix what is confirmed** when you are allowed to edit. Rules for rewrites are in `references/`. Keep the meaning,
   remove the claim you cannot prove, add the missing item. Never invent facts (addresses, phone numbers, survey names,
   prices) to make a check pass - leave a clearly marked placeholder like 【要記入: 電話番号】 and list it.
5. **Re-run the script** on the fixed text. Repeat until no confirmed errors remain.
6. **Report** in the user's language with this shape:

   | id | rule | severity | status | evidence (line) | fix |
   |---|---|---|---|---|---|

   Then: what was changed, placeholders the owner must fill, the `not_checked` list from the script output,
   and the sources (each finding has `law` and `source`). End with: this is an automated check, not legal advice;
   for high-stakes cases ask a lawyer (弁護士), tax accountant (税理士) or the regulator's consultation desk.

## Hard rules

- Never write 「合法です」「問題ありません」「compliant」. Say what was checked and what was found.
- Never remove an ad disclosure (【PR】, 広告) to make copy look cleaner.
- Never add a "regular price" (通常価格) unless the owner confirms the product really sold at it recently.
- Never present a ranking (#1) claim without the survey details next to it; prefer deleting it.
- Health/beauty effect claims are outside this skill (薬機法). Flag them and send to a specialist.
- Registration numbers: the script checks format and check digit only. Whether a number is registered *today*
  must be checked on the National Tax Agency site (国税庁 適格請求書発行事業者公表サイト). Do not scrape its search
  screen - its terms forbid programmatic access to the search function; use its download data or Web-API.

## References

- `references/ad.md` - 景品表示法: stealth marketing, #1/ranking claims, double pricing, absolute claims, with rewrite examples
- `references/tokusho.md` - 特定商取引法: required items for mail-order ads and the final confirmation screen
- `references/invoice.md` - 適格請求書: six required items, rounding once per rate, registration numbers
