import unittest

import composition_pipeline


class PackageTest(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(
            composition_pipeline.__all__,
            ["EditProtocolError", "apply_edit_document"],
        )


if __name__ == "__main__":
    unittest.main()
