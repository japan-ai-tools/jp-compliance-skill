"""jpcheck tests. Standard library only: python -m unittest discover -s tests"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import jpcheck  # noqa: E402

EX = ROOT / "examples"


def rules(out):
    return [f["rule"] for f in out["findings"]]


class TestAd(unittest.TestCase):
    def test_bad_example(self):
        out = jpcheck.check_ad((EX / "ad_bad.txt").read_text(encoding="utf-8"))
        r = rules(out)
        for want in ("KEIHYO_STEALTH_NO_DISCLOSURE", "KEIHYO_NO1_NO_BASIS", "KEIHYO_ABSOLUTE_CLAIM",
                     "KEIHYO_DOUBLE_PRICE", "KEIHYO_SCARCITY", "OUT_OF_SCOPE_HEALTH_CLAIM"):
            self.assertIn(want, r)
        stealth = [f for f in out["findings"] if f["rule"] == "KEIHYO_STEALTH_NO_DISCLOSURE"][0]
        self.assertEqual(stealth["evidence"]["line"], 7)             # the affiliate link line
        self.assertTrue(all(f["needs_review"] and f["source"].startswith("https://") for f in out["findings"]))

    def test_good_example_is_clean(self):
        out = jpcheck.check_ad((EX / "ad_good.txt").read_text(encoding="utf-8"))
        self.assertEqual(out["summary"], {"error": 0, "warning": 0, "info": 0}, rules(out))

    def test_disclosure_only_at_the_end_is_a_warning(self):
        text = "\n".join(["使ってよかったです。"] * 60 + ["https://amzn.to/abc", "※この記事は広告を含みます"])
        out = jpcheck.check_ad(text)
        self.assertIn("KEIHYO_STEALTH_DISCLOSURE_NOT_PROMINENT", rules(out))
        self.assertNotIn("KEIHYO_STEALTH_NO_DISCLOSURE", rules(out))

    def test_no1_with_basis_is_only_a_warning(self):
        out = jpcheck.check_ad("売上No.1 ※2025年4月〜9月 自社EC 美容液カテゴリ 自社調べ")
        self.assertEqual(rules(out), ["KEIHYO_NO1_CHECK_BASIS"])

    def test_full_width_is_normalized(self):
        out = jpcheck.check_ad("満足度Ｎｏ．１!")
        self.assertIn("KEIHYO_NO1_NO_BASIS", rules(out))

    def test_ordinary_words_are_not_flagged(self):
        out = jpcheck.check_ad("がんばって作りました。最高の一日を。絶対値の計算。")
        self.assertEqual(out["findings"], [])


class TestTokusho(unittest.TestCase):
    def test_bad_example_lists_missing_items(self):
        out = jpcheck.check_tokusho((EX / "tokusho_bad.txt").read_text(encoding="utf-8"), digital=True, corporate=True)
        r = rules(out)
        for want in ("TOKUSHO_ADDRESS", "TOKUSHO_PHONE", "TOKUSHO_EXTRA_COST", "TOKUSHO_DELIVERY",
                     "TOKUSHO_REPRESENTATIVE", "TOKUSHO_SYSTEM_REQUIREMENTS", "TOKUSHO_PAY_TIMING", "TOKUSHO_NO_RETURN_CHECK"):
            self.assertIn(want, r)
        self.assertGreaterEqual(out["summary"]["error"], 6)

    def test_good_example(self):
        out = jpcheck.check_tokusho((EX / "tokusho_good.txt").read_text(encoding="utf-8"),
                                    digital=True, corporate=True, subscription=True)
        self.assertEqual(out["summary"]["error"], 0, rules(out))
        self.assertEqual(out["summary"]["warning"], 0, rules(out))

    def test_disclose_on_request_downgrades_identity_items(self):
        out = jpcheck.check_tokusho("販売価格: 1,000円\n住所・電話番号: ご請求があれば遅滞なく開示します\n"
                                    "送料: 無料\nお支払い: ご注文時にカード決済\nお届け: 決済後すぐにダウンロード\n返品: 不良品のみ交換")
        sev = {f["rule"]: f["severity"] for f in out["findings"]}
        self.assertEqual(sev.get("TOKUSHO_SELLER_NAME"), "info")

    def test_unfilled_template_is_an_error(self):
        text = (EX / "tokusho_good.txt").read_text(encoding="utf-8").replace("03-1234-5678", "【要記入: 電話番号】")
        out = jpcheck.check_tokusho(text, digital=True, corporate=True, subscription=True)
        self.assertIn("UNFILLED_PLACEHOLDER", rules(out))
        out = jpcheck.check_tokusho("販売業者: ○○株式会社")
        self.assertIn("UNFILLED_PLACEHOLDER", rules(out))
        out = jpcheck.check_ad("【PR】【重要】本日のお知らせ")
        self.assertNotIn("UNFILLED_PLACEHOLDER", rules(out))

    def test_final_screen(self):
        out = jpcheck.check_tokusho("合計 2,980円(税込)\nお支払い: ご注文時にカード決済", final_screen=True, subscription=True)
        r = rules(out)
        for want in ("TOKUSHO_FINAL_QUANTITY", "TOKUSHO_FINAL_DELIVERY", "TOKUSHO_FINAL_CANCEL", "TOKUSHO_FINAL_SUB_COUNT"):
            self.assertIn(want, r)
        self.assertNotIn("TOKUSHO_FINAL_PRICE", r)


class TestReviewRegressions(unittest.TestCase):
    """Cases found by the independent review on 2026-11-23."""

    def test_bracket_headings_are_not_blanks(self):
        page = (EX / "tokusho_good.txt").read_text(encoding="utf-8").replace("販売業者:", "【販売業者】")
        out = jpcheck.check_tokusho(page, digital=True, corporate=True, subscription=True)
        self.assertNotIn("UNFILLED_PLACEHOLDER", rules(out))
        self.assertNotIn("UNFILLED_PLACEHOLDER", rules(jpcheck.check_ad("【公式】【送料無料】春の新作 3,980円")))

    def test_value_blanks_and_tbd_words(self):
        self.assertIn("UNFILLED_PLACEHOLDER", rules(jpcheck.check_tokusho("| 所在地 | 【住所】 |")))
        self.assertIn("UNFILLED_PLACEHOLDER", rules(jpcheck.check_tokusho("配送: 未定")))

    def test_subscription_trap_on_final_screen(self):
        out = jpcheck.check_tokusho("お試しセット 1個 500円\n※2回目以降は定期コース\n解約はお電話で\n"
                                    "このボタンを押しても購入にはなりません", final_screen=True, subscription=True)
        r = rules(out)
        for want in ("TOKUSHO_FINAL_SUB_PRICE", "TOKUSHO_FINAL_SUB_PAY_TIMING", "TOKUSHO_FINAL_MISLEADING"):
            self.assertIn(want, r)

    def test_stealth_holes(self):
        link = "\nhttps://px.a8.net/svt/ejp?a8mat=1"
        self.assertIn("KEIHYO_STEALTH_DENIES_AD", rules(jpcheck.check_ad("本記事は広告ではありません。" + link)))
        self.assertIn("KEIHYO_STEALTH_NO_DISCLOSURE", rules(jpcheck.check_ad("メーカー様から商品をいただきました。良かったです。")))
        self.assertIn("KEIHYO_STEALTH_NO_DISCLOSURE", rules(jpcheck.check_ad("自己PRです。https://amzn.to/abc")))
        self.assertIn("KEIHYO_STEALTH_NO_DISCLOSURE", rules(jpcheck.check_ad("おすすめ https://a.r10.to/abc")))

    def test_everyday_blog_has_no_errors(self):
        out = jpcheck.check_ad("学年1位をとった。日本一のお父さん。新曲『No.1』が好き。絶対また来たい。必ず成功するまで続ける。")
        self.assertEqual(out["summary"]["error"], 0, rules(out))

    def test_more_claims_in_sales_copy(self):
        r = rules(jpcheck.check_ad("業界トップクラスの品質。売上ナンバー1。飲むだけでたった3日で-5kg!今なら3,980円。※個人の感想です"))
        for want in ("KEIHYO_NO1_NO_BASIS", "OUT_OF_SCOPE_HEALTH_CLAIM", "KEIHYO_SCARCITY", "KEIHYO_DISCLAIMER_DOES_NOT_CANCEL"):
            self.assertIn(want, r)

    def test_phone_number_without_label(self):
        out = jpcheck.check_tokusho("お問い合わせ 086-123-4567")
        self.assertNotIn("TOKUSHO_PHONE", rules(out))

    def test_shipping_separate_and_no_cancel(self):
        r = rules(jpcheck.check_tokusho("送料別途\nキャンセル不可"))
        self.assertIn("TOKUSHO_SHIPPING_AMOUNT", r)
        self.assertIn("TOKUSHO_NO_RETURN_CHECK", r)

    def test_malformed_invoice_is_bad_input(self):
        for bad in ({"items": "x"}, {"issuer": "abc"}, {"items": [1]}):
            try:
                jpcheck.check_invoice(bad)
            except ValueError:
                continue
            except Exception as e:  # noqa: BLE001
                self.fail(f"{bad}: {type(e).__name__}")


class TestInvoiceAndRegno(unittest.TestCase):
    def test_invoice_rounding_error(self):
        out = jpcheck.check_invoice(json.loads((EX / "invoice_bad.json").read_text(encoding="utf-8")))
        self.assertEqual(rules(out), ["E_TAX_MISMATCH"])
        self.assertIn("by_rate", out["detail"])

    def test_regno(self):
        out = jpcheck.check_regno(["T7123456789012", "Ｔ７１２３４５６７８９０１２", "T123"])
        self.assertEqual([x["valid_format"] for x in out["results"]], [True, True, False])
        self.assertTrue(out["results"][0]["corporate_check_digit_ok"])


class TestCli(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "jpcheck.py"), *args], input=stdin,
                              capture_output=True, text=True, encoding="utf-8")

    def test_exit_codes_and_json(self):
        r = self.run_cli("ad", str(EX / "ad_bad.txt"))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["check"], "ad")
        self.assertEqual(self.run_cli("ad", str(EX / "ad_good.txt")).returncode, 0)
        self.assertEqual(self.run_cli("ad", "-", stdin="ふつうの文章です。").returncode, 0)
        self.assertEqual(self.run_cli("ad", str(EX / "nope.md")).returncode, 2)

    def test_shift_jis_input(self, ):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sjis.txt"
            p.write_bytes("日本一の品質".encode("cp932"))
            r = self.run_cli("ad", str(p))
            self.assertIn("KEIHYO_NO1_NO_BASIS", r.stdout)


if __name__ == "__main__":
    unittest.main()
