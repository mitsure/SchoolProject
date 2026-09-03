import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from run import environment_flag, load_environment_file


class RunConfigurationTest(unittest.TestCase):
    def test_load_environment_file_keeps_existing_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("EXISTING='file-value'\nNEW_VALUE='loaded value'\n", encoding="utf-8")
            with patch.dict(os.environ, {"EXISTING": "shell-value"}, clear=True):
                load_environment_file(path)
                self.assertEqual(os.environ["EXISTING"], "shell-value")
                self.assertEqual(os.environ["NEW_VALUE"], "loaded value")

    def test_environment_flag(self):
        with patch.dict(os.environ, {"ENABLED": "yes", "DISABLED": "0"}, clear=True):
            self.assertTrue(environment_flag("ENABLED"))
            self.assertFalse(environment_flag("DISABLED"))
            self.assertTrue(environment_flag("MISSING", default=True))


if __name__ == "__main__":
    unittest.main()
