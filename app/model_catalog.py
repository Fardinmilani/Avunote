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
SHERPA_BACKENDS = frozenset({'sherpa-parakeet', 'sherpa-qwen3', 'sherpa-sensevoice', 'sherpa-omnilingual'})

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
                    'family': 'Whisper · Kartal Ol',
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
for variant, revision, weight_size, weight_hash, config_size, config_digest, total in [
    ('tiny', 'd90ca5fe260221311c53c58e660288d3deb8d356', 75538270,
     'dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1', 2249,
     {'sha256': 'a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8'}, 78203619),
    ('base', 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66', 145217532,
     'd01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9', 2309,
     {'sha256': '56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a'}, 147882941),
    ('small', '536b0662742c02347bc0e980a01041f333bce120', 483546902,
     '3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671', 2370,
     {'sha256': 'b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828'}, 486212372),
    ('medium', '08e178d48790749d25932bbc082711ddcfdfbc4f', 1527906378,
     '9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae', 2257,
     {'git_sha1': '242aa06a480a7b5509375c645097e87af5136774'}, 1530571735),
]:
    repo = f'Systran/faster-whisper-{variant}'
    CATALOG.append({'key': f'multilingual-{variant}', 'title': f'Whisper {variant.title()} · چندزبانه',
                    'family': 'OpenAI Whisper',
                    'size': f'{total / 1e9:.2f} GB' if total >= 1e9 else f'{total / 1e6:.0f} MB',
                    'bytes': total,
                    'weight_bytes': weight_size, 'detail': {
                        'tiny': 'کم‌حجم؛ مناسب شروع و بررسی سرعت · دانلود مشترک · CPU INT8',
                        'base': 'تعادل حجم و سرعت · یک دانلود برای چند زبان · CPU INT8',
                        'small': 'پیشنهاد برای آزمون دقت فارسی؛ پردازش طولانی‌تر · دانلود مشترک · CPU INT8',
                        'medium': 'Larger multilingual Whisper model',
                    }[variant],
                    'backend': 'faster-whisper', 'repo': repo, 'revision': revision, 'subfolder': '',
                    'license': 'MIT', 'url': f'https://huggingface.co/{repo}',
                    'license_url': 'https://github.com/openai/whisper/blob/main/LICENSE',
                    'attribution': 'Copyright (c) 2022 OpenAI — Whisper. CTranslate2 checkpoint conversion published by SYSTRAN.',
                    'model_license_basis': 'This specific Systran model repository declares MIT in its model card and identifies conversion from OpenAI Whisper. Preserve the original OpenAI MIT notice and SYSTRAN conversion provenance; this does not relicense other application dependencies.',
                    'files': list(CT2_FILES),
                    'artifacts': [{'name': 'config.json', 'size': config_size, **config_digest},
                                  {'name': 'model.bin', 'size': weight_size, 'sha256': weight_hash},
                                  *[dict(item) for item in _SHARED]]})


def _onnx_model(key, title, family, backend, languages, repo, revision, detail,
                license_name, license_url, attribution, license_basis, artifacts,
                *, automatic_language=False):
    total = sum(item['size'] for item in artifacts)
    size = f'{total / 1_000_000_000:.2f} GB' if total >= 950_000_000 else f'{total / 1_000_000:.0f} MB'
    return {
        'key': key, 'title': title, 'family': family, 'backend': backend,
        'languages': tuple(languages.split()), 'cpu_only': True, 'fixed_decoder': True,
        'automatic_language': automatic_language,
        'size': size, 'bytes': total, 'detail': detail,
        'repo': repo, 'revision': revision, 'subfolder': '',
        'url': f'https://huggingface.co/{repo}/tree/{revision}',
        'license': license_name, 'license_url': license_url,
        'attribution': attribution, 'model_license_basis': license_basis,
        'files': [item['name'] for item in artifacts], 'artifacts': artifacts,
    }


