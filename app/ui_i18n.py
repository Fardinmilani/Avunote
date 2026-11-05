"""Small offline UI localization layer. Speech/model choices are independent."""
from __future__ import annotations

import re

UI_LANGUAGES = [('en', 'English'), ('fa', 'فارسی'), ('tr', 'Türkçe'),
                ('ar', 'العربية'), ('az', 'Azərbaycanca')]
RTL_LANGUAGES = {'fa', 'ar'}
_language = 'en'

EN = {
    'صدای شما. کلمات شما.': 'Your voice. Your words.',
    'فضای کار': 'WORKSPACE', 'استودیوی گفتار': 'Speech studio',
    'زبان‌ها و مدل‌ها': 'Model library', 'تاریخچه': 'History',
    'روی همین دستگاه': 'On your device',
    'صدای شما برای پردازش به اینترنت ارسال نمی‌شود.': 'Your audio stays on your device. No uploads.',
    'درباره و مجوزها': 'About & licenses', 'زبان رابط کاربری': 'Interface language',
    'از گفتن تا نوشتن': 'FROM VOICE TO WORDS', 'بگذار صدایت بنویسد.': 'Let your voice do the writing.',
    'فایل صوتی یا ضبط زنده؛ متن خام، خصوصی و به زبان خودتان.': 'An audio file or a live recording. Original words. Entirely private.',
    'آفلاین و خصوصی': 'Private & offline', 'زبان گفتار': 'Speech language',
    'مدل': 'Model', 'حالت پردازش': 'Processing mode',
    'دقت بیشتر': 'Higher accuracy', 'سریع‌تر': 'Faster',
    'مدیریت مدل‌ها': 'Manage models', 'دریافت مدل': 'Get model',
    'کتابخانه مدل‌ها': 'Model library', 'مدل تشخیص گفتار': 'Speech recognition model',
    'کیفیت پردازش': 'Processing quality', 'وضعیت مدل در حال بررسی است.': 'Checking model availability.',
    'مدل آماده است؛ تبدیل بدون اینترنت انجام می‌شود.': 'Model ready. Transcription works offline.',
    'این مدل هنوز روی دستگاه نیست؛ از کتابخانه دانلود کنید یا مدل محلی را معرفی کنید.': 'This model is not installed. Download it from the library or add a local model.',
    'ضبط مستقیم': 'Record your voice', 'صحبت کنید؛ با پایان ضبط، تبدیل شروع می‌شود.': 'Speak freely. Transcription starts when you stop.',
    'انتخاب میکروفون': 'Select microphone', 'بازخوانی میکروفون‌ها': 'Refresh microphones',
    'شروع ضبط': 'Start recording', 'فایل آماده دارید؟': 'Have an audio file?',
    'فایل را انتخاب کنید یا داخل پنجره رها کنید.': 'Choose a file or drop it into this window.',
    'هنوز فایلی انتخاب نشده': 'No file selected yet', 'انتخاب فایل صوتی': 'Choose audio file',
    'متن شما': 'Your transcript', 'خروجی خام مدل': 'Original model output',
    'متن خام خروجی مدل': 'Unedited model transcript',
    'اینجا، صدای شما به کلمات تبدیل می‌شود…\n\nبرای شروع، یک فایل انتخاب کنید یا ضبط را بزنید.': 'Your voice becomes words here…\n\nChoose an audio file or start a recording to begin.',
    'بدون ترجمه، اصلاح املا یا بازنویسی خودکار.': 'No translation, spelling correction, or automatic rewriting.',
    'کپی': 'Copy', 'ذخیره متن': 'Save text', 'تبدیل دوباره': 'Transcribe again',
    'همین فایل را با زبان و مدل انتخاب‌شده دوباره پردازش کنید.': 'Transcribe this file again with the selected speech language and model.',
    'آماده برای شنیدن؛ فایل یا میکروفون را انتخاب کنید.': 'Ready when you are. Choose an audio file or start recording.',
    'توقف تبدیل': 'Stop transcription', 'کلمات شما، همیشه در دسترس': 'YOUR WORDS, ALWAYS WITH YOU',
    'تاریخچه و مقایسه': 'History & comparison',
    'روی هر نتیجه دوبارکلیک کنید تا متن خام و آمار پردازش نمایش داده شود.': 'Double-click a result to see its original transcript and processing statistics.',
    'فایل / ضبط': 'File / recording', 'مدت صوت': 'Audio duration', 'زمان تبدیل': 'Processing time',
    'تاریخ': 'Date', 'بازخوانی': 'Refresh', 'پوشه متن‌ها و ضبط‌ها': 'Open recordings & transcripts',
    'مرز زبان را بردارید': 'BEYOND LANGUAGE BARRIERS', 'به زبان خودتان.': 'In your own language.',
    'زبان را انتخاب کنید، مدل مناسب را دریافت کنید و آفلاین بنویسید.': 'Choose a language. Get the right model. Transcribe offline.',
    'زبان موردنظر': 'Speech language', 'افزودن مدل محلی': 'Add local model',
    'فیلتر زبان کتابخانه': 'Model library speech language',
    'مدل‌های آذربایجانی این بخش، مخصوص گونه رایج در ایران هستند.': 'These Azerbaijani models are tailored to the variety spoken in Iran.',
    'مدل‌های اختصاصی برای آذربایجانی رایج در ایران؛ به زبان خودتان و با خط اصلی مدل.': 'Dedicated models for Iranian Azerbaijani, preserving the original model spelling.',
    'این مدل‌های چندزبانه روی CPU اجرا می‌شوند. با تغییر زبان، مدل دانلودشده دوباره دریافت نمی‌شود؛ دقت به زبان و کیفیت صدا بستگی دارد.': 'These multilingual models run on CPU. Download once and reuse across languages. Accuracy varies with language and audio quality.',
    'مدل‌ها یک بار دانلود می‌شوند. پردازش فایل‌ها و ضبط‌های شما همیشه روی همین دستگاه انجام می‌شود.': 'Download a model once. Your audio files and recordings are always processed on this device.',
    'اختصاصی آذربایجانی جنوبی · CPU': 'Dedicated South Azerbaijani model · CPU',
    'کم‌حجم؛ مناسب شروع و بررسی سرعت · دانلود مشترک · CPU INT8': 'Compact. Great for a first try and speed checks · Shared download · CPU INT8',
    'تعادل حجم و سرعت · یک دانلود برای چند زبان · CPU INT8': 'Balanced size and speed · One download for multiple languages · CPU INT8',
    'پیشنهاد برای آزمون دقت فارسی؛ پردازش طولانی‌تر · دانلود مشترک · CPU INT8': 'A good candidate for Persian accuracy tests; slower processing · Shared download · CPU INT8',
    'یک دانلود برای همه زبان‌های عمومی · CPU int8': 'One download for all general languages · CPU int8',
    'آماده دریافت': 'Ready to download', 'دانلود مدل': 'Download model',
    'توقف موقت': 'Pause', 'لغو دانلود': 'Cancel download', 'استفاده از مدل': 'Use model',
    'جزئیات مدل و مجوزها': 'Model details & licenses',
    'مدل آذربایجانی جنوبی · مؤسسه Kartal Ol': 'South Azerbaijani model · Kartal Ol Foundation',
    'مشاهده منبع و شرایط مدل': 'View model source & terms',
    'آماده‌سازی دانلود': 'Preparing download', 'در حال دانلود': 'Downloading',
    'متوقف موقت؛ برای ادامه آماده است': 'Paused. Ready to resume.',
    'بررسی صحت فایل‌ها': 'Verifying files', 'آماده استفاده آفلاین': 'Ready for offline use',
    'دانلود لغو شد': 'Download cancelled', 'دانلود کامل نشد': 'Download incomplete',
    'نیازی به دانلود دوباره نیست': 'No need to download again', 'ادامه دانلود': 'Resume download',
    'اتصال و فضای دیسک را بررسی کنید؛ امکان تلاش دوباره وجود دارد.': 'Check your connection and disk space, then try again.',
    'مدل آماده است؛ فایل صوتی را انتخاب کنید یا ضبط را شروع کنید.': 'Model ready. Choose an audio file or start recording.',
    'انتخاب پوشه مدل یا پوشه مدل‌های نسخه قبلی': 'Choose a model folder or the previous app model directory',
    'میکروفون پیدا نشد': 'No microphone found', 'میکروفون در دسترس نیست': 'Microphone unavailable',
    'انتخاب ویس': 'Choose an audio file',
    'ابتدا مدل این زبان را دریافت کنید یا پوشه مدل محلی را معرفی کنید.': 'Get a model for this speech language first, or add a local model folder.',
    'یک فایل WAV، MP3، M4A یا OGG معتبر انتخاب کنید.': 'Choose a valid WAV, MP3, M4A, or OGG file.',
    'در حال پایان ضبط…': 'Finishing recording…', 'آماده‌سازی میکروفون…': 'Preparing microphone…',
    'پایان ضبط و تبدیل': 'Stop & transcribe',
    'ضبط انجام نشد؛ میکروفون و اجازه دسترسی در تنظیمات ویندوز را بررسی کنید.': 'Recording failed. Check your microphone and Windows microphone permissions.',
    'در حال آماده‌سازی میکروفون؛ پس از فعال‌شدن دکمه پایان ضبط، صحبت کنید.': 'Preparing microphone. Speak when the Stop & transcribe button becomes available.',
    'آماده‌سازی': 'Preparing', 'خواندن صوت': 'Reading audio', 'بارگذاری مدل': 'Loading model',
    'تشخیص گفتار': 'Transcribing', 'ذخیره نتیجه': 'Saving result', 'خطا': 'Error',
    'تبدیل متوقف شد؛ می‌توانید فایل یا مدل دیگری انتخاب کنید.': 'Transcription stopped. You can choose another file or model.',
    'تبدیل تمام شد؛ متن و گزارش خودکار ذخیره شدند.': 'Done. Your transcript and processing report have been saved.',
    'تبدیل کامل نشد.': 'Transcription did not finish.',
    'تبدیل ناموفق بود؛ فایل گزارش برای عیب‌یابی نگه داشته شد.': 'Transcription failed. A diagnostic log has been kept.',
    'ذخیره متن خام': 'Save original transcript',
    'نتیجه ذخیره‌شده از تاریخچه نمایش داده شد.': 'Showing a saved result from your history.',
    'نیاز به بررسی': 'Something needs attention', 'درباره Voxriva': 'About Voxriva',
    'بازکردن مجوزها': 'Open licenses', 'بستن': 'Close',
    'در حال توقف ایمن دانلود؛ چند لحظه دیگر دوباره برنامه را ببندید.': 'Stopping the download safely. Please close the app again in a moment.',
    'Voxriva — استودیوی گفتار آفلاین': 'Voxriva — Offline speech studio',
    'نمودار سطح صدای میکروفون': 'Microphone level',
    'برنامه متن‌باز است؛ مجوز کد اختصاصی برنامه MIT است.': 'Voxriva is open source. Its application code is licensed under MIT.',
    'توسعه‌دهنده برنامه': 'Application developer',
    'مدل‌های آذربایجانی جنوبی: مؤسسه Kartal Ol': 'South Azerbaijani models: Kartal Ol Foundation',
    'طبق اعلام توسعه‌دهنده، مجوز مدل‌های آذربایجانی MIT است.': 'The developer reports that the Azerbaijani models are licensed under MIT.',
    'اعلان‌ها و مجوز هر مدل در کتابخانه و اسناد همراه حفظ شده‌اند.': 'Model notices and licenses are retained in the library and accompanying documents.',
    'این برنامه از کتابخانه‌های Qt / PySide6 تحت LGPLv3 استفاده می‌کند.': 'This app uses Qt / PySide6 under LGPLv3.',
    'اطلاعیه‌ها، متن مجوزها و منابع متناظر کتابخانه‌ها در پوشه Licenses قرار دارند.': 'Notices, license texts, and corresponding library sources are in the Licenses folder.',
    'حقوق تغییر و جایگزینی این کتابخانه‌ها محفوظ است.': 'Your rights to modify and replace these libraries are preserved.',
    'اینترنت فقط برای دریافت اختیاری مدل‌ها استفاده می‌شود. صوت، ضبط و متن شما به سرویس خارجی ارسال نمی‌شود.': 'Internet access is used only for optional model downloads. Your audio, recordings, and transcripts are never uploaded.',
    'این مدل‌های چندزبانه روی CPU اجرا می‌شوند.': 'These multilingual models run on CPU.',
    'ضبط خیلی کوتاه بود؛ حداقل یک ثانیه صحبت کنید.': 'The recording is too short. Please speak for at least one second.',
    'میکروفون بخشی از صدا را از دست داد؛ ضبط را در سیستم کم‌بارتر تکرار کنید.': 'The microphone dropped some audio. Reduce system load and record again.',
}

