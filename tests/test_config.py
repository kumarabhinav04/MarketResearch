from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aifactory.config import load_env_file


class DotenvTests(unittest.TestCase):
    def test_loads_values_without_overwriting_runtime_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# comment\nAIFACTORY_TEST_NEW='from-file'\n"
                "AIFACTORY_TEST_EXISTING=from-file\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"AIFACTORY_TEST_EXISTING": "from-runtime"},
                clear=False,
            ):
                os.environ.pop("AIFACTORY_TEST_NEW", None)
                load_env_file(path)
                self.assertEqual(os.environ["AIFACTORY_TEST_NEW"], "from-file")
                self.assertEqual(os.environ["AIFACTORY_TEST_EXISTING"], "from-runtime")


if __name__ == "__main__":
    unittest.main()