# These INT8 exports run entirely on-device. Published file sizes and Git/LFS
# object hashes are recorded against their immutable Hugging Face commits.
CATALOG.extend([
    _onnx_model(
        'omnilingual-ctc-300m', 'Omnilingual ASR 300M', 'Meta Omnilingual ASR', 'sherpa-omnilingual',
        # Intersection of this app's language choices and Meta's published lang_ids.py.
        # For Iranian Azerbaijani the relevant upstream code is aze_Arab, for Persian
        # fas_Arab and for Chinese cmn_Hans. The CTC export detects language and script.
        'azb fa tr en ar de fr es ru it pt nl hi ur zh ja ko uk pl sv el he af sq am hy as ba eu be bn bs br bg ca '
        'hr cs da et fo fi gl ka gu ht ha haw hu is id jw kn kk km lo la lv ln lt lb mk mg ms ml mt mi mr mn my ne '
        'no oc ps pa ro sr sn sd si sk sl so su sw tl tg ta tt te th bo tk uz vi cy yi yo',
        'csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-int8-2025-11-12',
        '6abf1ece20cd2308bdb7d13cd78ec1c44fa4c094',
        'Broad multilingual recognition · automatic language detection · CPU INT8',
        'Apache 2.0', 'https://huggingface.co/facebook/omniASR-CTC-300M',
        'Meta Platforms, Inc. — omniASR CTC 300M. INT8 ONNX conversion published by the sherpa-onnx project.',
        'The export includes the upstream weight license notice. The Meta code and dataset have separate license terms.',
        [
            {'name': 'model.int8.onnx', 'size': 365352120, 'sha256': 'e7c4e54ee4c4c47829cc6667d5d00ed8ea7bef1dcfeef0fce766f77752a2726c'},
            {'name': 'tokens.txt', 'size': 86423, 'git_sha1': 'f6541787d8060867baa6804f4910ba055cd57bb5'},
            {'name': 'LICENSE', 'size': 581, 'git_sha1': 'f7934c80a1d123053efd4313c5723c55a447416b'},
        ], automatic_language=True,
    ),
    _onnx_model(
        'parakeet-tdt-v3', 'Parakeet TDT 0.6B v3', 'NVIDIA Parakeet', 'sherpa-parakeet',
        'bg hr cs da nl en et fi fr de el hu it lv lt mt pl pt ro sk sl es sv ru uk',
        'csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8',
        '2bda32ec70b097a55adaa07d9a7173915b43cc78',
        '25 European languages · automatic language detection · CPU INT8',
        'CC BY 4.0', 'https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3#licenseterms-of-use',
        'NVIDIA — Parakeet TDT 0.6B v3. INT8 ONNX conversion published by the sherpa-onnx project.',
        'The NVIDIA base checkpoint declares CC BY 4.0. This is its converted and quantized sherpa-onnx export.',
        [
            {'name': 'encoder.int8.onnx', 'size': 652184281, 'sha256': 'acfc2b4456377e15d04f0243af540b7fe7c992f8d898d751cf134c3a55fd2247'},
            {'name': 'decoder.int8.onnx', 'size': 11845275, 'sha256': '179e50c43d1a9de79c8a24149a2f9bac6eb5981823f2a2ed88d655b24248db4e'},
            {'name': 'joiner.int8.onnx', 'size': 6355277, 'sha256': '3164c13fc2821009440d20fcb5fdc78bff28b4db2f8d0f0b329101719c0948b3'},
            {'name': 'tokens.txt', 'size': 93939, 'git_sha1': 'fc43e1c723e262df60b70e1919614417162d1fe2'},
        ], automatic_language=True,
    ),
    _onnx_model(
        'qwen3-asr-06b', 'Qwen3-ASR 0.6B', 'Alibaba Qwen', 'sherpa-qwen3',
        'zh en ar de fr es pt id it ko ru th vi ja tr hi ms nl sv da fi pl cs fa el hu mk ro',
        'csukuangfj2/sherpa-onnx-qwen3-asr-0.6B-int8-2026-03-25',
        '68818b2313fe77bd06f6a7c5068ff3ef59d02b8a',
        'Persian, Turkish, Arabic and more · automatic language detection · CPU INT8',
        'Apache 2.0', 'https://github.com/QwenLM/Qwen3-ASR/blob/main/LICENSE',
        'Alibaba Qwen — Qwen3-ASR-0.6B. INT8 ONNX conversion by Wasser1462, published by sherpa-onnx.',
        'The original Qwen/Qwen3-ASR-0.6B checkpoint declares Apache 2.0. This snapshot records the ONNX conversion provenance in its README.',
        [
            {'name': 'conv_frontend.onnx', 'size': 44148281, 'sha256': 'd22dc4423e0940e49884e903d2ea2f7e5567c14fc1aed97e4e26d6b8f208ef9e'},
            {'name': 'encoder.int8.onnx', 'size': 182491662, 'sha256': '60748d3e6744a57c9c91e1b17424a6c2990567e8adceb0783940c03ed98fa9d9'},
            {'name': 'decoder.int8.onnx', 'size': 755914231, 'sha256': '4f6885be5959ae26af3089d38ee7972c5fafbeeb1cf8d5e76eab6d8b61ca5771'},
            {'name': 'merges.txt', 'remote_prefix': 'tokenizer', 'size': 1671853, 'git_sha1': '31349551d90c7606f325fe0f11bbb8bd5fa0d7c7'},
            {'name': 'tokenizer_config.json', 'remote_prefix': 'tokenizer', 'size': 12487, 'sha256': '4942d005604266809309cabc9f4e9cb89ce855d59b14681fdc0e1cc62ea26c4c'},
            {'name': 'vocab.json', 'remote_prefix': 'tokenizer', 'size': 2776833, 'sha256': 'ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910'},
        ], automatic_language=True,
    ),
    _onnx_model(
        'sensevoice-small', 'SenseVoice Small', 'FunAudioLLM SenseVoice', 'sherpa-sensevoice',
        'zh en ja ko',
        'csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17',
        '2365baeacb507f821a0c8120fcee3d484dba7a07',
        'Mandarin, English, Japanese and Korean · CPU INT8',
        'FunASR Model Open Source License v1.1', 'https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE',
        'FunAudioLLM — SenseVoiceSmall. INT8 ONNX conversion published by the sherpa-onnx project.',
        'The export LICENSE refers to FunASR model terms and the original SenseVoiceSmall model card links to the FunASR Model Open Source License Agreement.',
        [
            {'name': 'model.int8.onnx', 'size': 239233841, 'sha256': 'c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51'},
            {'name': 'tokens.txt', 'size': 315894, 'git_sha1': '2cfc92fc2ff26aaa690b7c01fd96b41109413881'},
            {'name': 'LICENSE', 'size': 71, 'git_sha1': 'b5aafcccf5cfd5f7293c710bd6588dc6544eef2b'},
        ],
    ),
])


def get_model(key):
    for item in CATALOG:
        if item['key'] == key:
            return item
    raise ValueError('مدل در فهرست مجاز برنامه نیست.')


def models_for_language(code):
    if code not in {item['code'] for item in LANGUAGES}:
        raise ValueError('زبان ناشناخته است.')
    general_backend = 'transformers' if code == 'azb' else 'faster-whisper'
    return [item for item in CATALOG if code in item.get('languages', ())
            or ('languages' not in item and item['backend'] == general_backend)]


def data_root():
    # Keep the existing default folder and legacy overrides across the rebrand:
    # recordings, downloaded models, chats and encrypted profile keys stay put.
    override = os.environ.get('AVUNOTE_DATA_DIR') or os.environ.get('VOXRIVA_DATA_DIR') or os.environ.get('AZB_DATA_DIR')
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
        if model['backend'] not in SHERPA_BACKENDS:
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
