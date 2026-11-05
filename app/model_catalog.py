"""Curated, immutable model catalog and local cache discovery. No network on import."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

AZB_REPO = 'Kartal-Ol/ASR-AZB'
AZB_REVISION = 'ca9890cd78fb181633a61f4b8a71a750acdcfdf4'
AZB_FILES = ['added_tokens.json', 'config.json', 'generation_config.json', 'merges.txt',
             'model.safetensors', 'normalizer.json', 'preprocessor_config.json',
             'special_tokens_map.json', 'tokenizer_config.json', 'vocab.json']
CT2_FILES = ['config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt']

# Official Whisper language names, filtered against the pinned Tiny tokenizer.
# General az is intentionally excluded: dedicated azb models handle Iranian Azerbaijani.
# Source: https://raw.githubusercontent.com/openai/whisper/86098128c0b4f24f0e2aa2994de830614b474227/whisper/tokenizer.py
LANGUAGES = [
    {'code': code, 'title': title, 'english_title': english, 'whisper_code': whisper_code}
    for code, title, english, whisper_code in [
        ('azb', 'آذربایجانی ایران', 'Iranian Azerbaijani', None),
        ('fa', 'فارسی ایران', 'Persian (Iran)', 'fa'),
        ('tr', 'ترکی استانبولی', 'Turkish', 'tr'),
        ('en', 'انگلیسی', 'English', 'en'),
        ('ar', 'عربی', 'Arabic', 'ar'),
        ('de', 'آلمانی', 'German', 'de'),
        ('fr', 'فرانسوی', 'French', 'fr'),
        ('es', 'اسپانیایی', 'Spanish', 'es'),
        ('ru', 'روسی', 'Russian', 'ru'),
        ('it', 'ایتالیایی', 'Italian', 'it'),
        ('pt', 'پرتغالی', 'Portuguese', 'pt'),
        ('nl', 'هلندی', 'Dutch', 'nl'),
        ('hi', 'هندی', 'Hindi', 'hi'),
        ('ur', 'اردو', 'Urdu', 'ur'),
        ('zh', 'چینی', 'Chinese', 'zh'),
        ('ja', 'ژاپنی', 'Japanese', 'ja'),
        ('ko', 'کره\u200cای', 'Korean', 'ko'),
        ('uk', 'اوکراینی', 'Ukrainian', 'uk'),
        ('pl', 'لهستانی', 'Polish', 'pl'),
        ('sv', 'سوئدی', 'Swedish', 'sv'),
        ('el', 'یونانی', 'Greek', 'el'),
        ('he', 'عبری', 'Hebrew', 'he'),
        ('af', 'آفریکانس', 'Afrikaans', 'af'),
        ('sq', 'آلبانیایی', 'Albanian', 'sq'),
        ('am', 'امهری', 'Amharic', 'am'),
        ('hy', 'ارمنی', 'Armenian', 'hy'),
        ('as', 'آسامی', 'Assamese', 'as'),
        ('ba', 'باشقیری', 'Bashkir', 'ba'),
        ('eu', 'باسکی', 'Basque', 'eu'),
        ('be', 'بلاروسی', 'Belarusian', 'be'),
        ('bn', 'بنگالی', 'Bengali', 'bn'),
        ('bs', 'بوسنیایی', 'Bosnian', 'bs'),
        ('br', 'برتونی', 'Breton', 'br'),
        ('bg', 'بلغاری', 'Bulgarian', 'bg'),
        ('ca', 'کاتالان', 'Catalan', 'ca'),
        ('hr', 'کرواتی', 'Croatian', 'hr'),
        ('cs', 'چکی', 'Czech', 'cs'),
        ('da', 'دانمارکی', 'Danish', 'da'),
        ('et', 'استونیایی', 'Estonian', 'et'),
        ('fo', 'فارویی', 'Faroese', 'fo'),
        ('fi', 'فنلاندی', 'Finnish', 'fi'),
        ('gl', 'گالیسیایی', 'Galician', 'gl'),
        ('ka', 'گرجی', 'Georgian', 'ka'),
        ('gu', 'گجراتی', 'Gujarati', 'gu'),
        ('ht', 'کریول هائیتی', 'Haitian Creole', 'ht'),
        ('ha', 'هوسا', 'Hausa', 'ha'),
        ('haw', 'هاوایی', 'Hawaiian', 'haw'),
        ('hu', 'مجاری', 'Hungarian', 'hu'),
        ('is', 'ایسلندی', 'Icelandic', 'is'),
        ('id', 'اندونزیایی', 'Indonesian', 'id'),
        ('jw', 'جاوه\u200cای', 'Javanese', 'jw'),
        ('kn', 'کانادا (زبان جنوب هند)', 'Kannada', 'kn'),
        ('kk', 'قزاقی', 'Kazakh', 'kk'),
        ('km', 'خمری', 'Khmer', 'km'),
        ('lo', 'لائوسی', 'Lao', 'lo'),
        ('la', 'لاتین', 'Latin', 'la'),
        ('lv', 'لتونیایی', 'Latvian', 'lv'),
        ('ln', 'لینگالا', 'Lingala', 'ln'),
        ('lt', 'لیتوانیایی', 'Lithuanian', 'lt'),
        ('lb', 'لوگزامبورگی', 'Luxembourgish', 'lb'),
        ('mk', 'مقدونی', 'Macedonian', 'mk'),
        ('mg', 'مالاگاسی', 'Malagasy', 'mg'),
        ('ms', 'مالایی', 'Malay', 'ms'),
        ('ml', 'مالایالم', 'Malayalam', 'ml'),
        ('mt', 'مالتی', 'Maltese', 'mt'),
        ('mi', 'مائوری', 'Maori', 'mi'),
        ('mr', 'مراتی', 'Marathi', 'mr'),
        ('mn', 'مغولی', 'Mongolian', 'mn'),
        ('my', 'برمه\u200cای', 'Myanmar', 'my'),
        ('ne', 'نپالی', 'Nepali', 'ne'),
        ('no', 'نروژی', 'Norwegian', 'no'),
        ('nn', 'نروژی نینورسک', 'Nynorsk', 'nn'),
        ('oc', 'اکسیتان', 'Occitan', 'oc'),
        ('ps', 'پشتو', 'Pashto', 'ps'),
        ('pa', 'پنجابی', 'Punjabi', 'pa'),
        ('ro', 'رومانیایی', 'Romanian', 'ro'),
        ('sa', 'سانسکریت', 'Sanskrit', 'sa'),
        ('sr', 'صربی', 'Serbian', 'sr'),
        ('sn', 'شونا', 'Shona', 'sn'),
        ('sd', 'سندی', 'Sindhi', 'sd'),
        ('si', 'سینهالی', 'Sinhala', 'si'),
        ('sk', 'اسلواکی', 'Slovak', 'sk'),
        ('sl', 'اسلوونیایی', 'Slovenian', 'sl'),
        ('so', 'سومالیایی', 'Somali', 'so'),
        ('su', 'سوندایی', 'Sundanese', 'su'),
        ('sw', 'سواحیلی', 'Swahili', 'sw'),
        ('tl', 'تاگالوگ', 'Tagalog', 'tl'),
        ('tg', 'تاجیکی', 'Tajik', 'tg'),
        ('ta', 'تامیلی', 'Tamil', 'ta'),
        ('tt', 'تاتاری', 'Tatar', 'tt'),
        ('te', 'تلوگو', 'Telugu', 'te'),
        ('th', 'تایلندی', 'Thai', 'th'),
        ('bo', 'تبتی', 'Tibetan', 'bo'),
        ('tk', 'ترکمنی', 'Turkmen', 'tk'),
        ('uz', 'ازبکی', 'Uzbek', 'uz'),
        ('vi', 'ویتنامی', 'Vietnamese', 'vi'),
        ('cy', 'ولزی', 'Welsh', 'cy'),
        ('yi', 'ییدیش', 'Yiddish', 'yi'),
        ('yo', 'یوروبایی', 'Yoruba', 'yo'),
    ]
]


CATALOG = []
for key, title, size, total, weight in [
    ('whisper-base-full', 'AZB · Base Full', '292 MB', 292312046, 290403936),
    ('whisper-base', 'AZB · Base', '292 MB', 292311983, 290403936),
    ('whisper-tiny', 'AZB · Tiny', '153 MB', 152969659, 151061672),
    ('whisper-Small-Farsi', 'AZB · Small Farsi-init', '969 MB', 968903123, 966995080),
]:
    CATALOG.append({'key': key, 'title': title, 'size': size, 'bytes': total,
                    'weight_bytes': weight, 'detail': 'اختصاصی آذربایجانی جنوبی · CPU',
                    'backend': 'transformers', 'repo': AZB_REPO, 'revision': AZB_REVISION,
                    'subfolder': key, 'license': 'MIT (اعلام توسعه‌دهنده)',
                    'url': f'https://huggingface.co/{AZB_REPO}/tree/{AZB_REVISION}/{key}',
                    'license_url': f'https://huggingface.co/{AZB_REPO}',
                    'attribution': 'Kartal Ol Foundation / مؤسسه Kartal Ol — https://github.com/Kartalol',
                    'model_license_basis': 'On 2026-11-03, Fardin Milani reported MIT licensing confirmed directly by the model maintainer, with attribution to Kartal Ol. The pinned upstream snapshot has no separate model LICENSE file; this record does not derive weight rights from the research-code license.',
                    'files': list(AZB_FILES)})

_SHARED = [
    {'name': 'tokenizer.json', 'size': 2203239, 'sha256': 'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab'},
    {'name': 'vocabulary.txt', 'size': 459861, 'sha256': '34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913'},
]
for variant, revision, weight_size, weight_hash, config_size, config_hash, total in [
    ('tiny', 'd90ca5fe260221311c53c58e660288d3deb8d356', 75538270,
     'dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1', 2249,
     'a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8', 78203619),
    ('base', 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66', 145217532,
     'd01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9', 2309,
     '56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a', 147882941),
    ('small', '536b0662742c02347bc0e980a01041f333bce120', 483546902,
     '3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671', 2370,
     'b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828', 486212372),
]:
    repo = f'Systran/faster-whisper-{variant}'
    CATALOG.append({'key': f'multilingual-{variant}', 'title': f'Whisper {variant.title()} · چندزبانه',
                    'size': f'{total / 1000000:.0f} MB', 'bytes': total,
                    'weight_bytes': weight_size, 'detail': {
                        'tiny': 'کم‌حجم؛ مناسب شروع و بررسی سرعت · دانلود مشترک · CPU INT8',
                        'base': 'تعادل حجم و سرعت · یک دانلود برای چند زبان · CPU INT8',
                        'small': 'پیشنهاد برای آزمون دقت فارسی؛ پردازش طولانی‌تر · دانلود مشترک · CPU INT8'
                    }[variant],
                    'backend': 'faster-whisper', 'repo': repo, 'revision': revision, 'subfolder': '',
                    'license': 'MIT', 'url': f'https://huggingface.co/{repo}',
                    'license_url': 'https://github.com/openai/whisper/blob/main/LICENSE',
                    'attribution': 'Copyright (c) 2022 OpenAI — Whisper. CTranslate2 checkpoint conversion published by SYSTRAN.',
                    'model_license_basis': 'This specific Systran model repository declares MIT in its model card and identifies conversion from OpenAI Whisper. Preserve the original OpenAI MIT notice and SYSTRAN conversion provenance; this does not relicense other application dependencies.',
                    'files': list(CT2_FILES),
                    'artifacts': [{'name': 'config.json', 'size': config_size, 'sha256': config_hash},
                                  {'name': 'model.bin', 'size': weight_size, 'sha256': weight_hash},
                                  *[dict(item) for item in _SHARED]]})


def get_model(key):
    for item in CATALOG:
        if item['key'] == key:
            return item
    raise ValueError('مدل در فهرست مجاز برنامه نیست.')


def models_for_language(code):
    if code not in {item['code'] for item in LANGUAGES}:
        raise ValueError('زبان ناشناخته است.')
    return [item for item in CATALOG if (item['backend'] == 'transformers') == (code == 'azb')]


def data_root():
    override = os.environ.get('VOXRIVA_DATA_DIR') or os.environ.get('AZB_DATA_DIR')
    root = Path(override) if override else Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'.local/share')))/'AZBVoiceStudio'
    root.mkdir(parents=True, exist_ok=True)
    return root


def model_dir(key):
    get_model(key)
    return data_root()/'models'/key


def _safe_file(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in {'.', '..'}:
        raise ValueError('Unsafe model filename')
    return name


def _complete_folder(path, model, managed=False):
    try:
        if not path.is_dir():
            return False
        expected = {x['name']: x['size'] for x in model.get('artifacts', [])}
        for name in model['files']:
            file = path/_safe_file(name)
            if not file.is_file() or file.stat().st_size <= 0:
                return False
            size = expected.get(name)
            if size and file.stat().st_size != size:
                return False
        weight = path/('model.bin' if model['backend'] == 'faster-whisper' else 'model.safetensors')
        if weight.stat().st_size != model['weight_bytes']:
            return False
        config = json.loads((path/'config.json').read_text(encoding='utf-8'))
        if not isinstance(config, dict):
            return False
        if model['backend'] == 'transformers' and config.get('model_type') != 'whisper':
            return False
        if managed:
            marker = json.loads((path/'completed.json').read_text(encoding='utf-8'))
            if not isinstance(marker, dict) or not isinstance(marker.get('files'), list):
                return False
            if marker.get('repo') != model['repo'] or marker.get('revision') != model['revision']:
                return False
            records = {x['name']: x for x in marker.get('files', [])}
            if set(records) != set(model['files']):
                return False
            if any((path/name).stat().st_size != records[name]['size'] for name in model['files']):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _registered_roots():
    try:
        value = json.loads((data_root()/'model-roots.json').read_text(encoding='utf-8'))
        return [Path(x) for x in value if isinstance(x, str)]
    except (OSError, ValueError, TypeError):
        return []


def register_local_root(path):
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('پوشه مدل وجود ندارد.')
    roots = _registered_roots()
    if root not in roots:
        roots.append(root)
    target = data_root()/'model-roots.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps([str(x) for x in roots], ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, target)
    return sum(find_local_model(m['key']) is not None for m in CATALOG)


def _legacy_roots():
    # Relative paths only; importing the catalog never scans a user's personal folders.
    root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    candidates = [root/'_internal/assets/models', root/'assets/models',
                  root/'Portable/_internal/assets/models', root.parent/'AZBVoiceStudio/Portable/_internal/assets/models',
                  root.parent.parent/'AZBVoiceStudio/Portable/_internal/assets/models']
    if not getattr(sys, 'frozen', False):
        outputs = Path(__file__).resolve().parents[2]
        candidates.append(outputs/'south_azerbaijani_asr_test/cache/huggingface/models--Kartal-Ol--ASR-AZB/snapshots'/AZB_REVISION)
    return candidates


def find_local_model(key):
    model = get_model(key)
    managed = model_dir(key)
    if _complete_folder(managed, model, managed=True):
        return managed
    for root in [*_registered_roots(), *_legacy_roots()]:
        for path in [root, root/key, root/model.get('subfolder', '')] if model.get('subfolder') else [root, root/key]:
            if _complete_folder(path, model):
                return path
    return None