EXTRA_EN = {
    'Speech language': ('زبان گفتار', 'Konuşma dili', 'لغة الكلام', 'Nitq dili'),
}

# Populated from the audited speech catalog, including languages added after launch.
from ui_v3_strings import V3_ROWS
EN.update({row[0]: row[1] for row in V3_ROWS})

_speech_titles = {}
_native_speech_titles = {}


def set_language(code):
    global _language
    _language = code if code in dict(UI_LANGUAGES) else 'en'


def current_language():
    return _language


def register_speech_languages(languages):
    for item in languages:
        english = item.get('english_title') or item.get('english') or item.get('name_en') or item['title']
        _speech_titles[item['title']] = english
        _native_speech_titles[item['code']] = item['title']


def _localized(english):
    try:
        from ui_locales import TRANSLATIONS
        return TRANSLATIONS.get(_language, {}).get(english, english)
    except ImportError:
        return english


def _localized_fragments(text):
    for source in ['MIT (developer declaration)', 'CPU processing', 'Multilingual',
                   'Audio:', 'Inference:', 'Total:', 'Log:', 'License:']:
        text = text.replace(source, _localized(source))
    return text


def language_title(item):
    if _language == 'fa':
        return item['title']
    english = item.get('english_title') or item.get('english') or item.get('name_en') or _speech_titles.get(item['title'], item['title'])
    return _localized(english)


