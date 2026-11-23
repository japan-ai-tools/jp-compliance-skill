#!/usr/bin/env python3
"""jpcheck — deterministic checks for Japanese business rules, for coding agents and people.

    python jpcheck.py ad       FILE|-            # ad / landing-page copy: Premiums and Representations Act (景品表示法)
    python jpcheck.py tokusho  FILE|- [--digital] [--subscription] [--corporate] [--final-screen]
                                                 # online-shop legal notice / order-confirmation page (特定商取引法)
    python jpcheck.py invoice  FILE|- [--role issue|receive]   # qualified invoice JSON (適格請求書)
    python jpcheck.py regno    T1234567890123 ...              # invoice registration number format + check digit

Output: one JSON object on stdout:
    {"tool": "jpcheck", "version", "check", "summary": {"error", "warning", "info"},
     "findings": [{"id", "rule", "severity", "message_en", "message_ja", "fix_en", "fix_ja",
                   "law", "source", "evidence": {"line", "text"} | null, "needs_review": true}],
     "not_checked": [...]}
Exit code: 0 no errors, 1 at least one error-level finding, 2 bad input.

Every finding is a pattern match or a missing-item check, not a legal judgement. `needs_review` is always true:
an agent or a person must look at the evidence line and decide. Python standard library only. No network.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jp_invoice_rules as inv_rules  # noqa: E402

VERSION = "0.1.0"

SRC_KEIHYO = "https://www.caa.go.jp/policies/policy/representation/fair_labeling/"
SRC_STEALTH = "https://www.caa.go.jp/policies/policy/representation/fair_labeling/stealth_marketing/"
SRC_DOUBLE = "https://www.caa.go.jp/policies/policy/representation/fair_labeling/representation_regulation/double_price"
SRC_NO1 = "https://www.caa.go.jp/policies/policy/representation/fair_labeling/survey"
SRC_TOKUSHO = "https://www.no-trouble.caa.go.jp/what/mailorder/"
SRC_TOKUSHO_RULES = "https://www.japaneselawtranslation.go.jp/en/laws/view/4865/ja"
SRC_INVOICE = "https://www.nta.go.jp/publication/pamph/shohi/shohizei_11.pdf"


def _n(s):
    """NFKC (full-width → half-width), keep line breaks."""
    return unicodedata.normalize("NFKC", s)


class Report:
    def __init__(self, check, text=None):
        self.check, self.findings, self.not_checked = check, [], []
        self.lines = _n(text).splitlines() if text is not None else []

    def where(self, pos_or_regex):
        """Evidence for a regex match position in the normalized text, or None."""
        if pos_or_regex is None:
            return None
        joined, start = "\n".join(self.lines), pos_or_regex
        line_no = joined.count("\n", 0, start) + 1
        line = self.lines[line_no - 1] if line_no - 1 < len(self.lines) else ""
        return {"line": line_no, "text": line.strip()[:200]}

    def add(self, rule, severity, en, ja, fix_en, fix_ja, law, source, pos=None):
        self.findings.append({
            "id": f"{self.check}-{len(self.findings) + 1:03d}", "rule": rule, "severity": severity,
            "message_en": en, "message_ja": ja, "fix_en": fix_en, "fix_ja": fix_ja,
            "law": law, "source": source, "evidence": self.where(pos), "needs_review": True})

    def out(self):
        s = {k: sum(1 for f in self.findings if f["severity"] == k) for k in ("error", "warning", "info")}
        return {"tool": "jpcheck", "version": VERSION, "check": self.check, "summary": s,
                "findings": self.findings, "not_checked": self.not_checked}


BLANK_WORD = r"(要記入|未記入|記入|入力してください|未定|要確認|確認中|準備中|TBD|TODO|ここに|あとで|後で|\(仮\)|(仮))"
PLACEHOLDER = re.compile(r"(【[^】\n]{0,30}" + BLANK_WORD + r"[^】\n]{0,30}】|【\s*】|" + BLANK_WORD + r"|(?i:\bTBD\b|\bTODO\b|lorem ipsum)|"
                         r"○○|〇〇|XXX+)")
# 【氏名】 alone as the value of a row ("| 所在地 | 【住所】 |", "所在地: 【住所】") is a blank; 【所在地】 as a heading is not
VALUE_BLANK = re.compile(r"(?m)(\||:|：)\s*(【[^】\n]{1,20}】)\s*(\||\(|（|$)")


def _placeholders(r, t, law, source):
    """Unfilled blanks: a check must never pass on a template."""
    urls = [u.span() for u in re.finditer(r"https?://\S+", t)]
    seen = set()
    hits = [(m.start(), m.group(0)) for m in PLACEHOLDER.finditer(t)] + \
           [(m.start(2), m.group(2)) for m in VALUE_BLANK.finditer(t)]
    for pos, word in sorted(hits):
        if pos in seen or any(a <= pos < b for a, b in urls):     # ids inside links are not blanks
            continue
        seen.add(pos)
        if re.fullmatch(r"【(PR|広告|プロモーション)】", word):
            continue
        r.add("UNFILLED_PLACEHOLDER", "error", f"Unfilled placeholder '{word}'. The page is still a template.",
              f"「{word}」が埋まっていません。まだひな形のままです。", "Fill in the real value before publishing.",
              "公開する前に本当の値を入れる。", law, source, pos)


# ---------------------------------------------------------------- ad copy (景品表示法)
AFFILIATE = re.compile(r"(?i)(amazon\.co\.jp/[^\s]*[?&]tag=|amzn\.to/|a8\.net|px\.a8\.net|af\.moshimo\.com|"
                       r"hb\.afl\.rakuten\.co\.jp|a\.r10\.to|valuecommerce\.com|ck\.jp\.ap\.valuecommerce|accesstrade\.net|"
                       r"felmat\.net|t\.afi-b\.com|link-a\.net|rakuten\.co\.jp/[^\s]*scid=af|shopping\.yahoo\.co\.jp/[^\s]*sc_e=af)")
SPONSORED_HINT = re.compile(r"(提供を受け|ご提供いただ|提供いただ|いただきました|頂きました|頂戴しました|ご恵贈|献本|案件|依頼を受け|"
                            r"サンプルをいただ|招待され|タイアップ|PR案件)")
PR_MARK = re.compile(r"(?i)(広告|(?<![A-Za-z自己])PR(?![A-Za-z])|プロモーション|アフィリエイト|タイアップ|スポンサー|sponsored|#ad\b|提供:)")
PR_NEGATED = re.compile(r"(広告|PR|プロモーション|案件)(では|じゃ)(ありません|ない)")
COMMERCE = re.compile(r"(円|¥|￥|購入|販売|注文|申し?込|カート|今すぐ|お得|https?://|価格|料金|プラン|割引|セール)")
NO1 = re.compile(r"(?i)(No\.?\s?1|ナンバー\s?(ワン|1)|第\s?1\s?位|(?<![\d学年組クラス])1位|日本一|世界一|業界(初|No|一|トップ)|"
                 r"トップクラス|ランキング(上位|1位)|世界初|日本初|国内初|史上初|最安(値)?)")
PRICE_CLAIM = re.compile(r"最安")
BASIS = re.compile(r"(出典|調査|調べ|対象[:：]|期間[:：]|根拠|\d{4}\s?年[^\n]{0,20}(月|調査|時点))")
ABSOLUTE = re.compile(r"(絶対(に)?(?!パス|値)|必ず(痩|治|効|儲|稼|売|成功|上が)|100\s?%(効|安全|成功|治|満足|保証|確実)|"
                      r"完全(に)?(除去|無害|安全|治)|確実に(儲|稼|痩|治)|副作用(なし|ゼロ|が?ない))")
DOUBLE = re.compile(r"(通常価格|当社通常|定価|元値|参考価格|メーカー希望小売価格|希望小売価格|市場価格|"
                    r"(?<!\d)\d{1,3}\s?%\s?(OFF|off|オフ|引き)|半額)")
SCARCITY = re.compile(r"(先着\s?\d|残り\s?(わずか|\d)|在庫限り|期間限定|本日限り|今だけ|今なら|限定\s?\d+\s?(名|個|本|セット))")
DISCLAIMER = re.compile(r"(個人の感想|効果には個人差|効果・効能を(保証|示す)ものでは)")
HEALTH = re.compile(r"(治る|治す|治療|改善する|予防する|痩せる|やせる|飲むだけで|塗るだけで|貼るだけで|たった\s?\d+\s?日で|-\s?\d+\s?kg|マイナス\s?\d+\s?kg|アンチエイジング|若返|免疫(力)?(を|が)?(上げ|高め|アップ)|"
                    r"血圧(を|が)?下|血糖値(を|が)?下|がんに効|癌に効|シミ.{0,6}(消え|消す|なくな|改善)|シワ.{0,6}(消え|消す|なくな)|発毛|育毛効果)")


def check_ad(text):
    r = Report("ad", text)
    t = "\n".join(r.lines)
    head = t[:300]   # "near the top": the title and first lines a reader sees

    _placeholders(r, t, "景品表示法 第5条", SRC_KEIHYO)
    aff = AFFILIATE.search(t)
    spon = SPONSORED_HINT.search(t)
    clean = PR_NEGATED.sub("", t)          # 「広告ではありません」 is not a disclosure
    mark = PR_MARK.search(clean)
    head_mark = PR_MARK.search(PR_NEGATED.sub("", head))
    if aff or spon:
        trigger = aff or spon
        if PR_NEGATED.search(t):
            r.add("KEIHYO_STEALTH_DENIES_AD", "error",
                  "The text says it is not an ad, but contains an affiliate link or sponsored wording.",
                  "「広告ではありません」などと書かれていますが、アフィリエイトのリンクや提供を受けた旨の言葉があります。",
                  "Remove the denial and add a clear 【PR】 / 広告 marker at the top.",
                  "否定の言葉を消し、冒頭に【PR】・広告などの印を入れる。",
                  "景品表示法 第5条第3号・ステルスマーケティング告示(2023-10-01 施行)", SRC_STEALTH, PR_NEGATED.search(t).start())
        if not mark:
            r.add("KEIHYO_STEALTH_NO_DISCLOSURE", "error",
                  "Promotional content (affiliate link or sponsored wording) with no ad disclosure. If the advertiser "
                  "was involved in this content, an ad that consumers cannot recognise as an ad may violate the "
                  "Premiums and Representations Act (stealth-marketing notice, since 2023-10-01).",
                  "アフィリエイトのリンク、または提供を受けた旨の言葉があるのに、広告である印がありません。"
                  "広告主が関わった表示なら、広告と分からない広告(ステマ)として景品表示法違反のおそれがあります(2023年10月1日から)。",
                  "Put a clear marker such as 【PR】 / 広告 / プロモーション at the beginning, where readers see it first.",
                  "冒頭の目に入る所に【PR】・広告・プロモーションなどの印を入れる。",
                  "景品表示法 第5条第3号・ステルスマーケティング告示(2023-10-01 施行)", SRC_STEALTH, trigger.start())
        elif not head_mark:
            r.add("KEIHYO_STEALTH_DISCLOSURE_NOT_PROMINENT", "warning",
                  "An ad marker exists but not near the top. A marker only at the end or in small print may not be "
                  "'clear' to readers.",
                  "広告の印はありますが、冒頭にありません。末尾や小さな字だけでは「明瞭」と言えないおそれがあります。",
                  "Move the marker to the title or first lines.", "印をタイトルか最初の数行に移す。",
                  "ステルスマーケティング告示・運用基準", SRC_STEALTH, mark.start())

    commerce = bool(COMMERCE.search(t))
    for m in NO1.finditer(t):
        near = t[max(0, m.start() - 150): m.end() + 250]
        if not BASIS.search(near):
            r.add("KEIHYO_NO1_NO_BASIS", "error" if commerce else "warning",
                  f"Superlative/ranking claim '{m.group(0)}' with no basis (survey, period, target) nearby. "
                  "The CAA 2024 survey report treats No.1 claims without an objective, fair survey as misleading.",
                  f"「{m.group(0)}」という順位・一番の言い方の近くに、根拠(調査の名前・期間・対象)がありません。"
                  "消費者庁は2024年の報告書で、客観的で公正な調査がない No.1 表示は不当表示のおそれがあると示しています。",
                  "Delete it, or add the survey name, period, comparison target and who surveyed, right next to it.",
                  "消すか、すぐ近くに調査の名前・期間・比べた対象・調べた人を書く。",
                  "景品表示法 第5条第2号(有利誤認)" if PRICE_CLAIM.match(m.group(0)) else
                  "景品表示法 第5条第1号(優良誤認)・第7条第2項(合理的な根拠)", SRC_NO1, m.start())
        else:
            r.add("KEIHYO_NO1_CHECK_BASIS", "warning",
                  f"'{m.group(0)}' has a note nearby. Check that the survey compares the same kind of products, "
                  "on a fair basis, with real users, and that the claim matches what was measured.",
                  f"「{m.group(0)}」の近くに注記があります。比べた対象が同じ種類の商品か、基準が公正か、"
                  "実際に使った人の調査か、言っている中身と調べた中身が合っているかを確かめる。",
                  "Keep the note readable and next to the claim.", "注記は読める大きさで、言い方のすぐ近くに置く。",
                  "景品表示法 第5条第1号", SRC_NO1, m.start())

    for m in ABSOLUTE.finditer(t) if commerce else ():
        r.add("KEIHYO_ABSOLUTE_CLAIM", "warning",
              f"Absolute claim '{m.group(0)}'. Results that vary by person cannot be promised; the CAA can require "
              "reasonable evidence within 15 days.",
              f"「{m.group(0)}」は言い切りです。人によって結果が違う物を約束する言い方は優良誤認のおそれがあり、"
              "消費者庁は15日以内に合理的な根拠を出すよう求めることができます。",
              "State only what you can prove, with conditions.", "確かめた事実だけを、条件つきで書く。",
              "景品表示法 第5条第1号・第7条第2項", SRC_KEIHYO, m.start())

    for m in DOUBLE.finditer(t) if commerce else ():
        r.add("KEIHYO_DOUBLE_PRICE", "warning",
              f"Comparison/discount price '{m.group(0)}'. Our 'regular price' must be a price actually sold for a "
              "substantial recent period (guideline yardstick: more than half of the 8 weeks before the sale - or of "
              "the whole sales period if shorter - at least 2 weeks in total, and not more than 2 weeks since it "
              "was last sold at that price). A manufacturer's suggested price must be one the manufacturer really "
              "published; a 'market price' needs proof of the actual market. Otherwise it may be misleading (有利誤認).",
              f"「{m.group(0)}」は比べる値段の表示です。「当社通常価格」と書けるのは、最近の相当期間に実際に売っていた値段だけです"
              "(目安: セール開始からさかのぼる8週間(販売が8週間より短ければその期間)の過半で、通算2週間以上、"
              "かつその値段で最後に売った日から2週間以内)。希望小売価格はメーカーが本当に公表した値段、市場価格は実際の相場の"
              "根拠が要ります。そうでなければ有利誤認のおそれがあります。",
              "Show the actual price flow instead (e.g. 'first month ¥100, then ¥980/month').",
              "実際の料金の流れで書く(例「初月100円、2か月目から月980円」)。",
              "景品表示法 第5条第2号・価格表示ガイドライン", SRC_DOUBLE, m.start())

    for m in SCARCITY.finditer(t):
        r.add("KEIHYO_SCARCITY", "info",
              f"Limited-offer wording '{m.group(0)}'. It must be true (real stock / real deadline, ended on time).",
              f"「{m.group(0)}」は数や期限で区切る言い方です。本当の数・本当の期限であること(過ぎたら終える)。",
              "Keep the count and deadline real; do not extend silently.", "数と期限を本当に守る。黙って延ばさない。",
              "景品表示法 第5条第2号", SRC_KEIHYO, m.start())

    for m in HEALTH.finditer(t):
        r.add("OUT_OF_SCOPE_HEALTH_CLAIM", "warning",
              f"Health/medical wording '{m.group(0)}'. Claims about curing or body effects are regulated by the "
              "Pharmaceutical and Medical Device Act and the Health Promotion Act. Not checked by this tool.",
              f"「{m.group(0)}」は体への効き目の言い方です。薬機法・健康増進法の対象になり得ます。この道具では判断しません。",
              "Have a specialist review it.", "専門家に確かめてもらう。",
              "薬機法 第66〜68条・健康増進法 第65条(この道具の範囲外)", SRC_KEIHYO, m.start())

    m = DISCLAIMER.search(t)
    if m and (r.findings):
        r.add("KEIHYO_DISCLAIMER_DOES_NOT_CANCEL", "info",
              f"'{m.group(0)}' does not cancel a strong claim elsewhere; the CAA looks at the overall impression.",
              f"「{m.group(0)}」と書いても、ほかの強い言い方が打ち消されるわけではありません(消費者庁は全体の印象で判断します)。",
              "Fix the claim itself instead of relying on the note.", "注記に頼らず、言い方そのものを直す。",
              "景品表示法 第5条(打消し表示)", SRC_KEIHYO, m.start())

    r.not_checked = ["images and video (text only)", "whether a survey or price history is real",
                     "industry-specific codes (公正競争規約)", "Pharmaceutical Act / Health Promotion Act in detail"]
    return r.out()


# ---------------------------------------------------------------- 特定商取引法
PHONE = re.compile(r"(0\d{1,4}[-(\s]?\d{1,4}[-)\s]?\d{3,4}|\+81[-\s]?\d)")
PREF = re.compile(r"(北海道|東京都|京都府|大阪府|.{2,3}県)\S*?(市|区|町|村|郡)")
DISCLOSE_ON_REQUEST = re.compile(r"(請求|お申し出|ご請求).{0,20}(遅滞なく|速やかに|すみやかに).{0,10}(開示|提供|お知らせ|通知)")

TOKUSHO_ITEMS = [
    # (rule, label_en, label_ja, regex, law)
    ("TOKUSHO_SELLER_NAME", "seller name", "販売業者の名前",
     r"(販売業者|事業者(名|の名称)?|販売事業者|運営(者|会社)|会社名|氏名|屋号|名称)", "施行規則 第23条"),
    ("TOKUSHO_ADDRESS", "address", "住所", r"(所在地|住所)", "施行規則 第23条"),
    ("TOKUSHO_PHONE", "phone number", "電話番号", r"(電話番号|電話|TEL|Tel|tel)", "施行規則 第23条"),
    ("TOKUSHO_PRICE", "price", "販売価格", r"(販売価格|価格|料金|代金|対価)", "法 第11条第1号"),
    ("TOKUSHO_EXTRA_COST", "other costs (shipping, fees)", "価格以外にかかるお金(送料・手数料)",
     r"(送料|手数料|商品代金以外|追加(料金|費用)|その他(の)?費用|別途)", "法 第11条第1号・施行規則 第23条"),
    ("TOKUSHO_PAY_TIMING_METHOD", "payment timing and method", "支払の時期と方法",
     r"(支払|お支払い|決済)", "法 第11条第2号"),
    ("TOKUSHO_DELIVERY", "delivery / service start timing", "引渡し・提供の時期",
     r"(引渡|引き渡|お届け|発送|配送|提供(時期|開始)|納品|ダウンロード|利用開始|すぐに(ご)?利用)", "法 第11条第3号"),
    ("TOKUSHO_CANCEL", "cancellation / returns", "申込みの撤回・解除(返品・キャンセル)",
     r"(返品|返金|キャンセル|解約|撤回|解除|交換)", "法 第11条第5号"),
]


def check_tokusho(text, digital=False, subscription=False, corporate=False, final_screen=False):
    r = Report("tokusho-final-screen" if final_screen else "tokusho", text)
    t = "\n".join(r.lines)
    if final_screen:
        items = [
            ("TOKUSHO_FINAL_QUANTITY", "quantity / number of deliveries", "分量(数・回数・期間)",
             r"(数量|個数|分量|回数|\d+\s?(個|本|袋|回|か月|ヶ月|カ月|日分)|内容量)", "法 第12条の6第1項"),
            ("TOKUSHO_FINAL_PRICE", "price", "販売価格・対価", r"(価格|料金|代金|合計|お支払い金額|円)", "法 第12条の6第1項"),
            ("TOKUSHO_FINAL_PAYMENT", "payment timing and method", "支払の時期と方法", r"(支払|お支払い|決済|引き落とし)", "法 第12条の6第1項"),
            ("TOKUSHO_FINAL_DELIVERY", "delivery timing", "引渡し・提供の時期", r"(お届け|発送|配送|提供|引渡|利用開始)", "法 第12条の6第1項"),
            ("TOKUSHO_FINAL_CANCEL", "cancellation terms", "申込みの撤回・解除", r"(解約|キャンセル|撤回|解除|返品)", "法 第12条の6第1項"),
        ]
        if subscription:
            # for recurring contracts the number of deliveries/period and the total or later amounts are part of 分量・価格
            items += [
                ("TOKUSHO_FINAL_SUB_COUNT", "number of deliveries / contract period", "定期の回数・契約期間(分量)",
                 r"(\d+\s?回(分|目|まで|以上)|回数|契約期間|\d+\s?(か月|ヶ月|カ月|年)(間|ごと|毎)|縛り|期間の定めなし|いつでも解約)", "法 第12条の6第1項"),
                ("TOKUSHO_FINAL_SUB_PRICE", "price from the 2nd time / total", "2回目以降の金額または総額",
                 r"((2回目|次回)(以降|から)[^\n]{0,20}?[\d,]+\s?円|総額[^\n]{0,10}?[\d,]+\s?円|毎月\s?[\d,]+\s?円|月額\s?[\d,]+\s?円)",
                 "法 第12条の6第1項"),
                ("TOKUSHO_FINAL_SUB_PAY_TIMING", "payment timing for each delivery", "毎回の支払の時期",
                 r"(毎月\s?\d+\s?日|お届け(の)?(都度|ごと)|更新日|引き落とし日|請求日|ご注文時|発送時)", "法 第12条の6第1項"),
            ]
    else:
        items = list(TOKUSHO_ITEMS)
        if corporate:
            items.append(("TOKUSHO_REPRESENTATIVE", "representative or responsible person", "代表者または責任者の名前",
                          r"(代表者|代表取締役|責任者|運営責任者)", "施行規則 第23条"))
        if digital:
            items.append(("TOKUSHO_SYSTEM_REQUIREMENTS", "system requirements", "動作環境(必要なパソコンの仕様)",
                          r"(動作環境|推奨環境|対応(OS|ブラウザ|環境)|必要(な)?環境|Windows|Mac|iOS|Android)", "施行規則 第23条"))
        if subscription:
            items.append(("TOKUSHO_SUBSCRIPTION_TERMS", "subscription terms (amount, period)", "定期・継続の条件(金額・期間)",
                          r"(定期|継続|自動(で)?更新|月額|年額|契約期間|毎月)", "施行規則 第23条"))

    _placeholders(r, t, "特定商取引法 第11条", SRC_TOKUSHO)
    on_request = DISCLOSE_ON_REQUEST.search(t)
    phone_number = PHONE.search(t)
    if final_screen:
        m = re.search(r"(購入(には|では)(なりません|ありません)|申込み?(には|では)(なりません|ありません)|無料で(お試し|もらえる)|"
                      r"お試し(だけ|のみ)|0\s?円で)", t)
        if m:
            r.add("TOKUSHO_FINAL_MISLEADING", "warning",
                  f"'{m.group(0)}' on the final screen may make people think the click is not a paid order "
                  "(or hide later charges).",
                  f"「{m.group(0)}」は、押しても有料の申込みにならない、または後の支払いがないと思わせるおそれがあります。",
                  "State plainly that this is a paid order and show every later charge.",
                  "有料の申込みであることと、後の支払いを全部はっきり書く。", "特定商取引法 第12条の6第2項", SRC_TOKUSHO, m.start())
        lim = re.search(r"(期間限定|先着|まで(の)?(お)?申込|締め?切り?)", t)
        if lim and not re.search(r"(\d{1,2}\s?月\s?\d{1,2}\s?日|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d+\s?名)", t):
            r.add("TOKUSHO_FINAL_APPLY_PERIOD", "error", "A limited offer without its actual period or limit.",
                  "申込みの期間・数の定めがあるのに、その中身(日付・人数)が見つかりません。", "Write the end date or the count.",
                  "締め切りの日付か人数を書く。", "特定商取引法 第12条の6第1項(第11条第4号)", SRC_TOKUSHO, lim.start())
    for rule, en, ja, rx, law in items:
        if re.search(rx, t):
            continue
        sev = "error"
        if rule == "TOKUSHO_PHONE" and phone_number:
            continue
        if on_request and rule in ("TOKUSHO_SELLER_NAME", "TOKUSHO_ADDRESS", "TOKUSHO_PHONE", "TOKUSHO_REPRESENTATIVE"):
            sev = "info"
        r.add(rule, sev,
              f"Required item not found: {en}." + (" (The page says it will be disclosed on request; that is allowed "
                                                   "only if you really send it without delay.)" if sev == "info" else ""),
              f"表示が必要な事項が見つかりません: {ja}。" + ("(請求があれば遅滞なく書面・電子で出すと書かれています。"
                                                      "本当にすぐ出せる用意がある場合だけ、広告での表示を省けます。法 第11条ただし書)" if sev == "info" else ""),
              f"Add a row for {en}.", f"「{ja}」の行を足す。", "特定商取引法 " + law, SRC_TOKUSHO)

    if not final_screen and re.search(r"(電話番号|電話|TEL)", t) and not PHONE.search(t) and not on_request:
        r.add("TOKUSHO_PHONE_VALUE", "warning", "A phone label exists but no phone number was recognised.",
              "電話番号の見出しはありますが、番号が見つかりません。", "Write the actual number.", "実際の番号を書く。",
              "特定商取引法 施行規則 第23条", SRC_TOKUSHO)
    if not final_screen and re.search(r"(所在地|住所)", t) and not PREF.search(t) and not on_request:
        r.add("TOKUSHO_ADDRESS_VALUE", "warning", "An address label exists but no Japanese address was recognised.",
              "住所の見出しはありますが、住所(都道府県・市区町村)が見つかりません。", "Write the full address.",
              "番地まで書く。", "特定商取引法 施行規則 第23条", SRC_TOKUSHO)
    if not final_screen and re.search(r"(支払|お支払い|決済)", t) and not re.search(
            r"(時期|時点|前払|後払|前金|ご注文時|注文時|購入時|決済時|即時|以内|までに|毎月|請求時|引き落とし日|代金引換|代引)", t):
        r.add("TOKUSHO_PAY_TIMING", "warning", "Payment method is shown but not the payment timing.",
              "支払の方法はありますが、支払の時期(注文時・前払い・○日以内など)が見つかりません。",
              "Write when payment happens for each method.", "方法ごとに、いつ払うかを書く。",
              "特定商取引法 第11条第2号", SRC_TOKUSHO)
    m = re.search(r"送料(は)?\s?別途(?![^\n]{0,20}\d)", t)
    if m and not final_screen:
        r.add("TOKUSHO_SHIPPING_AMOUNT", "warning", "Shipping is 'separate' but no amount or rule is shown.",
              "送料が「別途」とだけ書かれ、金額や決め方がありません。送料も価格の一部として示す必要があります。",
              "Write the amount (or a table by region/size).", "金額(または地域・大きさごとの表)を書く。",
              "特定商取引法 第11条第1号", SRC_TOKUSHO, m.start())
    m = re.search(r"((返品|キャンセル|返金)(は)?(一切)?(不可|できません|お受けできません|いたしません)|ノークレーム|ノーリターン)", t)
    if m and not final_screen:
        r.add("TOKUSHO_NO_RETURN_CHECK", "info",
              "Returns refused. For mail order this is allowed only if it is clearly shown in the ad (返品特約). "
              "Defective goods are a separate matter (契約不適合).",
              "返品を受けない書き方です。通信販売では広告に分かりやすく書いてあれば認められます(返品特約)。"
              "不良品の扱いは別の決まり(契約不適合責任)です。",
              "Keep it visible and separate from defect handling.", "見やすく書き、不良品の扱いは別に書く。",
              "特定商取引法 第11条第5号・第15条の3", SRC_TOKUSHO, m.start())
    m = re.search(r"(No\.?\s?1|日本一|世界一|絶対|必ず|100\s?%)", t)
    if m:
        r.add("TOKUSHO_EXAGGERATION", "warning", f"Exaggeration '{m.group(0)}' on a legal page.",
              f"「{m.group(0)}」は誇大広告のおそれがある言い方です。", "Run `jpcheck ad` on the page.",
              "`jpcheck ad` でも確かめる。", "特定商取引法 第12条", SRC_TOKUSHO, m.start())
    r.not_checked = ["whether the written values are true", "layout and font size",
                     "the order flow itself (only the text you pass is checked)"]
    return r.out()


# ---------------------------------------------------------------- invoice / regno
def check_invoice(data, role="issue"):
    r = Report("invoice")
    try:
        res = inv_rules.check_invoice(data, role=role)
    except (AttributeError, TypeError, KeyError, IndexError) as e:
        raise ValueError(f"invoice JSON has an unexpected shape ({type(e).__name__}: {e}); see references/invoice.md") from e
    for m in res["errors"] + res["warnings"]:
        r.findings.append({"id": f"invoice-{len(r.findings) + 1:03d}", "rule": m["code"], "severity": m["level"],
                           "message_en": m["message"], "message_ja": m["message_ja"], "fix_en": "", "fix_ja": "",
                           "law": "消費税法 第57条の4(適格請求書の記載事項)", "source": SRC_INVOICE,
                           "evidence": {"field": m["field"]}, "needs_review": True})
    o = r.out()
    o["detail"] = {k: res[k] for k in res if k not in ("errors", "warnings")}
    o["not_checked"] = ["whether the registration is valid today (no network; use the NTA public site)",
                        "simplified invoices (適格簡易請求書)", "the 80%/50% transitional deduction"]
    return o


def check_regno(values):
    r = Report("regno")
    results = []
    for v in values:
        x = inv_rules.check_registration_number(v)
        results.append({k: x[k] for k in ("input", "normalized", "valid_format", "corporate_check_digit_ok")})
        for m in x["messages"]:
            r.findings.append({"id": f"regno-{len(r.findings) + 1:03d}", "rule": m["code"], "severity": m["level"],
                               "message_en": m["message"], "message_ja": m["message_ja"], "fix_en": "", "fix_ja": "",
                               "law": "消費税法 第57条の2", "source": SRC_INVOICE, "evidence": {"input": v},
                               "needs_review": True})
    o = r.out()
    o["results"] = results
    o["not_checked"] = ["whether the number is registered today (no network)"]
    return o


def _read(path):
    data = sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("cannot decode input (UTF-8 or Shift_JIS)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="jpcheck", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ad"); p.add_argument("file")
    p = sub.add_parser("tokusho"); p.add_argument("file")
    for f in ("--digital", "--subscription", "--corporate", "--final-screen"):
        p.add_argument(f, action="store_true")
    p = sub.add_parser("invoice"); p.add_argument("file"); p.add_argument("--role", choices=("issue", "receive"), default="issue")
    p = sub.add_parser("regno"); p.add_argument("numbers", nargs="+")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "ad":
            out = check_ad(_read(a.file))
        elif a.cmd == "tokusho":
            out = check_tokusho(_read(a.file), a.digital, a.subscription, a.corporate, a.final_screen)
        elif a.cmd == "invoice":
            data = json.loads(_read(a.file))
            if not isinstance(data, dict):
                raise ValueError("invoice JSON must be an object")
            out = check_invoice(data, a.role)
        else:
            out = check_regno(a.numbers)
    except (OSError, ValueError) as e:
        print(json.dumps({"tool": "jpcheck", "error": str(e)}, ensure_ascii=False))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if out["summary"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
