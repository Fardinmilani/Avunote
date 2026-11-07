"""Presentation helpers: bidi embedding, elided combo values, themed tooltips and checkmarks."""
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication
    import studio_theme as theme
except ImportError:
    theme = None


@unittest.skipIf(theme is None, 'Qt dependencies unavailable')
class ThemePolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_bidi_embedding_only_when_direction_disagrees(self):
        self.assertEqual(theme.base_direction('  (2) Microphone'), 'ltr')
        self.assertEqual(theme.base_direction('میکروفون USB'), 'rtl')
        self.assertIsNone(theme.base_direction('123 · ()'))
        self.assertEqual(theme.bidi_embed('Microphone (USB)', True), '\u202aMicrophone (USB)\u202c')
        self.assertEqual(theme.bidi_embed('میکروفون', False), '\u202bمیکروفون\u202c')
        self.assertEqual(theme.bidi_embed('Microphone', False), 'Microphone')
        self.assertEqual(theme.bidi_embed('میکروفون', True), 'میکروفون')

    def test_long_combo_value_is_elided_but_text_is_unchanged(self):
        combo = theme.ChevronComboBox()
        long_name = 'Microphone (2- Realtek(R) High Definition Audio) · Windows WASAPI'
        combo.addItem(long_name)
        combo.resize(160, 44)
        combo.show()
        combo.grab()
        self.assertTrue(combo._elided)
        self.assertEqual(combo.currentText(), long_name)
        combo.resize(900, 44)
        combo.grab()
        self.assertFalse(combo._elided)
        combo.close()

    def test_tooltips_and_checkmarks_follow_theme(self):
        for name in ('light', 'dark'):
            colors = theme.COLORS[name]
            palette = theme.native_palette(name)
            self.assertEqual(palette.color(QPalette.ColorRole.ToolTipBase).name().upper(), colors['tip_bg'].upper())
            sheet = theme.stylesheet(name, rtl=name == 'dark')
            self.assertIn(f'background: {colors["tip_bg"]}', sheet)
            self.assertNotIn('$', sheet)
            check = theme.check_mark(colors['action_ink'])
            self.assertTrue(Path(check).exists())
            self.assertIn(check, sheet)
        self.assertNotEqual(theme.COLORS['dark']['tip_bg'], theme.COLORS['dark']['text'])


if __name__ == '__main__':
    unittest.main()
