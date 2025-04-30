import unittest
import subprocess
import time

class TestScrapper(unittest.TestCase):
  def test_scrapper_runs_successfully(self):
    """Verifica que el script se ejecuta correctamente y sin errores."""
    result = subprocess.run(['python3', 'fb_marketplace.py'], capture_output=True, text=True)
    assert result.returncode == 0, f"Error en ejecución: {result.stderr}"

  def test_scrapper_execution_time(self):
      start = time.time()
      result = subprocess.run(['python3', 'fb_marketplace.py'], capture_output=True, text=True)
      duration = time.time() - start
      assert result.returncode == 0, f"Error en ejecución: {result.stderr}"
      assert duration < 600, f"Ejecución superó 10 minutos"

    