def _english(text):
    if text in EN:
        return EN[text]
    if text in _speech_titles:
        return _speech_titles[text]
    patterns = [
        (r'^(\d+) زبان در دسترس$', lambda m: f'{m[1]} languages available'),
        (r'^(\d+) مدل محلی شناسایی شد؛ فایل‌ها جابه‌جا یا دوباره دانلود نمی‌شوند\.$', lambda m: f'{m[1]} local models found. No files are moved or downloaded again.'),
        (r'^در حال ضبط  ·  (.+)  ·  برای تبدیل، پایان ضبط را بزنید\.$', lambda m: f'Recording  ·  {m[1]}  ·  Stop recording to transcribe.'),
        (r'^حدود (.+) باقی‌مانده$', lambda m: f'About {m[1]} remaining'),
        (r'^(.+) · بخش (\d+) از (\d+)$', lambda m: f'{_english(m[1])} · Part {m[2]} of {m[3]}'),
        (r'^(.+)  ·  (\d+) ثانیه گذشته است  ·  (.+)$', lambda m: f'{_english(m[1])}  ·  {m[2]}s elapsed  ·  {m[3]}'),
        (r'^پیشرفت دانلود (.+)$', lambda m: f'Download progress: {_english(m[1])}'),
    ]
    for pattern, replace in patterns:
        match = re.match(pattern, text)
        if match:
            return replace(match)
    if '  ·  ' in text:
        return '  ·  '.join(_english(part) for part in text.split('  ·  '))
    if '\n' in text:
        return '\n'.join(_english(part) for part in text.split('\n'))
    replacements = {
        ' · چندزبانه': ' · Multilingual', 'MIT (اعلام توسعه‌دهنده)': 'MIT (developer declaration)',
        'مجوز: ': 'License: ', 'پردازش روی CPU': 'CPU processing',
        'صوت: ': 'Audio: ', 'تشخیص: ': 'Inference: ', 'کل: ': 'Total: ', ' ثانیه': 's',
        'گزارش: ': 'Log: ',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def tr(text):
    text = str(text)
    if _language == 'fa':
        return text
    if text in EN:
        return _localized(EN[text])
    match = re.match(r'^(\d+) زبان در دسترس$', text)
    if match:
        return _localized('{count} languages available').format(count=match[1])
    match = re.match(r'^(\d+) مدل محلی شناسایی شد؛ فایل‌ها جابه‌جا یا دوباره دانلود نمی‌شوند\.$', text)
    if match:
        return _localized('{count} local models found. No files are moved or downloaded again.').format(count=match[1])
    match = re.match(r'^در حال ضبط  ·  (.+)  ·  برای تبدیل، پایان ضبط را بزنید\.$', text)
    if match:
        return _localized('Recording · {time} · Stop recording to transcribe.').format(time=match[1])
    match = re.match(r'^حدود (.+) باقی‌مانده$', text)
    if match:
        return _localized('About {time} remaining').format(time=match[1])
    match = re.match(r'^(.+) · بخش (\d+) از (\d+)$', text)
    if match:
        return tr(match[1]) + ' · ' + _localized('Part {index} of {total}').format(index=match[2], total=match[3])
    match = re.match(r'^(.+)  ·  (\d+) ثانیه گذشته است  ·  (.+)$', text)
    if match:
        return tr(match[1]) + '  ·  ' + _localized('{seconds}s elapsed').format(seconds=match[2]) + '  ·  ' + match[3]
    match = re.match(r'^پیشرفت دانلود (.+)$', text)
    if match:
        return _localized('Download progress: {model}').format(model=tr(match[1]))
    match = re.match(r'^مجوز: (.+)  ·  پردازش روی CPU$', text)
    if match:
        return _localized('License: {license} · CPU processing').format(license=_localized(_english(match[1])))
    if '  ·  ' in text:
        return '  ·  '.join(tr(part) for part in text.split('  ·  '))
    if '\n' in text:
        return '\n'.join(tr(part) for part in text.split('\n'))
    english = _english(text)
    if english in EN.values() or english in _speech_titles.values():
        return _localized(english)
    if '  ·  ' in english:
        return '  ·  '.join(_localized(part) for part in english.split('  ·  '))
    return _localized_fragments(_localized(english))
