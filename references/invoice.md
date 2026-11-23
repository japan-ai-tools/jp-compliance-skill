# 適格請求書 (qualified invoice) - consumption tax

Source: National Tax Agency pamphlet https://www.nta.go.jp/publication/pamph/shohi/shohizei_11.pdf

## Six required items (消費税法 第57条の4)
1. Issuer name and registration number (T + 13 digits)
2. Transaction date
3. Description of goods/services, with reduced-rate (8%) items marked (e.g. ※ and a legend)
4. Total per tax rate (tax-inclusive or tax-exclusive) and the rate
5. Consumption tax per tax rate
6. Buyer name - may be omitted on a simplified qualified invoice (適格簡易請求書) issued by retailers, restaurants,
   taxis and similar businesses; `jpcheck invoice` checks the full invoice only.

## Rounding
Once per invoice **per tax rate** (「一の適格請求書につき、税率ごとに1回」). Rounding each line and adding up is
not allowed. The method (floor / half-up / ceil) is free. jpcheck reports which method the stated tax matches, or that
none does.

## Registration numbers
- Format: `T` + 13 digits. For corporations the 13 digits are the corporate number, whose first digit is a check
  digit (jpcheck verifies it). Sole proprietors get a 13-digit number assigned by the NTA; the check-digit test
  applies to corporate numbers only, so a mismatch is a warning, not an error.
- Whether a number is registered today: NTA public site, its daily diff download, or its Web-API (application ID).
  The search screen must not be scraped (site terms).

## JSON shape for `jpcheck invoice`
```json
{"issuer": {"name": "株式会社サンプル", "registration_number": "T7123456789012"}, "date": "2026-10-28",
 "buyer": {"name": "株式会社テスト"}, "price_basis": "exclusive",
 "items": [{"description": "コピー用紙", "amount": 1999, "rate": 10},
           {"description": "※ お茶", "amount": 1234, "rate": 8, "reduced": true}],
 "totals": [{"rate": 10, "amount": 1999, "tax": 199}, {"rate": 8, "amount": 1234, "tax": 98}]}
```
