"""Localization contract tests; no GUI, network, recordings, or model loading."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
import ui_i18n as i18n
from model_catalog import LANGUAGES


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        i18n.register_speech_languages(LANGUAGES)
        i18n.set_language('en')

    def tearDown(self):
        i18n.set_language('en')

    def test_default_and_invalid_locale_are_english(self):
        i18n.set_language('not-a-locale')
        self.assertEqual(i18n.current_language(), 'en')
        self.assertEqual(i18n.tr('شروع ضبط'), 'Start recording')

    def test_all_english_source_translations_have_no_persian(self):
        for source in i18n.EN:
            with self.subTest(source=source):
                self.assertFalse(any('\u0600' <= char <= '\u06ff' for char in i18n.tr(source)))

    def test_dynamic_progress_elapsed_and_counts(self):
        examples = [
            '99 زبان در دسترس',
            '3 مدل محلی شناسایی شد؛ فایل‌ها جابه‌جا یا دوباره دانلود نمی‌شوند.',
            'در حال ضبط  ·  01:22  ·  برای تبدیل، پایان ضبط را بزنید.',
            'تشخیص گفتار · بخش 2 از 4  ·  12 ثانیه گذشته است  ·  whisper-base-full',
            'در حال دانلود  ·  33.8%  ·  50 MB / 148 MB  ·  2 MB/s  ·  حدود 00:49 باقی‌مانده',
            'صوت: 2.0 ثانیه   |   تشخیص: 3.0 ثانیه   |   کل: 4.0 ثانیه   |   RAM: 500 MiB   |   CPU',
            'مجوز: MIT (اعلام توسعه‌دهنده)  ·  پردازش روی CPU',
        ]
        for source in examples:
            with self.subTest(source=source):
                result = i18n.tr(source)
                self.assertFalse(any('\u0600' <= char <= '\u06ff' for char in result), result)

    def test_speech_language_names_do_not_change_model_codes(self):
        for language in LANGUAGES:
            title = i18n.language_title(language)
            self.assertTrue(title)
            self.assertFalse(any('\u0600' <= char <= '\u06ff' for char in title), title)

    def test_persian_preserves_original_ui_strings(self):
        i18n.set_language('fa')
        self.assertEqual(i18n.tr('شروع ضبط'), 'شروع ضبط')
        self.assertEqual(i18n.tr('دانلود مدل'), 'دانلود مدل')

    def test_interface_directions_are_separate_from_speech(self):
        self.assertEqual(i18n.RTL_LANGUAGES, {'fa', 'ar'})
        self.assertNotIn('az', i18n.RTL_LANGUAGES)
        self.assertIn('en', dict(i18n.UI_LANGUAGES))

    def test_every_secondary_locale_covers_static_ui_copy(self):
        from ui_locales import TRANSLATIONS
        for code in ['tr', 'ar', 'az']:
            with self.subTest(locale=code):
                self.assertFalse(set(i18n.EN.values()) - set(TRANSLATIONS[code]))

    def test_dynamic_values_survive_all_locale_templates(self):
        for code in dict(i18n.UI_LANGUAGES):
            i18n.set_language(code)
            with self.subTest(locale=code):
                self.assertIn('99', i18n.tr('99 زبان در دسترس'))
                self.assertIn('01:22', i18n.tr('در حال ضبط  ·  01:22  ·  برای تبدیل، پایان ضبط را بزنید.'))
                self.assertIn('00:49', i18n.tr('حدود 00:49 باقی‌مانده'))


if __name__ == '__main__':
    unittest.main()
