import base64
import importlib.util
import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = APP_ROOT / "scripts" / "cafe24_gmail_order_witness.py"
spec = importlib.util.spec_from_file_location("cafe24_gmail_order_witness", SCRIPT_PATH)
gmail_witness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gmail_witness
spec.loader.exec_module(gmail_witness)


def b64url(value):
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


class Cafe24GmailOrderWitnessTest(unittest.TestCase):
    def test_extract_order_ids_deduplicates_subject_and_body(self):
        order_ids = gmail_witness.extract_order_ids(
            "[인스타마트] 20260603-0000011 주문 내역",
            "주문번호 20260603-0000011 / 20260603-0000012",
        )

        self.assertEqual(order_ids, ["20260603-0000011", "20260603-0000012"])

    def test_witness_from_gmail_message_decodes_nested_payload(self):
        message = {
            "id": "msg_1",
            "threadId": "thread_1",
            "internalDate": "1780501065000",
            "snippet": "주문번호 20260603-0000011",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "[인스타마트] 주문 내역"},
                    {"name": "From", "value": "no-reply@cafe24shop.com"},
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": b64url("<p>주문번호</p><strong>20260603-0000011</strong>"),
                        },
                    }
                ],
            },
        }

        witness = gmail_witness.witness_from_gmail_message(message)

        self.assertEqual(witness.message_id, "msg_1")
        self.assertEqual(witness.thread_id, "thread_1")
        self.assertEqual(witness.sender, "no-reply@cafe24shop.com")
        self.assertEqual(witness.order_ids, ["20260603-0000011"])

    def test_witness_payload_sends_order_ids_and_message_ids_only(self):
        witness = gmail_witness.GmailOrderWitness(
            message_id="msg_1",
            thread_id="thread_1",
            subject="[인스타마트] 이진아 님 주문 내역을 알려드립니다.",
            sender="no-reply@cafe24shop.com",
            internal_date="1780501065000",
            order_ids=["20260603-0000011"],
        )

        payload = gmail_witness.witness_payload([witness])

        self.assertEqual(payload["source"], "gmail_order_witness")
        self.assertEqual(payload["orderIds"], ["20260603-0000011"])
        self.assertEqual(payload["gmailMessageIds"], ["msg_1"])
        encoded = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("이진아", encoded)
        self.assertNotIn("no-reply@cafe24shop.com", encoded)

    def test_missing_credentials_can_skip_without_failure(self):
        with patch.dict("os.environ", {}, clear=True), redirect_stdout(StringIO()):
            status = gmail_witness.main(["--allow-missing-credentials"])

        self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()
