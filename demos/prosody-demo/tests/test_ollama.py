import io
import json
import unittest
from unittest.mock import patch

from prosody_demo.ollama import OllamaClient
from prosody_demo.server import _validate_chat


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class OllamaClientTests(unittest.TestCase):
    @patch("prosody_demo.ollama.urlopen")
    def test_lists_model_names(self, urlopen):
        urlopen.return_value = FakeResponse(
            json.dumps({"models": [{"name": "gemma3:4b"}]}).encode()
        )
        self.assertEqual(OllamaClient().list_models(), ["gemma3:4b"])

    @patch("prosody_demo.ollama.urlopen")
    def test_chat_disables_streaming(self, urlopen):
        urlopen.return_value = FakeResponse(
            json.dumps({"message": {"role": "assistant", "content": "hello"}}).encode()
        )
        result = OllamaClient().chat("gemma3:4b", [{"role": "user", "content": "hi"}])
        self.assertEqual(result["message"]["content"], "hello")
        request = urlopen.call_args.args[0]
        self.assertFalse(json.loads(request.data)["stream"])


class ValidationTests(unittest.TestCase):
    def test_accepts_both_demo_modes(self):
        for mode in ("baseline", "prosody"):
            model, selected_mode, messages = _validate_chat(
                {"model": "gemma3:4b", "mode": mode, "messages": [{"role": "user", "content": "hi"}]}
            )
            self.assertEqual(model, "gemma3:4b")
            self.assertEqual(selected_mode, mode)
            self.assertEqual(messages[-1]["content"], "hi")

    def test_rejects_retired_speculative_mode(self):
        with self.assertRaisesRegex(ValueError, "baseline or prosody"):
            _validate_chat(
                {"model": "gemma3:4b", "mode": "speculative", "messages": [{"role": "user", "content": "hi"}]}
            )

    def test_injects_measurements_only_in_prosody_mode(self):
        payload = {
            "model": "gemma3:4b",
            "mode": "prosody",
            "messages": [{"role": "user", "content": "hello"}],
            "prosody": {"features": {"energy_rms": 0.2}},
        }
        self.assertIn("Measured delivery metadata", _validate_chat(payload)[2][-1]["content"])
        payload["mode"] = "baseline"
        self.assertEqual(_validate_chat(payload)[2][-1]["content"], "hello")


if __name__ == "__main__":
    unittest.main()
