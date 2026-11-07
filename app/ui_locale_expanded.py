"""Short interface copy in the additional Avunote locales.

Rows are keyed by the stable English label. Context and interpolation fields
are kept identical to the English source. Unknown diagnostics fall back to
English rather than silently changing the selected interface language.
"""

ADDITIONAL_LANGUAGES = [
    ('es', 'Español'), ('fr', 'Français'), ('de', 'Deutsch'),
    ('pt', 'Português (Brasil)'), ('ru', 'Русский'),
    ('zh', '简体中文'), ('ja', '日本語'),
]

_NEW_ROWS = """
Settings|تنظیمات|Ayarlar|الإعدادات|Parametrlər
Updates|به‌روزرسانی|Güncellemeler|التحديثات|Yeniləmələr
Check for updates|بررسی به‌روزرسانی|Güncellemeleri denetle|التحقق من التحديثات|Yeniləmələri yoxla
Checking for updates…|در حال بررسی به‌روزرسانی…|Güncellemeler denetleniyor…|جارٍ التحقق من التحديثات…|Yeniləmələr yoxlanılır…
You're up to date.|آخرین نسخه نصب است.|En güncel sürüm yüklü.|أحدث إصدار مثبت.|Ən son versiya quraşdırılıb.
Update available|به‌روزرسانی در دسترس است|Güncelleme var|يتوفر تحديث|Yeniləmə var
Download update|دانلود به‌روزرسانی|Güncellemeyi indir|تنزيل التحديث|Yeniləməni endir
Downloading update…|در حال دانلود به‌روزرسانی…|Güncelleme indiriliyor…|جارٍ تنزيل التحديث…|Yeniləmə endirilir…
Restart and install|راه‌اندازی دوباره و نصب|Yeniden başlat ve yükle|إعادة التشغيل والتثبيت|Yenidən başlat və quraşdır
Try again|تلاش دوباره|Tekrar dene|أعد المحاولة|Yenidən cəhd et
Couldn't check for updates.|بررسی به‌روزرسانی انجام نشد.|Güncellemeler denetlenemedi.|تعذر التحقق من التحديثات.|Yeniləmələri yoxlamaq alınmadı.
Couldn't download the update.|دانلود به‌روزرسانی انجام نشد.|Güncelleme indirilemedi.|تعذر تنزيل التحديث.|Yeniləməni endirmək alınmadı.
Download cancelled.|دانلود لغو شد.|İndirme iptal edildi.|أُلغي التنزيل.|Endirmə ləğv edildi.
Update ready to install.|به‌روزرسانی آمادهٔ نصب است.|Güncelleme yüklenmeye hazır.|التحديث جاهز للتثبيت.|Yeniləmə quraşdırılmağa hazırdır.
Update available: {version}|نسخهٔ {version} در دسترس است|Güncelleme var: {version}|يتوفر الإصدار {version}|Yeniləmə var: {version}
Installed: {version}|نسخهٔ نصب‌شده: {version}|Yüklü: {version}|الإصدار المثبت: {version}|Quraşdırılıb: {version}
Download size: {size}|حجم دانلود: {size}|İndirme boyutu: {size}|حجم التنزيل: {size}|Endirmə ölçüsü: {size}
Windows Setup installation required for in-app updates.|برای به‌روزرسانی درون برنامه، نسخهٔ نصبی ویندوز لازم است.|Uygulama içi güncellemeler için Windows kurulumunu kullanın.|تتطلب التحديثات داخل التطبيق تثبيته بمثبت Windows.|Tətbiqdaxili yeniləmələr üçün Windows quraşdırıcısından istifadə edin.
Close the active task before installing the update.|پیش از نصب به‌روزرسانی، کار جاری را تمام کنید.|Güncellemeyi yüklemeden önce etkin işlemi sonlandırın.|أنه المهمة الحالية قبل تثبيت التحديث.|Yeniləməni quraşdırmazdan əvvəl cari əməliyyatı bitirin.
Couldn't start the installer.|نصاب اجرا نشد.|Kurulum başlatılamadı.|تعذر تشغيل المثبت.|Quraşdırıcını başlatmaq alınmadı.
Automatic update checks are off.|بررسی خودکار به‌روزرسانی خاموش است.|Otomatik güncelleme denetimi kapalı.|التحقق التلقائي من التحديثات متوقف.|Avtomatik yeniləmə yoxlaması söndürülüb.
Update is smaller because only changed files are included.|فقط فایل‌های تغییرکرده دانلود می‌شوند.|Yalnızca değişen dosyalar indirilir.|يُنزّل التحديث الملفات المتغيرة فقط.|Yalnız dəyişmiş fayllar endirilir.
Transcript|متن گفتار|Döküm|النص المفرغ|Transkript
Recognition|تشخیص گفتار|Konuşma tanıma|التعرّف على الكلام|Nitqin tanınması
Microphone|میکروفون|Mikrofon|الميكروفون|Mikrofon
Record|ضبط|Kaydet|تسجيل|Səs yaz
Open audio|بازکردن صوت|Ses dosyası aç|فتح ملف صوتي|Audio aç
Ask AI|پرسش از AI|Yapay zekâya sor|اسأل الذكاء الاصطناعي|Süni intellektdən soruş
No transcripts yet|هنوز متنی تبدیل نشده|Henüz döküm yok|لا توجد نصوص مفرغة بعد|Hələ transkript yoxdur
Open transcript|بازکردن متن|Dökümü aç|فتح النص|Transkripti aç
Preferences|ترجیحات|Tercihler|التفضيلات|Seçimlər
Installed|نصب‌شده|Yüklü|مثبت|Quraşdırılıb
Audio input|ورودی صوت|Ses girişi|إدخال الصوت|Səs girişi
No transcript yet|هنوز متنی نیست|Henüz döküm yok|لا يوجد نص بعد|Hələ transkript yoxdur
Choose a model|انتخاب مدل|Model seç|اختر نموذجًا|Model seç
No conversations yet|هنوز گفت‌وگویی نیست|Henüz sohbet yok|لا توجد محادثات بعد|Hələ söhbət yoxdur
Send a message|ارسال پیام|Mesaj gönder|أرسل رسالة|Mesaj göndər
Ask anything|سؤالت را بپرس|Bir soru sor|اطرح أي سؤال|Sual ver
Message actions|کارهای پیام|Mesaj işlemleri|إجراءات الرسالة|Mesaj əməliyyatları
Conversation actions|کارهای گفت‌وگو|Sohbet işlemleri|إجراءات المحادثة|Söhbət əməliyyatları
Add context|افزودن متن مرجع|Bağlam ekle|إضافة سياق|Kontekst əlavə et
New chat|گفت‌وگوی تازه|Yeni sohbet|محادثة جديدة|Yeni söhbət
Chat|گفت‌وگو|Sohbet|محادثة|Söhbət
Connections|اتصال‌ها|Bağlantılar|الاتصالات|Bağlantılar
Another model is downloading.|یک مدل دیگر در حال دانلود است.|Başka bir model indiriliyor.|يُنزّل نموذج آخر الآن.|Başqa model endirilir.
Download a model using the icon in the list.|برای دانلود مدل، روی آیکن آن در فهرست بزنید.|Listede modelin indirme simgesini seçin.|نزّل النموذج من خلال أيقونة التنزيل في القائمة.|Modeli siyahıdakı endirmə nişanından endirin.
Close|بستن|Kapat|إغلاق|Bağla
Cancel download|لغو دانلود|İndirmeyi iptal et|إلغاء التنزيل|Endirməni ləğv et
Larger multilingual Whisper model|مدل چندزبانهٔ بزرگ‌تر Whisper|Daha büyük çok dilli Whisper modeli|نموذج Whisper متعدد اللغات بحجم أكبر|Daha böyük çoxdilli Whisper modeli
Multilingual Whisper with a faster decoder|ویسپر چندزبانه با رمزگشای سریع‌تر|Daha hızlı çözücülü çok dilli Whisper|Whisper متعدد اللغات بفك ترميز أسرع|Daha sürətli dekoderli çoxdilli Whisper
Broad multilingual recognition · automatic language detection · CPU INT8|تشخیص گستردهٔ چندزبانه · تشخیص خودکار زبان · CPU INT8|Geniş dil kapsamı · otomatik dil algılama · CPU INT8|تغطية لغوية واسعة · اكتشاف تلقائي للغة · CPU INT8|Geniş dil dəstəyi · avtomatik dil tanıma · CPU INT8
"""

# Spanish, French, German, Brazilian Portuguese, Russian, Simplified Chinese,
# and Japanese. Longer privacy and error text lives alongside the controls.
_APP_ROWS = """
Settings|Configuración|Paramètres|Einstellungen|Configurações|Настройки|设置|設定
Updates|Actualizaciones|Mises à jour|Updates|Atualizações|Обновления|更新|アップデート
Check for updates|Buscar actualizaciones|Rechercher des mises à jour|Nach Updates suchen|Verificar atualizações|Проверить обновления|检查更新|アップデートを確認
Checking for updates…|Buscando actualizaciones…|Recherche de mises à jour…|Suche nach Updates…|Verificando atualizações…|Проверка обновлений…|正在检查更新…|アップデートを確認中…
You're up to date.|Ya tienes la última versión.|Vous disposez de la dernière version.|Die neueste Version ist installiert.|Você já tem a versão mais recente.|Установлена последняя версия.|已是最新版本。|最新バージョンです。
Update available|Actualización disponible|Mise à jour disponible|Update verfügbar|Atualização disponível|Доступно обновление|有可用更新|アップデートがあります
Download update|Descargar actualización|Télécharger la mise à jour|Update herunterladen|Baixar atualização|Скачать обновление|下载更新|アップデートをダウンロード
Downloading update…|Descargando actualización…|Téléchargement de la mise à jour…|Update wird heruntergeladen…|Baixando atualização…|Загрузка обновления…|正在下载更新…|アップデートをダウンロード中…
Restart and install|Reiniciar e instalar|Redémarrer et installer|Neu starten und installieren|Reiniciar e instalar|Перезапустить и установить|重启并安装|再起動してインストール
Try again|Reintentar|Réessayer|Erneut versuchen|Tentar novamente|Повторить|重试|再試行
Couldn't check for updates.|No se pudo buscar actualizaciones.|Impossible de rechercher les mises à jour.|Die Suche nach Updates ist fehlgeschlagen.|Não foi possível verificar atualizações.|Не удалось проверить обновления.|无法检查更新。|アップデートを確認できませんでした。
Couldn't download the update.|No se pudo descargar la actualización.|Impossible de télécharger la mise à jour.|Das Update konnte nicht heruntergeladen werden.|Não foi possível baixar a atualização.|Не удалось скачать обновление.|无法下载更新。|アップデートをダウンロードできませんでした。
Download cancelled.|Descarga cancelada.|Téléchargement annulé.|Download abgebrochen.|Download cancelado.|Загрузка отменена.|下载已取消。|ダウンロードをキャンセルしました。
Update ready to install.|Actualización lista para instalar.|La mise à jour est prête à être installée.|Das Update kann installiert werden.|Atualização pronta para instalar.|Обновление готово к установке.|更新已准备就绪。|アップデートをインストールできます。
Update available: {version}|Actualización disponible: {version}|Mise à jour disponible : {version}|Update verfügbar: {version}|Atualização disponível: {version}|Доступно обновление: {version}|有可用更新：{version}|アップデートあり：{version}
Installed: {version}|Instalada: {version}|Version installée : {version}|Installiert: {version}|Instalada: {version}|Установлено: {version}|已安装：{version}|インストール済み：{version}
Download size: {size}|Tamaño de descarga: {size}|Taille du téléchargement : {size}|Downloadgröße: {size}|Tamanho do download: {size}|Размер загрузки: {size}|下载大小：{size}|ダウンロードサイズ：{size}
Windows Setup installation required for in-app updates.|Para actualizar desde la aplicación, instálala con el instalador de Windows.|Pour mettre à jour l’application depuis son interface, utilisez le programme d’installation Windows.|Updates in der App setzen die Installation mit dem Windows-Setup voraus.|Para atualizar pelo aplicativo, use o instalador do Windows.|Для обновления из приложения нужна установка через установщик Windows.|要在应用内更新，请使用 Windows 安装程序安装此应用。|アプリ内で更新するには Windows インストーラーでのインストールが必要です。
Close the active task before installing the update.|Termina la tarea activa antes de instalar la actualización.|Terminez la tâche en cours avant d’installer la mise à jour.|Beende die laufende Aufgabe vor der Installation des Updates.|Finalize a tarefa em andamento antes de instalar a atualização.|Завершите текущую задачу перед установкой обновления.|请先结束当前任务，再安装更新。|アップデートをインストールする前に、処理中の作業を終了してください。
Couldn't start the installer.|No se pudo iniciar el instalador.|Impossible de lancer le programme d’installation.|Das Installationsprogramm konnte nicht gestartet werden.|Não foi possível iniciar o instalador.|Не удалось запустить установщик.|无法启动安装程序。|インストーラーを起動できませんでした。
Automatic update checks are off.|La búsqueda automática de actualizaciones está desactivada.|La recherche automatique de mises à jour est désactivée.|Die automatische Update-Suche ist deaktiviert.|A verificação automática de atualizações está desativada.|Автопроверка обновлений отключена.|自动检查更新已关闭。|アップデートの自動確認はオフです。
Update is smaller because only changed files are included.|Solo se descargan los archivos que han cambiado.|Seuls les fichiers modifiés sont téléchargés.|Nur geänderte Dateien werden heruntergeladen.|Somente os arquivos alterados serão baixados.|Скачиваются только изменённые файлы.|仅下载有改动的文件。|変更されたファイルのみダウンロードします。
Transcript|Transcripción|Transcription|Transkript|Transcrição|Расшифровка|转写文本|文字起こし
Recognition|Reconocimiento de voz|Reconnaissance vocale|Spracherkennung|Reconhecimento de fala|Распознавание речи|语音识别|音声認識
Microphone|Micrófono|Microphone|Mikrofon|Microfone|Микрофон|麦克风|マイク
Record|Grabar|Enregistrer|Aufnehmen|Gravar|Записать|录音|録音
Open audio|Abrir audio|Ouvrir un fichier audio|Audiodatei öffnen|Abrir áudio|Открыть аудио|打开音频|音声を開く
Ask AI|Preguntar a la IA|Demander à l’IA|KI fragen|Perguntar à IA|Спросить ИИ|询问 AI|AI に質問
No transcripts yet|Aún no hay transcripciones|Aucune transcription pour le moment|Noch keine Transkripte|Ainda não há transcrições|Расшифровок пока нет|暂无转写文本|文字起こしはまだありません
Open transcript|Abrir transcripción|Ouvrir la transcription|Transkript öffnen|Abrir transcrição|Открыть расшифровку|打开转写文本|文字起こしを開く
Preferences|Preferencias|Préférences|Voreinstellungen|Preferências|Параметры|偏好设置|環境設定
Installed|Instalado|Installé|Installiert|Instalado|Установлено|已安装|インストール済み
Audio input|Entrada de audio|Entrée audio|Audioeingang|Entrada de áudio|Аудиовход|音频输入|音声入力
No transcript yet|Aún no hay transcripción|Aucune transcription pour le moment|Noch kein Transkript|Ainda não há transcrição|Расшифровки пока нет|暂无转写文本|文字起こしはまだありません
Choose a model|Elegir un modelo|Choisir un modèle|Modell auswählen|Escolher um modelo|Выбрать модель|选择模型|モデルを選択
No conversations yet|Aún no hay conversaciones|Aucune conversation pour le moment|Noch keine Unterhaltungen|Ainda não há conversas|Бесед пока нет|暂无对话|会話はまだありません
Send a message|Enviar un mensaje|Envoyer un message|Nachricht senden|Enviar uma mensagem|Отправить сообщение|发送消息|メッセージを送信
Ask anything|Escribe tu pregunta|Posez votre question|Stelle eine Frage|Faça uma pergunta|Задайте вопрос|输入问题|質問を入力
Message actions|Acciones del mensaje|Actions du message|Nachrichtenaktionen|Ações da mensagem|Действия с сообщением|消息操作|メッセージ操作
Conversation actions|Acciones de la conversación|Actions de la conversation|Unterhaltungsaktionen|Ações da conversa|Действия с беседой|对话操作|会話の操作
Add context|Añadir contexto|Ajouter du contexte|Kontext hinzufügen|Adicionar contexto|Добавить контекст|添加上下文|参照テキストを追加
New chat|Nueva conversación|Nouvelle conversation|Neuer Chat|Nova conversa|Новая беседа|新对话|新しいチャット
Chat|Conversación|Discussion|Chat|Conversa|Беседа|对话|チャット
Connections|Conexiones|Connexions|Verbindungen|Conexões|Подключения|连接|接続
Another model is downloading.|Se está descargando otro modelo.|Un autre modèle est en cours de téléchargement.|Ein anderes Modell wird heruntergeladen.|Outro modelo está sendo baixado.|Загружается другая модель.|正在下载其他模型。|別のモデルをダウンロード中です。
Download a model using the icon in the list.|Descarga un modelo con su icono en la lista.|Téléchargez un modèle avec son icône dans la liste.|Lade ein Modell über sein Download-Symbol in der Liste herunter.|Baixe um modelo pelo ícone na lista.|Скачайте модель с помощью значка в списке.|点击列表中的下载图标以获取模型。|一覧のダウンロードアイコンからモデルを入手してください。
Larger multilingual Whisper model|Modelo Whisper multilingüe de mayor tamaño|Modèle Whisper multilingue de plus grande taille|Größeres mehrsprachiges Whisper-Modell|Modelo Whisper multilíngue de maior porte|Более крупная многоязычная модель Whisper|更大的多语言 Whisper 模型|大型の多言語 Whisper モデル
Multilingual Whisper with a faster decoder|Whisper multilingüe con un decodificador más rápido|Whisper multilingue à décodage accéléré|Mehrsprachiges Whisper mit schnellerem Decoder|Whisper multilíngue com decodificador mais rápido|Многоязычная модель Whisper с ускоренным декодером|采用更快解码器的多语言 Whisper|高速デコーダー搭載の多言語 Whisper
Broad multilingual recognition · automatic language detection · CPU INT8|Amplia cobertura de idiomas · detección automática · CPU INT8|Nombreuses langues · détection automatique · CPU INT8|Breite Sprachabdeckung · automatische Spracherkennung · CPU INT8|Ampla cobertura de idiomas · detecção automática · CPU INT8|Широкий охват языков · автоопределение языка · CPU INT8|广泛的多语言识别 · 自动检测语言 · CPU INT8|幅広い言語に対応 · 言語の自動検出 · CPU INT8
"""

_CORE_ROWS = """
Speech studio|Estudio de voz|Studio vocal|Sprachstudio|Estúdio de voz|Студия речи|语音工作台|音声スタジオ
Model library|Biblioteca de modelos|Bibliothèque de modèles|Modellbibliothek|Biblioteca de modelos|Библиотека моделей|模型库|モデルライブラリ
History|Historial|Historique|Verlauf|Histórico|История|历史记录|履歴
History & comparison|Historial y comparación|Historique et comparaison|Verlauf und Vergleich|Histórico e comparação|История и сравнение|历史与对比|履歴と比較
AI chat|Chat con IA|Discussion IA|KI-Chat|Chat com IA|Чат с ИИ|AI 对话|AI チャット
AI workspace|Chat con IA|Espace IA|KI-Arbeitsbereich|Área de IA|Рабочая область ИИ|AI 工作区|AI ワークスペース
Interface language|Idioma de la interfaz|Langue de l’interface|Oberflächensprache|Idioma da interface|Язык интерфейса|界面语言|表示言語
Appearance|Apariencia|Apparence|Darstellung|Aparência|Оформление|外观|外観
System theme|Tema del sistema|Thème du système|Systemdesign|Tema do sistema|Системная тема|跟随系统|システムに合わせる
Light|Claro|Clair|Hell|Claro|Светлая|浅色|ライト
Dark|Oscuro|Sombre|Dunkel|Escuro|Тёмная|深色|ダーク
About Avunote|Acerca de Avunote|À propos d’Avunote|Über Avunote|Sobre o Avunote|Об Avunote|关于 Avunote|Avunote について
About & licenses|Acerca de y licencias|À propos et licences|Über und Lizenzen|Sobre e licenças|О программе и лицензии|关于和许可证|情報とライセンス
Open licenses|Abrir licencias|Ouvrir les licences|Lizenzen öffnen|Abrir licenças|Открыть лицензии|打开许可证|ライセンスを開く
Private & offline|Privado y sin conexión|Privé et hors ligne|Privat und offline|Privado e offline|Приватно и офлайн|私密且离线|プライベート・オフライン
On your device|En tu dispositivo|Sur votre appareil|Auf deinem Gerät|No seu dispositivo|На вашем устройстве|在你的设备上|このデバイス上
Speech language|Idioma del audio|Langue parlée|Gesprochene Sprache|Idioma do áudio|Язык речи|语音语言|音声の言語
Model library speech language|Idioma de los modelos|Langue des modèles|Sprache der Modelle|Idioma dos modelos|Язык моделей|模型语言|モデルの言語
Model|Modelo|Modèle|Modell|Modelo|Модель|模型|モデル
Speech recognition model|Modelo de reconocimiento de voz|Modèle de reconnaissance vocale|Spracherkennungsmodell|Modelo de reconhecimento de fala|Модель распознавания речи|语音识别模型|音声認識モデル
No model installed|No hay modelos instalados|Aucun modèle installé|Kein Modell installiert|Nenhum modelo instalado|Нет установленных моделей|尚未安装模型|モデルがインストールされていません
Not downloaded|Sin descargar|Non téléchargé|Nicht heruntergeladen|Não baixado|Не скачана|未下载|未ダウンロード
Get model|Obtener modelo|Obtenir un modèle|Modell beziehen|Obter modelo|Получить модель|获取模型|モデルを入手
Manage models|Gestionar modelos|Gérer les modèles|Modelle verwalten|Gerenciar modelos|Управление моделями|管理模型|モデルを管理
Download model|Descargar modelo|Télécharger le modèle|Modell herunterladen|Baixar modelo|Скачать модель|下载模型|モデルをダウンロード
Download|Descargar|Télécharger|Herunterladen|Baixar|Скачать|下载|ダウンロード
Resume download|Reanudar descarga|Reprendre le téléchargement|Download fortsetzen|Retomar download|Возобновить загрузку|继续下载|ダウンロードを再開
Pause|Pausar|Mettre en pause|Pausieren|Pausar|Приостановить|暂停|一時停止
Cancel download|Cancelar descarga|Annuler le téléchargement|Download abbrechen|Cancelar download|Отменить загрузку|取消下载|ダウンロードをキャンセル
Use model|Usar modelo|Utiliser le modèle|Modell verwenden|Usar modelo|Использовать модель|使用模型|モデルを使用
Model details & licenses|Detalles y licencias del modelo|Détails et licences du modèle|Modelldetails und Lizenzen|Detalhes e licenças do modelo|Сведения и лицензии модели|模型详情和许可证|モデルの詳細とライセンス
View model source & terms|Ver origen y condiciones|Voir la source et les conditions|Quelle und Bedingungen anzeigen|Ver origem e condições|Источник и условия модели|查看模型来源和条款|モデルの配布元と利用条件
Add local model|Añadir modelo local|Ajouter un modèle local|Lokales Modell hinzufügen|Adicionar modelo local|Добавить локальную модель|添加本地模型|ローカルモデルを追加
Choose a model folder or the previous app model directory|Selecciona la carpeta de un modelo|Choisissez le dossier d’un modèle|Modellordner auswählen|Selecione a pasta de um modelo|Выберите папку с моделью|选择模型文件夹|モデルフォルダーを選択
Model ready. Transcription works offline.|Modelo listo para transcribir sin conexión.|Le modèle est prêt pour la transcription hors ligne.|Modell bereit für die Offline-Transkription.|Modelo pronto para transcrever offline.|Модель готова к распознаванию офлайн.|模型已就绪，可以离线转写。|モデルの準備ができました。オフラインで文字起こしできます。
Checking model availability.|Comprobando modelos…|Vérification des modèles…|Modellverfügbarkeit wird geprüft…|Verificando modelos…|Проверка моделей…|正在检查模型…|モデルを確認中…
Ready to download|Lista para descargar|Prêt au téléchargement|Zum Download bereit|Pronto para baixar|Готова к загрузке|可下载|ダウンロードできます
Preparing download|Preparando descarga|Préparation du téléchargement|Download wird vorbereitet|Preparando download|Подготовка к загрузке|准备下载|ダウンロードを準備中
Downloading|Descargando|Téléchargement|Wird heruntergeladen|Baixando|Загрузка|正在下载|ダウンロード中
Paused. Ready to resume.|En pausa. Puedes reanudarla.|En pause. Le téléchargement peut reprendre.|Pausiert. Kann fortgesetzt werden.|Em pausa. Você pode retomar.|На паузе. Загрузку можно продолжить.|已暂停，可以继续。|一時停止中。再開できます。
Verifying files|Verificando archivos|Vérification des fichiers|Dateien werden geprüft|Verificando arquivos|Проверка файлов|正在验证文件|ファイルを検証中
Ready for offline use|Lista para usar sin conexión|Prêt pour l’usage hors ligne|Offline einsatzbereit|Pronto para usar offline|Готова к работе офлайн|可离线使用|オフラインで使用可能
Download cancelled|Descarga cancelada|Téléchargement annulé|Download abgebrochen|Download cancelado|Загрузка отменена|下载已取消|ダウンロードをキャンセルしました
Download incomplete|Descarga incompleta|Téléchargement incomplet|Download unvollständig|Download incompleto|Загрузка не завершена|下载未完成|ダウンロードが完了していません
No need to download again|No hace falta descargar de nuevo|Inutile de télécharger à nouveau|Kein erneuter Download nötig|Não é preciso baixar novamente|Повторная загрузка не нужна|无需再次下载|再ダウンロードは不要です
Processing options|Opciones de procesamiento|Options de traitement|Verarbeitungsoptionen|Opções de processamento|Параметры обработки|处理选项|処理オプション
Processing mode|Modo de procesamiento|Mode de traitement|Verarbeitungsmodus|Modo de processamento|Режим обработки|处理模式|処理モード
Processing quality|Calidad del procesamiento|Qualité du traitement|Verarbeitungsqualität|Qualidade do processamento|Качество обработки|处理质量|処理品質
Processing device|Dispositivo de procesamiento|Appareil de traitement|Verarbeitungsgerät|Dispositivo de processamento|Устройство обработки|处理设备|処理デバイス
Audio chunk duration|Duración de segmento|Durée des segments audio|Dauer der Audioabschnitte|Duração do trecho de áudio|Длительность фрагмента|音频片段时长|音声区間の長さ
Higher accuracy|Mayor precisión|Plus précis|Höhere Genauigkeit|Maior precisão|Точнее|精度优先|精度優先
Faster|Más rápido|Plus rapide|Schneller|Mais rápido|Быстрее|速度优先|速度優先
Auto · CPU fallback|Automático · CPU como respaldo|Auto · CPU en secours|Auto · CPU als Reserve|Automático · CPU como alternativa|Авто · резервный ЦП|自动 · 可回退到 CPU|自動 · CPU に切り替え
NPU · CPU if unsupported|NPU · CPU si no es compatible|NPU · CPU si non pris en charge|NPU · CPU bei fehlender Unterstützung|NPU · CPU se incompatível|NPU · ЦП при несовместимости|NPU · 不支持时使用 CPU|NPU · 非対応時は CPU
Record your voice|Grabar tu voz|Enregistrer votre voix|Stimme aufnehmen|Gravar sua voz|Записать голос|录制语音|声を録音
Select microphone|Seleccionar micrófono|Sélectionner un microphone|Mikrofon auswählen|Selecionar microfone|Выбрать микрофон|选择麦克风|マイクを選択
Refresh microphones|Actualizar micrófonos|Actualiser les microphones|Mikrofone aktualisieren|Atualizar microfones|Обновить список микрофонов|刷新麦克风列表|マイク一覧を更新
No microphone found|No se detectó ningún micrófono|Aucun microphone détecté|Kein Mikrofon gefunden|Nenhum microfone encontrado|Микрофон не найден|未找到麦克风|マイクが見つかりません
Microphone unavailable|Micrófono no disponible|Microphone indisponible|Mikrofon nicht verfügbar|Microfone indisponível|Микрофон недоступен|麦克风不可用|マイクを使用できません
Start recording|Iniciar grabación|Démarrer l’enregistrement|Aufnahme starten|Iniciar gravação|Начать запись|开始录音|録音を開始
Stop & transcribe|Detener y transcribir|Arrêter et transcrire|Stoppen und transkribieren|Parar e transcrever|Остановить и распознать|停止并转写|停止して文字起こし
Choose audio file|Elegir archivo de audio|Choisir un fichier audio|Audiodatei auswählen|Escolher arquivo de áudio|Выбрать аудиофайл|选择音频文件|音声ファイルを選択
Choose an audio file|Elige un archivo de audio|Choisissez un fichier audio|Wähle eine Audiodatei|Escolha um arquivo de áudio|Выберите аудиофайл|选择音频文件|音声ファイルを選択
No file selected yet|Ningún archivo seleccionado|Aucun fichier sélectionné|Keine Datei ausgewählt|Nenhum arquivo selecionado|Файл не выбран|尚未选择文件|ファイルが選択されていません
File / recording|Archivo o grabación|Fichier ou enregistrement|Datei oder Aufnahme|Arquivo ou gravação|Файл или запись|文件或录音|ファイルまたは録音
Audio duration|Duración del audio|Durée de l’audio|Audiodauer|Duração do áudio|Длительность аудио|音频时长|音声の長さ
Processing time|Tiempo de procesamiento|Temps de traitement|Verarbeitungszeit|Tempo de processamento|Время обработки|处理用时|処理時間
Date|Fecha|Date|Datum|Data|Дата|日期|日付
Refresh|Actualizar|Actualiser|Aktualisieren|Atualizar|Обновить|刷新|更新
Open recordings & transcripts|Abrir grabaciones y transcripciones|Ouvrir les enregistrements et transcriptions|Aufnahmen und Transkripte öffnen|Abrir gravações e transcrições|Открыть записи и расшифровки|打开录音和转写文本|録音と文字起こしを開く
Your transcript|Tu transcripción|Votre transcription|Dein Transkript|Sua transcrição|Ваша расшифровка|你的转写文本|文字起こし
Original model output|Resultado original del modelo|Sortie brute du modèle|Unbearbeitete Modellausgabe|Saída original do modelo|Исходный результат модели|模型原始输出|モデルの出力結果
Unedited model transcript|Transcripción sin editar|Transcription non modifiée|Unbearbeitetes Transkript|Transcrição sem edição|Расшифровка без правок|未经编辑的转写|未編集の文字起こし
Copy|Copiar|Copier|Kopieren|Copiar|Копировать|复制|コピー
Save|Guardar|Enregistrer|Speichern|Salvar|Сохранить|保存|保存
Save text|Guardar texto|Enregistrer le texte|Text speichern|Salvar texto|Сохранить текст|保存文本|テキストを保存
Save original transcript|Guardar transcripción original|Enregistrer la transcription originale|Originaltranskript speichern|Salvar transcrição original|Сохранить исходную расшифровку|保存原始转写|元の文字起こしを保存
Transcribe again|Volver a transcribir|Transcrire à nouveau|Erneut transkribieren|Transcrever novamente|Распознать ещё раз|重新转写|再度文字起こし
Stop transcription|Detener transcripción|Arrêter la transcription|Transkription stoppen|Parar transcrição|Остановить распознавание|停止转写|文字起こしを停止
Preparing|Preparando|Préparation|Wird vorbereitet|Preparando|Подготовка|正在准备|準備中
Reading audio|Leyendo audio|Lecture de l’audio|Audio wird gelesen|Lendo áudio|Чтение аудио|正在读取音频|音声を読み込み中
Loading model|Cargando modelo|Chargement du modèle|Modell wird geladen|Carregando modelo|Загрузка модели|正在加载模型|モデルを読み込み中
Transcribing|Transcribiendo|Transcription en cours|Wird transkribiert|Transcrevendo|Распознавание|正在转写|文字起こし中
Saving result|Guardando resultado|Enregistrement du résultat|Ergebnis wird gespeichert|Salvando resultado|Сохранение результата|正在保存结果|結果を保存中
Error|Error|Erreur|Fehler|Erro|Ошибка|错误|エラー
Something needs attention|Revisa esta información|Vérification nécessaire|Hinweis|Verifique esta informação|Требуется внимание|需要处理|確認が必要です
Close|Cerrar|Fermer|Schließen|Fechar|Закрыть|关闭|閉じる
Cancel|Cancelar|Annuler|Abbrechen|Cancelar|Отмена|取消|キャンセル
Multilingual|Multilingüe|Multilingue|Mehrsprachig|Multilíngue|Многоязычная|多语言|多言語
CPU processing|Procesamiento en CPU|Traitement sur CPU|Verarbeitung auf der CPU|Processamento na CPU|Обработка на ЦП|CPU 处理|CPU 処理
Audio:|Audio:|Audio :|Audio:|Áudio:|Аудио:|音频：|音声：
Inference:|Inferencia:|Inférence :|Inferenz:|Inferência:|Распознавание:|推理：|推論：
Total:|Total:|Total :|Gesamt:|Total:|Всего:|总计：|合計：
Log:|Registro:|Journal :|Protokoll:|Log:|Журнал:|日志：|ログ：
License:|Licencia:|Licence :|Lizenz:|Licença:|Лицензия:|许可证：|ライセンス：
MIT (developer declaration)|MIT (según el desarrollador)|MIT (déclaration du développeur)|MIT (Angabe des Entwicklers)|MIT (conforme o desenvolvedor)|MIT (по заявлению разработчика)|MIT（开发者声明）|MIT（開発者の申告）
License: {license} · CPU processing|Licencia: {license} · CPU|Licence : {license} · CPU|Lizenz: {license} · CPU|Licença: {license} · CPU|Лицензия: {license} · ЦП|许可证：{license} · CPU|ライセンス：{license} · CPU
{count} languages available|{count} idiomas disponibles|{count} langues disponibles|{count} Sprachen verfügbar|{count} idiomas disponíveis|Доступно языков: {count}|支持 {count} 种语言|{count} 言語に対応
{count} local models found. No files are moved or downloaded again.|{count} modelos locales encontrados. Se conservan los archivos en su ubicación.|Modèles locaux trouvés : {count}. Les fichiers restent en place.|Lokale Modelle gefunden: {count}. Die Dateien bleiben an ihrem Ort.|Modelos locais encontrados: {count}. Os arquivos permanecem no local.|Найдено локальных моделей: {count}. Файлы остаются на месте.|找到 {count} 个本地模型，文件保留在原位置。|ローカルモデルを {count} 個検出しました。ファイルは元の場所に残ります。
Recording · {time} · Stop recording to transcribe.|Grabando · {time} · Detén la grabación para transcribir.|Enregistrement · {time} · Arrêtez pour transcrire.|Aufnahme · {time} · Zum Transkribieren Aufnahme stoppen.|Gravando · {time} · Pare a gravação para transcrever.|Запись · {time} · Остановите запись для распознавания.|正在录音 · {time} · 停止录音即可转写。|録音中 · {time} · 録音を停止すると文字起こしが始まります。
About {time} remaining|Quedan unos {time}|Environ {time} restantes|Noch etwa {time}|Restam cerca de {time}|Осталось около {time}|大约还需 {time}|残り約 {time}
Part {index} of {total}|Parte {index} de {total}|Partie {index} sur {total}|Teil {index} von {total}|Parte {index} de {total}|Фрагмент {index} из {total}|第 {index} / {total} 段|{index} / {total} 区間
{seconds}s elapsed|{seconds} s transcurridos|{seconds} s écoulées|{seconds} s vergangen|{seconds} s decorridos|Прошло {seconds} с|已用时 {seconds} 秒|{seconds} 秒経過
Download progress: {model}|Progreso de descarga: {model}|Progression du téléchargement : {model}|Downloadfortschritt: {model}|Progresso do download: {model}|Ход загрузки: {model}|下载进度：{model}|ダウンロードの進捗：{model}
"""

_CHAT_ROWS = """
Chat mode|Modo de conversación|Mode de discussion|Chatmodus|Modo de conversa|Режим беседы|对话模式|チャットモード
Grammar review|Revisar gramática|Révision grammaticale|Grammatik prüfen|Revisão gramatical|Проверка грамматики|语法检查|文法チェック
Language practice|Practicar idiomas|Pratique des langues|Sprache üben|Prática de idiomas|Языковая практика|语言练习|言語練習
Practice starter|Empezar práctica|Commencer un exercice|Übung beginnen|Começar a prática|Начать упражнение|开始练习|練習を始める
Discuss a transcript or ask a question…|Comenta una transcripción o haz una pregunta…|Discutez d’une transcription ou posez une question…|Besprich ein Transkript oder stelle eine Frage…|Converse sobre uma transcrição ou faça uma pergunta…|Обсудите расшифровку или задайте вопрос…|讨论转写文本或提出问题…|文字起こしについて話したり、質問したりできます…
Enter a sentence or add a voice to check its grammar…|Escribe o graba una frase para revisar la gramática…|Écrivez ou enregistrez une phrase à vérifier…|Schreibe oder sprich einen Satz für die Grammatikprüfung…|Digite ou grave uma frase para revisar a gramática…|Введите или запишите фразу для проверки…|输入或录制一句话来检查语法…|文法を確認したい文を入力するか録音してください…
Say which language you want to practice, or answer by voice…|Indica qué idioma quieres practicar o responde por voz…|Indiquez la langue à pratiquer ou répondez à l’oral…|Wähle eine Übungssprache oder antworte per Spracheingabe…|Diga qual idioma quer praticar ou responda por voz…|Укажите язык для практики или ответьте голосом…|说出想练习的语言，或用语音回答…|練習したい言語を伝えるか、音声で回答してください…
Help me practice a language. Ask me which language and level, then give me one short exercise.|Ayúdame a practicar un idioma. Pregunta cuál y qué nivel tengo, y dame un ejercicio corto.|Aidez-moi à pratiquer une langue. Demandez-moi la langue et mon niveau, puis proposez un exercice court.|Hilf mir beim Sprachenlernen. Frage nach Sprache und Niveau und gib mir dann eine kurze Übung.|Ajude-me a praticar um idioma. Pergunte qual e meu nível, depois proponha um exercício curto.|Помоги мне практиковать язык. Спроси, какой язык и уровень, а затем дай короткое упражнение.|帮我练习一门语言。先问我想练习的语言和水平，再给我一个简短的练习。|言語の練習を手伝ってください。言語とレベルを尋ねてから、短い練習問題を出してください。
Text stays local until you press Send. Audio is never attached.|El texto permanece en tu equipo hasta que pulsas Enviar. El audio nunca se adjunta.|Le texte reste sur votre appareil jusqu’à l’envoi. L’audio n’est jamais joint.|Bis zum Senden bleibt der Text auf deinem Gerät. Audio wird nie angehängt.|O texto fica no dispositivo até você clicar em Enviar. O áudio nunca é anexado.|Текст остаётся на устройстве до отправки. Аудио не прикрепляется.|点击发送前，文本只保存在本机。音频不会作为附件发送。|送信するまでテキストは端末内に保存されます。音声は添付されません。
Add connection|Añadir conexión|Ajouter une connexion|Verbindung hinzufügen|Adicionar conexão|Добавить подключение|添加连接|接続を追加
Edit connection|Editar conexión|Modifier la connexion|Verbindung bearbeiten|Editar conexão|Изменить подключение|编辑连接|接続を編集
Delete connection|Eliminar conexión|Supprimer la connexion|Verbindung löschen|Excluir conexão|Удалить подключение|删除连接|接続を削除
Saved chats|Conversaciones guardadas|Conversations enregistrées|Gespeicherte Chats|Conversas salvas|Сохранённые беседы|已保存的对话|保存済みのチャット
Use current transcript|Usar transcripción actual|Utiliser la transcription actuelle|Aktuelles Transkript verwenden|Usar transcrição atual|Использовать текущую расшифровку|使用当前转写文本|現在の文字起こしを使う
Include this reference text|Incluir este texto de referencia|Inclure ce texte de référence|Diesen Referenztext beifügen|Incluir este texto de referência|Добавить этот справочный текст|包含这段参考文本|この参照テキストを含める
No reference text selected.|No hay texto de referencia seleccionado.|Aucun texte de référence sélectionné.|Kein Referenztext ausgewählt.|Nenhum texto de referência selecionado.|Справочный текст не выбран.|尚未选择参考文本。|参照テキストが選択されていません。
Allow sending selected text and chat to this cloud provider|Permitir enviar el texto seleccionado y la conversación a este proveedor en la nube|Autoriser l’envoi du texte sélectionné et de la conversation à ce fournisseur cloud|Ausgewählten Text und Chat an diesen Cloudanbieter senden|Permitir o envio do texto selecionado e da conversa a este provedor na nuvem|Разрешить отправку выбранного текста и беседы этому облачному поставщику|允许向此云服务发送选定文本和对话|選択したテキストとチャットをこのクラウドサービスに送信することを許可
Send|Enviar|Envoyer|Senden|Enviar|Отправить|发送|送信
Stop waiting|Dejar de esperar|Arrêter l’attente|Warten beenden|Parar de esperar|Прекратить ожидание|停止等待|応答待ちを中止
Copy reply|Copiar respuesta|Copier la réponse|Antwort kopieren|Copiar resposta|Скопировать ответ|复制回复|回答をコピー
Ready.|Listo.|Prêt.|Bereit.|Pronto.|Готово.|已就绪。|準備完了。
Waiting for reply…|Esperando respuesta…|En attente d’une réponse…|Warte auf Antwort…|Aguardando resposta…|Ожидание ответа…|正在等待回复…|応答を待っています…
Reply saved locally.|Respuesta guardada en este dispositivo.|Réponse enregistrée sur cet appareil.|Antwort auf diesem Gerät gespeichert.|Resposta salva neste dispositivo.|Ответ сохранён на устройстве.|回复已保存在本机。|回答を端末に保存しました。
Choose or add a connection first.|Primero elige o añade una conexión.|Choisissez ou ajoutez d’abord une connexion.|Wähle zuerst eine Verbindung oder füge eine hinzu.|Primeiro escolha ou adicione uma conexão.|Сначала выберите или добавьте подключение.|请先选择或添加连接。|先に接続を選択または追加してください。
Confirm cloud sending before pressing Send.|Autoriza el envío a la nube antes de pulsar Enviar.|Autorisez l’envoi vers le cloud avant de continuer.|Bestätige vor dem Senden die Übertragung in die Cloud.|Autorize o envio à nuvem antes de clicar em Enviar.|Перед отправкой подтвердите передачу в облако.|发送前，请先确认允许发送到云服务。|送信する前にクラウドへの送信を許可してください。
Local endpoint: use an installed local model. No AI model is downloaded by Avunote.|Conexión local. Utiliza un modelo local ya instalado. Avunote no descarga modelos de IA.|Connexion locale. Utilisez un modèle installé localement. Avunote ne télécharge pas de modèle d’IA.|Lokale Verbindung. Verwende ein installiertes lokales Modell. Avunote lädt keine KI-Modelle herunter.|Conexão local. Use um modelo local instalado. O Avunote não baixa modelos de IA.|Локальное подключение. Используйте установленную локальную модель. Avunote не скачивает модели ИИ.|本地连接。请使用已安装的本地模型。Avunote 不会下载 AI 模型。|ローカル接続です。インストール済みのローカルモデルを使ってください。Avunote は AI モデルをダウンロードしません。
Google cloud: unpaid requests and replies may be used to improve Google products and reviewed by humans. Free quotas vary.|Google Cloud. Las solicitudes y respuestas gratuitas pueden usarse para mejorar productos de Google y ser revisadas por personas. Los límites gratuitos varían.|Google Cloud. Les requêtes et réponses gratuites peuvent servir à améliorer les produits Google et être examinées par des personnes. Les quotas gratuits varient.|Google Cloud. Kostenlose Anfragen und Antworten können zur Verbesserung von Google-Produkten verwendet und von Menschen geprüft werden. Kostenlose Kontingente können sich ändern.|Google Cloud. Solicitações e respostas gratuitas podem ser usadas para melhorar produtos do Google e passar por revisão humana. As cotas gratuitas variam.|Облако Google. Бесплатные запросы и ответы могут использоваться для улучшения продуктов Google и проверяться людьми. Бесплатные квоты меняются.|Google 云端服务。免费请求和回复可能被用于改进 Google 产品，并可能接受人工审核。免费配额可能变化。|Google クラウド。無料枠のリクエストと応答は、Google 製品の改善に使用されたり、人が確認したりする場合があります。無料枠の上限は変動します。
Cloud endpoint: selected text and conversation leave this device when you press Send. Provider terms and charges apply.|Conexión en la nube. Al pulsar Enviar, el texto seleccionado y la conversación salen del dispositivo. Se aplican las condiciones y tarifas del proveedor.|Connexion cloud. À l’envoi, le texte sélectionné et la conversation quittent votre appareil. Les conditions et tarifs du fournisseur s’appliquent.|Cloudverbindung. Beim Senden verlassen der ausgewählte Text und der Chat dieses Gerät. Die Bedingungen und Gebühren des Anbieters gelten.|Conexão na nuvem. Ao enviar, o texto selecionado e a conversa saem deste dispositivo. Aplicam-se os termos e as tarifas do provedor.|Облачное подключение. При отправке выбранный текст и беседа передаются с устройства. Действуют условия и тарифы поставщика.|云端连接。点击发送后，选定文本和对话将发送到本机之外。适用服务商的条款和费用。|クラウド接続です。送信すると、選択したテキストと会話が端末の外部に送られます。提供元の利用条件と料金が適用されます。
Name|Nombre|Nom|Name|Nome|Имя|名称|名前
Provider|Proveedor|Fournisseur|Anbieter|Provedor|Поставщик|服务商|プロバイダー
API base URL|URL base de la API|URL de base de l’API|API-Basis-URL|URL base da API|Базовый URL API|API 基础网址|API ベース URL
Model name|Nombre del modelo|Nom du modèle|Modellname|Nome do modelo|Название модели|模型名称|モデル名
API key|Clave de API|Clé API|API-Schlüssel|Chave de API|Ключ API|API 密钥|API キー
Local Ollama|Ollama local|Ollama local|Lokales Ollama|Ollama local|Локальная Ollama|本地 Ollama|ローカル Ollama
OpenAI-compatible / LM Studio|Compatible con OpenAI / LM Studio|Compatible OpenAI / LM Studio|OpenAI-kompatibel / LM Studio|Compatível com OpenAI / LM Studio|Совместимый с OpenAI / LM Studio|兼容 OpenAI / LM Studio|OpenAI 互換 / LM Studio
Leave blank to keep the key for an unchanged connection|Déjala vacía para conservar la clave de esta conexión sin cambios|Laissez vide pour conserver la clé d’une connexion inchangée|Leer lassen, um den Schlüssel einer unveränderten Verbindung zu behalten|Deixe em branco para manter a chave de uma conexão sem alterações|Оставьте пустым, чтобы сохранить ключ для неизменённого подключения|连接未更改时，留空以保留密钥|接続を変更していない場合、空欄にすると既存のキーが保持されます
Remember key securely on this Windows account (DPAPI)|Guardar la clave de forma segura en esta cuenta de Windows (DPAPI)|Enregistrer la clé de façon sécurisée dans ce compte Windows (DPAPI)|Schlüssel sicher in diesem Windows-Konto speichern (DPAPI)|Salvar a chave com segurança nesta conta do Windows (DPAPI)|Безопасно сохранить ключ в этой учётной записи Windows (DPAPI)|在此 Windows 账户中安全保存密钥（DPAPI）|この Windows アカウントにキーを安全に保存（DPAPI）
Forget existing key|Olvidar la clave existente|Oublier la clé existante|Gespeicherten Schlüssel entfernen|Esquecer chave existente|Удалить сохранённый ключ|移除现有密钥|保存済みのキーを削除
You|Tú|Vous|Du|Você|Вы|你|あなた
{count} characters · {source}|{count} caracteres · {source}|{count} caractères · {source}|{count} Zeichen · {source}|{count} caracteres · {source}|{count} символов · {source}|{count} 个字符 · {source}|{count} 文字 · {source}
Conversations|Conversaciones|Conversations|Unterhaltungen|Conversas|Беседы|对话|会話
Delete chat|Eliminar conversación|Supprimer la conversation|Chat löschen|Excluir conversa|Удалить беседу|删除对话|チャットを削除
Export chat|Exportar conversación|Exporter la conversation|Chat exportieren|Exportar conversa|Экспортировать беседу|导出对话|チャットをエクスポート
Delete this conversation and its saved draft?|¿Eliminar esta conversación y su borrador guardado?|Supprimer cette conversation et son brouillon enregistré ?|Diese Unterhaltung und den gespeicherten Entwurf löschen?|Excluir esta conversa e o rascunho salvo?|Удалить эту беседу и сохранённый черновик?|删除此对话及其已保存的草稿？|この会話と保存済みの下書きを削除しますか？
Untitled chat|Conversación sin título|Conversation sans titre|Chat ohne Titel|Conversa sem título|Беседа без названия|未命名对话|無題のチャット
Draft|Borrador|Brouillon|Entwurf|Rascunho|Черновик|草稿|下書き
Voice & transcription|Voz y transcripción|Voix et transcription|Sprache und Transkription|Voz e transcrição|Голос и распознавание|语音与转写|音声と文字起こし
Speech settings|Ajustes de voz|Paramètres vocaux|Spracheinstellungen|Configurações de voz|Настройки речи|语音设置|音声の設定
Record a voice|Grabar audio|Enregistrer un message vocal|Sprachnachricht aufnehmen|Gravar áudio|Записать голос|录制语音|音声を録音
Add audio file|Añadir audio|Ajouter un fichier audio|Audiodatei hinzufügen|Adicionar áudio|Добавить аудиофайл|添加音频文件|音声ファイルを追加
Cancel transcription|Cancelar transcripción|Annuler la transcription|Transkription abbrechen|Cancelar transcrição|Отменить распознавание|取消转写|文字起こしをキャンセル
Start a conversation|Iniciar una conversación|Démarrer une conversation|Unterhaltung starten|Iniciar uma conversa|Начать беседу|开始对话|会話を始める
Voice text added to your draft. Review it, then press Send.|Se añadió la transcripción al borrador. Revísala y pulsa Enviar.|La transcription a été ajoutée au brouillon. Vérifiez-la, puis envoyez.|Das Transkript wurde zum Entwurf hinzugefügt. Prüfe es vor dem Senden.|A transcrição foi adicionada ao rascunho. Revise e clique em Enviar.|Расшифровка добавлена в черновик. Проверьте её и отправьте.|转写文本已加入草稿。请确认后发送。|文字起こしを下書きに追加しました。確認してから送信してください。
The audio contained no recognized speech. Your draft is unchanged.|No se reconoció voz en el audio. Se conservó el borrador.|Aucune parole reconnue dans l’audio. Votre brouillon est conservé.|Im Audio wurde keine Sprache erkannt. Dein Entwurf bleibt erhalten.|Nenhuma fala foi reconhecida no áudio. Seu rascunho foi mantido.|Речь в аудио не распознана. Черновик сохранён.|未识别到语音，草稿已保留。|音声を認識できませんでした。下書きは保持されます。
Preparing microphone…|Preparando micrófono…|Préparation du microphone…|Mikrofon wird vorbereitet…|Preparando microfone…|Подготовка микрофона…|正在准备麦克风…|マイクを準備中…
Recording… Speak, then press Stop & transcribe.|Grabando… Habla y después pulsa Detener y transcribir.|Enregistrement… Parlez, puis cliquez sur Arrêter et transcrire.|Aufnahme läuft… Sprich und wähle dann Stoppen und transkribieren.|Gravando… Fale e depois clique em Parar e transcrever.|Запись… Говорите, затем нажмите «Остановить и распознать».|正在录音… 说完后点击停止并转写。|録音中… 話し終えたら停止して文字起こしを開始してください。
Transcribing locally…|Transcribiendo en este dispositivo…|Transcription sur cet appareil…|Lokale Transkription läuft…|Transcrevendo neste dispositivo…|Локальное распознавание…|正在本地转写…|端末内で文字起こし中…
Finishing recording…|Terminando grabación…|Fin de l’enregistrement…|Aufnahme wird abgeschlossen…|Finalizando gravação…|Завершение записи…|正在结束录音…|録音を終了中…
Stopping transcription…|Deteniendo transcripción…|Arrêt de la transcription…|Transkription wird gestoppt…|Interrompendo transcrição…|Остановка распознавания…|正在停止转写…|文字起こしを停止中…
Draft saved locally.|Borrador guardado en este dispositivo.|Brouillon enregistré sur cet appareil.|Entwurf auf diesem Gerät gespeichert.|Rascunho salvo neste dispositivo.|Черновик сохранён на устройстве.|草稿已保存在本机。|下書きを端末に保存しました。
Conversation restored.|Conversación restaurada.|Conversation restaurée.|Unterhaltung wiederhergestellt.|Conversa restaurada.|Беседа восстановлена.|对话已恢复。|会話を復元しました。
Conversation exported.|Conversación exportada.|Conversation exportée.|Unterhaltung exportiert.|Conversa exportada.|Беседа экспортирована.|对话已导出。|会話をエクスポートしました。
The conversation could not be exported.|No se pudo exportar la conversación.|Impossible d’exporter la conversation.|Die Unterhaltung konnte nicht exportiert werden.|Não foi possível exportar a conversa.|Не удалось экспортировать беседу.|无法导出对话。|会話をエクスポートできませんでした。
The conversation could not be deleted.|No se pudo eliminar la conversación.|Impossible de supprimer la conversation.|Die Unterhaltung konnte nicht gelöscht werden.|Não foi possível excluir a conversa.|Не удалось удалить беседу.|无法删除对话。|会話を削除できませんでした。
Your messages are saved on this device automatically.|Tus mensajes se guardan automáticamente en este dispositivo.|Vos messages sont enregistrés automatiquement sur cet appareil.|Deine Nachrichten werden automatisch auf diesem Gerät gespeichert.|Suas mensagens são salvas automaticamente neste dispositivo.|Сообщения автоматически сохраняются на этом устройстве.|消息会自动保存在本机。|メッセージはこの端末に自動保存されます。
"""



_STATUS_ROWS = """
Connect free AI|Conectar IA gratuita|Connecter une IA gratuite|Kostenlose KI verbinden|Conectar IA gratuita|Подключить бесплатный ИИ|连接免费 AI|無料 AI に接続
Allow cloud chat|Permitir chat en la nube|Autoriser la discussion dans le cloud|Cloud-Chat erlauben|Permitir conversa na nuvem|Разрешить облачный чат|允许云端对话|クラウドチャットを許可
OpenRouter free models have usage limits. Your text is sent to OpenRouter and the selected provider.|Los modelos gratuitos de OpenRouter tienen límites de uso. Tu texto se envía a OpenRouter y al proveedor elegido.|Les modèles gratuits d’OpenRouter ont des limites d’utilisation. Votre texte est transmis à OpenRouter et au fournisseur sélectionné.|Kostenlose OpenRouter-Modelle haben Nutzungslimits. Dein Text wird an OpenRouter und den gewählten Anbieter gesendet.|Os modelos gratuitos do OpenRouter têm limites de uso. Seu texto é enviado ao OpenRouter e ao provedor selecionado.|У бесплатных моделей OpenRouter есть лимиты. Ваш текст передаётся OpenRouter и выбранному поставщику.|OpenRouter 的免费模型有用量限制。文本将发送给 OpenRouter 和所选服务商。|OpenRouter の無料モデルには利用上限があります。テキストは OpenRouter と選択した提供元に送信されます。
Choose a file or drop it into this window.|Elige un archivo o arrástralo a esta ventana.|Choisissez un fichier ou déposez-le dans cette fenêtre.|Wähle eine Datei aus oder ziehe sie in dieses Fenster.|Escolha um arquivo ou solte-o nesta janela.|Выберите файл или перетащите его в это окно.|选择文件，或将文件拖到此窗口。|ファイルを選択するか、このウィンドウにドロップしてください。
Double-click a result to see its original transcript and processing statistics.|Haz doble clic en un resultado para ver la transcripción y los datos de procesamiento.|Double-cliquez sur un résultat pour afficher la transcription et les statistiques de traitement.|Doppelklicke auf ein Ergebnis, um das Transkript und Verarbeitungsdaten zu sehen.|Clique duas vezes em um resultado para ver a transcrição e as estatísticas.|Дважды щёлкните результат, чтобы открыть расшифровку и статистику обработки.|双击结果以查看原始转写和处理统计。|結果をダブルクリックすると元の文字起こしと処理統計を表示します。
Get a model for this speech language first, or add a local model folder.|Descarga un modelo para este idioma o añade la carpeta de uno local.|Téléchargez un modèle pour cette langue ou ajoutez un dossier de modèle local.|Lade ein Modell für diese Sprache herunter oder füge einen lokalen Modellordner hinzu.|Baixe um modelo para este idioma ou adicione a pasta de um modelo local.|Скачайте модель для этого языка или добавьте папку с локальной моделью.|请先下载适用于此语言的模型，或添加本地模型文件夹。|この言語のモデルをダウンロードするか、ローカルモデルのフォルダーを追加してください。
No model is installed for this language. Download one from the model library.|No hay un modelo instalado para este idioma. Descarga uno de la biblioteca.|Aucun modèle installé pour cette langue. Téléchargez-en un depuis la bibliothèque.|Für diese Sprache ist kein Modell installiert. Lade eines aus der Bibliothek herunter.|Nenhum modelo instalado para este idioma. Baixe um na biblioteca.|Для этого языка нет установленной модели. Скачайте её из библиотеки.|尚未安装此语言的模型。请从模型库下载。|この言語のモデルは未インストールです。ライブラリからダウンロードしてください。
This model is not installed. Download it from the library or add a local model.|Este modelo no está instalado. Descárgalo o añade un modelo local.|Ce modèle n’est pas installé. Téléchargez-le ou ajoutez un modèle local.|Das Modell ist nicht installiert. Lade es herunter oder füge ein lokales Modell hinzu.|Este modelo não está instalado. Baixe-o ou adicione um modelo local.|Модель не установлена. Скачайте её или добавьте локальную модель.|此模型尚未安装。请下载模型或添加本地模型。|このモデルは未インストールです。ダウンロードするかローカルモデルを追加してください。
Transcription is available once the model is ready.|Podrás transcribir cuando el modelo esté listo.|La transcription sera disponible lorsque le modèle sera prêt.|Die Transkription ist verfügbar, sobald das Modell bereit ist.|A transcrição fica disponível quando o modelo estiver pronto.|Распознавание станет доступно, когда модель будет готова.|模型就绪后即可转写。|モデルの準備ができると文字起こしできます。
These models support the selected language. Download multilingual models once and reuse them across languages.|Estos modelos admiten el idioma elegido. Descarga cada modelo multilingüe una vez y úsalo en varios idiomas.|Ces modèles prennent en charge la langue choisie. Téléchargez chaque modèle multilingue une fois pour l’utiliser dans plusieurs langues.|Diese Modelle unterstützen die gewählte Sprache. Mehrsprachige Modelle lassen sich nach dem Download für mehrere Sprachen verwenden.|Estes modelos são compatíveis com o idioma selecionado. Baixe cada modelo multilíngue uma vez para usá-lo em vários idiomas.|Эти модели поддерживают выбранный язык. Многоязычную модель можно скачать один раз и использовать для нескольких языков.|这些模型支持所选语言。多语言模型只需下载一次，可用于多种语言。|これらのモデルは選択した言語に対応しています。多言語モデルは一度ダウンロードすれば複数の言語で使えます。
Speech language is detected automatically.|El idioma se detecta automáticamente.|La langue parlée est détectée automatiquement.|Die gesprochene Sprache wird automatisch erkannt.|O idioma falado é detectado automaticamente.|Язык речи определяется автоматически.|自动检测语音语言。|音声の言語は自動で検出されます。
This model always runs on the CPU.|Este modelo siempre usa la CPU.|Ce modèle utilise toujours le processeur.|Dieses Modell läuft immer auf der CPU.|Este modelo sempre usa a CPU.|Эта модель всегда работает на ЦП.|此模型始终在 CPU 上运行。|このモデルは常に CPU で実行します。
This model uses a fixed decoder. Processing mode affects audio chunk boundaries.|Este modelo usa un decodificador fijo. El modo de procesamiento cambia la división del audio.|Ce modèle utilise un décodeur fixe. Le mode de traitement modifie le découpage de l’audio.|Dieses Modell nutzt einen festen Decoder. Der Verarbeitungsmodus beeinflusst die Audiosegmentierung.|Este modelo usa um decodificador fixo. O modo de processamento altera a divisão do áudio.|У этой модели фиксированный декодер. Режим обработки влияет на разбиение аудио.|此模型使用固定解码器。处理模式会影响音频分段。|このモデルのデコーダーは固定です。処理モードは音声の分割位置に影響します。
Cancelling download|Cancelando descarga|Annulation du téléchargement|Download wird abgebrochen|Cancelando download|Отмена загрузки|正在取消下载|ダウンロードをキャンセル中
Choose a valid WAV, MP3, M4A, or OGG file.|Elige un archivo WAV, MP3, M4A u OGG válido.|Choisissez un fichier WAV, MP3, M4A ou OGG valide.|Wähle eine gültige WAV-, MP3-, M4A- oder OGG-Datei.|Escolha um arquivo WAV, MP3, M4A ou OGG válido.|Выберите корректный файл WAV, MP3, M4A или OGG.|请选择有效的 WAV、MP3、M4A 或 OGG 文件。|有効な WAV、MP3、M4A、OGG ファイルを選択してください。
Recording failed. Check your microphone and Windows microphone permissions.|No se pudo grabar. Comprueba el micrófono y los permisos de Windows.|Échec de l’enregistrement. Vérifiez le microphone et les autorisations de Windows.|Aufnahme fehlgeschlagen. Prüfe Mikrofon und Windows-Berechtigungen.|Falha na gravação. Verifique o microfone e as permissões do Windows.|Запись не удалась. Проверьте микрофон и разрешения Windows.|录音失败。请检查麦克风及 Windows 麦克风权限。|録音できませんでした。マイクと Windows のアクセス許可を確認してください。
The recording is too short. Please speak for at least one second.|La grabación es demasiado corta. Habla al menos un segundo.|L’enregistrement est trop court. Parlez au moins une seconde.|Die Aufnahme ist zu kurz. Sprich mindestens eine Sekunde.|A gravação é muito curta. Fale por pelo menos um segundo.|Запись слишком короткая. Говорите не менее секунды.|录音太短，请至少说一秒。|録音が短すぎます。1 秒以上話してください。
The microphone dropped some audio. Reduce system load and record again.|Se perdió parte del audio. Reduce la carga del sistema y vuelve a grabar.|Une partie de l’audio a été perdue. Réduisez la charge du système et recommencez.|Ein Teil der Aufnahme ging verloren. Verringere die Systemlast und nimm erneut auf.|Parte do áudio foi perdida. Reduza a carga do sistema e grave novamente.|Часть аудио потеряна. Снизьте нагрузку на систему и повторите запись.|部分音频丢失。请降低系统负载后重新录音。|音声の一部が失われました。システムの負荷を減らして録音し直してください。
Transcription stopped. You can choose another file or model.|Transcripción detenida. Puedes elegir otro archivo o modelo.|Transcription arrêtée. Vous pouvez choisir un autre fichier ou modèle.|Transkription gestoppt. Du kannst eine andere Datei oder ein anderes Modell wählen.|Transcrição interrompida. Você pode escolher outro arquivo ou modelo.|Распознавание остановлено. Можно выбрать другой файл или модель.|转写已停止。可以选择其他文件或模型。|文字起こしを停止しました。別のファイルやモデルを選べます。
Done. Your transcript and processing report have been saved.|Listo. Se guardaron la transcripción y el informe de procesamiento.|Terminé. La transcription et le rapport de traitement sont enregistrés.|Fertig. Transkript und Verarbeitungsbericht wurden gespeichert.|Pronto. A transcrição e o relatório foram salvos.|Готово. Расшифровка и отчёт сохранены.|已完成。转写文本和处理报告已保存。|完了しました。文字起こしと処理レポートを保存しました。
Transcription did not finish.|La transcripción no terminó.|La transcription n’a pas abouti.|Die Transkription wurde nicht abgeschlossen.|A transcrição não foi concluída.|Распознавание не завершено.|转写未完成。|文字起こしが完了しませんでした。
Transcription failed. A diagnostic log has been kept.|Falló la transcripción. Se guardó un registro de diagnóstico.|Échec de la transcription. Un journal de diagnostic a été conservé.|Transkription fehlgeschlagen. Ein Diagnoseprotokoll wurde gespeichert.|Falha na transcrição. Um log de diagnóstico foi salvo.|Распознавание не удалось. Сохранён журнал диагностики.|转写失败，已保存诊断日志。|文字起こしに失敗しました。診断ログを保存しました。
Showing a saved result from your history.|Mostrando un resultado del historial.|Affichage d’un résultat de l’historique.|Ein gespeichertes Ergebnis wird angezeigt.|Exibindo um resultado do histórico.|Показан сохранённый результат из истории.|正在显示历史记录中的结果。|履歴に保存された結果を表示しています。
Check your connection and disk space, then try again.|Comprueba la conexión y el espacio en disco y vuelve a intentarlo.|Vérifiez la connexion et l’espace disque, puis réessayez.|Prüfe Verbindung und Speicherplatz und versuche es erneut.|Verifique a conexão e o espaço em disco e tente novamente.|Проверьте подключение и свободное место, затем повторите попытку.|请检查网络连接和磁盘空间，然后重试。|接続と空き容量を確認してから再試行してください。
Secure HTTPS connections are unavailable in this build. Reinstall or update Avunote, then try again.|Las conexiones HTTPS seguras no están disponibles en esta versión. Reinstala o actualiza Avunote y vuelve a intentarlo.|Les connexions HTTPS sécurisées sont indisponibles dans cette version. Réinstallez ou mettez à jour Avunote, puis réessayez.|Sichere HTTPS-Verbindungen sind in dieser Version nicht verfügbar. Installiere oder aktualisiere Avunote erneut und versuche es noch einmal.|Conexões HTTPS seguras não estão disponíveis nesta versão. Reinstale ou atualize o Avunote e tente novamente.|Защищённые HTTPS-подключения недоступны в этой сборке. Переустановите или обновите Avunote и повторите попытку.|此版本无法使用安全 HTTPS 连接。请重新安装或更新 Avunote 后重试。|このビルドでは安全な HTTPS 接続を利用できません。Avunote を再インストールまたは更新してから再試行してください。
Could not connect through the system proxy. Check your VPN or proxy, then try again.|No se pudo conectar mediante el proxy del sistema. Comprueba la VPN o el proxy y vuelve a intentarlo.|Connexion impossible via le proxy système. Vérifiez votre VPN ou votre proxy, puis réessayez.|Keine Verbindung über den System-Proxy. Prüfe VPN oder Proxy und versuche es erneut.|Não foi possível conectar pelo proxy do sistema. Verifique a VPN ou o proxy e tente novamente.|Не удалось подключиться через системный прокси. Проверьте VPN или прокси и повторите попытку.|无法通过系统代理连接。请检查 VPN 或代理后重试。|システムプロキシ経由で接続できませんでした。VPN またはプロキシを確認してから再試行してください。
Could not reach Hugging Face. Check your internet connection, VPN or proxy, then try again.|No se pudo acceder a Hugging Face. Comprueba Internet, la VPN o el proxy y vuelve a intentarlo.|Impossible de joindre Hugging Face. Vérifiez votre connexion Internet, votre VPN ou votre proxy, puis réessayez.|Hugging Face ist nicht erreichbar. Prüfe Internetverbindung, VPN oder Proxy und versuche es erneut.|Não foi possível acessar o Hugging Face. Verifique a internet, a VPN ou o proxy e tente novamente.|Не удалось подключиться к Hugging Face. Проверьте интернет, VPN или прокси и повторите попытку.|无法连接 Hugging Face。请检查网络、VPN 或代理后重试。|Hugging Face に接続できませんでした。インターネット接続、VPN、プロキシを確認してから再試行してください。
Hugging Face refused the download. Try again in a little while.|Hugging Face rechazó la descarga. Vuelve a intentarlo en un rato.|Hugging Face a refusé le téléchargement. Réessayez dans un moment.|Hugging Face hat den Download abgelehnt. Versuche es später erneut.|O Hugging Face recusou o download. Tente novamente daqui a pouco.|Hugging Face отклонил загрузку. Повторите попытку чуть позже.|Hugging Face 拒绝了下载。请稍后重试。|Hugging Face がダウンロードを拒否しました。しばらくしてから再試行してください。
A downloaded file failed integrity verification. Try the download again.|Un archivo descargado no superó la verificación de integridad. Vuelve a intentar la descarga.|Un fichier téléchargé a échoué à la vérification d’intégrité. Relancez le téléchargement.|Eine heruntergeladene Datei hat die Integritätsprüfung nicht bestanden. Starte den Download erneut.|Um arquivo baixado falhou na verificação de integridade. Tente o download novamente.|Загруженный файл не прошёл проверку целостности. Повторите загрузку.|一个已下载文件未通过完整性校验。请重新下载。|ダウンロードしたファイルが整合性チェックに失敗しました。もう一度ダウンロードしてください。
Not enough free disk space for this model.|No hay suficiente espacio libre en disco para este modelo.|Espace disque insuffisant pour ce modèle.|Nicht genug freier Speicherplatz für dieses Modell.|Não há espaço livre suficiente em disco para este modelo.|Недостаточно свободного места на диске для этой модели.|磁盘空间不足，无法保存此模型。|このモデルに必要な空き容量がありません。
Could not save the model files. Check disk space and folder permissions.|No se pudieron guardar los archivos del modelo. Comprueba el espacio en disco y los permisos de la carpeta.|Impossible d’enregistrer les fichiers du modèle. Vérifiez l’espace disque et les autorisations du dossier.|Die Modelldateien konnten nicht gespeichert werden. Prüfe Speicherplatz und Ordnerberechtigungen.|Não foi possível salvar os arquivos do modelo. Verifique o espaço em disco e as permissões da pasta.|Не удалось сохранить файлы модели. Проверьте место на диске и права доступа к папке.|无法保存模型文件。请检查磁盘空间和文件夹权限。|モデルファイルを保存できませんでした。空き容量とフォルダーのアクセス許可を確認してください。
The download is still stopping. Wait a moment, then try Resume again.|La descarga todavía se está deteniendo. Espera un momento y vuelve a pulsar Reanudar.|Le téléchargement est encore en train de s’arrêter. Attendez un instant, puis réessayez Reprendre.|Der Download wird noch beendet. Warte kurz und klicke dann erneut auf Fortsetzen.|O download ainda está parando. Espere um momento e tente Retomar de novo.|Загрузка ещё останавливается. Подождите немного и снова нажмите Продолжить.|下载仍在停止中。请稍候再点击继续下载。|ダウンロードの停止処理中です。少し待ってから再開してください。
Recognition settings|Ajustes de reconocimiento|Paramètres de reconnaissance|Erkennungseinstellungen|Configurações de reconhecimento|Настройки распознавания|识别设置|認識設定
Audio source|Fuente de audio|Source audio|Audioquelle|Fonte de áudio|Источник звука|音频来源|音声の入力元
Your transcript appears here|Tu transcripción aparecerá aquí|Votre transcription s’affichera ici|Dein Transkript erscheint hier|Sua transcrição aparecerá aqui|Расшифровка появится здесь|转写文本将显示在此处|ここに文字起こしが表示されます
Choose an audio file or record to get started.|Elige un archivo de audio o inicia una grabación.|Choisissez un fichier audio ou lancez un enregistrement.|Wähle eine Audiodatei oder starte eine Aufnahme.|Escolha um arquivo de áudio ou inicie uma gravação.|Выберите аудиофайл или начните запись.|选择音频文件或开始录音。|音声ファイルを選択するか録音を開始してください。
Choose a language. Get the right model. Transcribe offline.|Elige un idioma, descarga un modelo y transcribe sin conexión.|Choisissez une langue et un modèle, puis transcrivez hors ligne.|Wähle Sprache und Modell und transkribiere offline.|Escolha um idioma e um modelo para transcrever offline.|Выберите язык и модель для распознавания офлайн.|选择语言和模型，即可离线转写。|言語とモデルを選択してオフラインで文字起こしできます。
These Azerbaijani models are tailored to the variety spoken in Iran.|Estos modelos están diseñados para el azerí hablado en Irán.|Ces modèles sont adaptés à l’azéri parlé en Iran.|Diese Modelle sind auf Aserbaidschanisch in Iran ausgelegt.|Estes modelos são voltados ao azerbaijano falado no Irã.|Эти модели предназначены для азербайджанского языка в Иране.|这些模型面向伊朗使用的阿塞拜疆语。|これらのモデルはイランで話されるアゼルバイジャン語に対応しています。
Dedicated models for Iranian Azerbaijani, preserving the original model spelling.|Modelos para el azerí iraní que conservan la ortografía del modelo.|Modèles pour l’azéri iranien, avec l’orthographe originale du modèle.|Modelle für iranisches Aserbaidschanisch mit der Originalschreibweise des Modells.|Modelos para o azerbaijano iraniano que preservam a ortografia do modelo.|Модели для азербайджанского языка Ирана сохраняют исходное написание.|适用于伊朗阿塞拜疆语的模型，保留模型原始拼写。|イラン・アゼルバイジャン語向けのモデルで、元の表記を保持します。
Dedicated South Azerbaijani model · CPU|Modelo de azerí meridional · CPU|Modèle pour l’azéri méridional · CPU|Modell für Südaserbaidschanisch · CPU|Modelo para o azerbaijano meridional · CPU|Модель для южноазербайджанского · ЦП|南阿塞拜疆语专用模型 · CPU|南アゼルバイジャン語専用モデル · CPU
South Azerbaijani model · Kartal Ol Foundation|Modelo de azerí meridional · Fundación Kartal Ol|Modèle d’azéri méridional · Fondation Kartal Ol|Südaserbaidschanisch-Modell · Kartal Ol Foundation|Modelo de azerbaijano meridional · Fundação Kartal Ol|Модель южноазербайджанского · Фонд Kartal Ol|南阿塞拜疆语模型 · Kartal Ol 基金会|南アゼルバイジャン語モデル · Kartal Ol 財団
Compact. Great for a first try and speed checks · Shared download · CPU INT8|Compacto y rápido, ideal para empezar · CPU INT8|Compact et rapide, idéal pour débuter · CPU INT8|Kompakt und schnell, gut für den Einstieg · CPU INT8|Compacto e rápido, ideal para começar · CPU INT8|Компактная быстрая модель для начала · ЦП INT8|体积小、速度快，适合入门 · CPU INT8|小型で高速、初めての利用に適しています · CPU INT8
Balanced size and speed · One download for multiple languages · CPU INT8|Equilibrio entre tamaño y velocidad · Multilingüe · CPU INT8|Bon équilibre entre taille et vitesse · Multilingue · CPU INT8|Ausgewogene Größe und Geschwindigkeit · Mehrsprachig · CPU INT8|Equilíbrio entre tamanho e velocidade · Multilíngue · CPU INT8|Баланс размера и скорости · Многоязычная · ЦП INT8|兼顾体积与速度 · 多语言 · CPU INT8|サイズと速度のバランス · 多言語 · CPU INT8
A good candidate for Persian accuracy tests; slower processing · Shared download · CPU INT8|Opción para comparar la precisión en persa; procesa más despacio · CPU INT8|Option pour évaluer la précision en persan, avec un traitement plus lent · CPU INT8|Zum Vergleich der Genauigkeit bei Persisch, mit langsamerer Verarbeitung · CPU INT8|Opção para comparar a precisão em persa, com processamento mais lento · CPU INT8|Подходит для сравнения точности на персидском, работает медленнее · ЦП INT8|适合比较波斯语识别精度，处理较慢 · CPU INT8|ペルシア語の精度比較向けで、処理はやや低速です · CPU INT8
25 European languages · automatic language detection · CPU INT8|25 idiomas europeos · detección automática · CPU INT8|25 langues européennes · détection automatique · CPU INT8|25 europäische Sprachen · automatische Erkennung · CPU INT8|25 idiomas europeus · detecção automática · CPU INT8|25 европейских языков · автоопределение · ЦП INT8|25 种欧洲语言 · 自动检测语言 · CPU INT8|欧州 25 言語 · 言語の自動検出 · CPU INT8
Persian, Turkish, Arabic and more · automatic language detection · CPU INT8|Persa, turco, árabe y más · detección automática · CPU INT8|Persan, turc, arabe et autres · détection automatique · CPU INT8|Persisch, Türkisch, Arabisch und weitere · automatische Erkennung · CPU INT8|Persa, turco, árabe e outros · detecção automática · CPU INT8|Персидский, турецкий, арабский и другие · автоопределение · ЦП INT8|波斯语、土耳其语、阿拉伯语等 · 自动检测语言 · CPU INT8|ペルシア語、トルコ語、アラビア語など · 言語の自動検出 · CPU INT8
Mandarin, English, Japanese and Korean · CPU INT8|Mandarín, inglés, japonés y coreano · CPU INT8|Mandarin, anglais, japonais et coréen · CPU INT8|Mandarin, Englisch, Japanisch und Koreanisch · CPU INT8|Mandarim, inglês, japonês e coreano · CPU INT8|Мандаринский, английский, японский и корейский · ЦП INT8|普通话、英语、日语和韩语 · CPU INT8|中国語（普通話）、英語、日本語、韓国語 · CPU INT8
Falling back to CPU|Cambiando a CPU|Basculement sur le processeur|Wechsel zur CPU|Mudando para a CPU|Переход на ЦП|正在切换到 CPU|CPU に切り替え中
Speech recognition stays on this device.|El reconocimiento se hace en tu dispositivo.|La reconnaissance vocale se fait sur votre appareil.|Die Spracherkennung findet auf deinem Gerät statt.|O reconhecimento acontece no seu dispositivo.|Распознавание речи выполняется на вашем устройстве.|语音识别在此设备上完成。|音声認識はこのデバイス上で行います。
Microphone level|Nivel del micrófono|Niveau du microphone|Mikrofonpegel|Nível do microfone|Уровень микрофона|麦克风音量|マイクレベル
Discuss this transcript|Comentar esta transcripción|Discuter de cette transcription|Dieses Transkript besprechen|Conversar sobre esta transcrição|Обсудить эту расшифровку|讨论这段转写|この文字起こしについて話す
No thanks|No, gracias|Non merci|Nein, danke|Não, obrigado|Нет, спасибо|不用了|いいえ
Open GitHub repository|Abrir repositorio de GitHub|Ouvrir le dépôt GitHub|GitHub-Repository öffnen|Abrir repositório no GitHub|Открыть репозиторий GitHub|打开 GitHub 仓库|GitHub リポジトリを開く
Audio is transcribed locally with your selected speech model. Review the text, then Send.|El modelo seleccionado transcribe el audio en tu equipo. Revisa el texto antes de enviarlo.|Le modèle choisi transcrit l’audio sur votre appareil. Relisez le texte avant l’envoi.|Das gewählte Modell transkribiert Audio auf deinem Gerät. Prüfe den Text vor dem Senden.|O modelo selecionado transcreve o áudio no seu dispositivo. Revise o texto antes de enviar.|Выбранная модель распознаёт аудио на устройстве. Проверьте текст перед отправкой.|所选模型会在本机转写音频。检查文本后再发送。|選択した音声モデルで端末内で文字起こしします。確認してから送信してください。
Speech processing stopped. Your draft is preserved.|Se detuvo el procesamiento de voz. Se conservó el borrador.|Le traitement vocal a été arrêté. Votre brouillon est conservé.|Sprachverarbeitung gestoppt. Dein Entwurf bleibt erhalten.|O processamento de voz foi interrompido. Seu rascunho foi mantido.|Обработка речи остановлена. Черновик сохранён.|语音处理已停止，草稿已保留。|音声処理を停止しました。下書きは保持されます。
Voice input failed. Your draft is preserved.|Falló la entrada de voz. Se conservó el borrador.|Échec de la saisie vocale. Votre brouillon est conservé.|Spracheingabe fehlgeschlagen. Dein Entwurf bleibt erhalten.|Falha na entrada de voz. Seu rascunho foi mantido.|Голосовой ввод не удался. Черновик сохранён.|语音输入失败，草稿已保留。|音声入力に失敗しました。下書きは保持されます。
Choose a downloaded speech model in Speech settings.|Selecciona un modelo descargado en los ajustes de voz.|Choisissez un modèle téléchargé dans les paramètres vocaux.|Wähle in den Spracheinstellungen ein heruntergeladenes Modell.|Escolha um modelo baixado nas configurações de voz.|Выберите скачанную модель в настройках речи.|请在语音设置中选择已下载的模型。|音声設定でダウンロード済みのモデルを選択してください。
Choose a microphone in Speech settings, or add an audio file.|Elige un micrófono en los ajustes de voz o añade un archivo de audio.|Choisissez un microphone dans les paramètres vocaux ou ajoutez un fichier audio.|Wähle ein Mikrofon in den Spracheinstellungen oder füge eine Audiodatei hinzu.|Escolha um microfone nas configurações de voz ou adicione um arquivo de áudio.|Выберите микрофон в настройках речи или добавьте аудиофайл.|请在语音设置中选择麦克风，或添加音频文件。|音声設定でマイクを選択するか、音声ファイルを追加してください。
Finish the current voice input before switching conversations.|Termina la entrada de voz antes de cambiar de conversación.|Terminez la saisie vocale avant de changer de conversation.|Beende die aktuelle Spracheingabe, bevor du den Chat wechselst.|Conclua a entrada de voz antes de mudar de conversa.|Завершите голосовой ввод перед переключением беседы.|请先结束当前语音输入，再切换对话。|音声入力を終了してから会話を切り替えてください。
The saved chat could not be loaded.|No se pudo cargar la conversación guardada.|Impossible de charger la conversation enregistrée.|Der gespeicherte Chat konnte nicht geladen werden.|Não foi possível carregar a conversa salva.|Не удалось загрузить сохранённую беседу.|无法加载已保存的对话。|保存済みのチャットを読み込めませんでした。
Do not include your API key in the conversation or reference text.|No incluyas tu clave de API en la conversación ni en el texto de referencia.|N’incluez pas votre clé API dans la conversation ni dans le texte de référence.|Füge deinen API-Schlüssel nicht zum Chat oder Referenztext hinzu.|Não inclua sua chave de API na conversa ou no texto de referência.|Не указывайте ключ API в беседе или справочном тексте.|请勿在对话或参考文本中包含 API 密钥。|会話や参照テキストに API キーを含めないでください。
"""


def _apply_rows(target, locales, rows):
    for line in rows.strip().splitlines():
        source, *translations = line.split('|')
        if len(translations) != len(locales):
            raise ValueError(f'Invalid translation row: {source}')
        for locale, translation in zip(locales, translations):
            target.setdefault(locale, {})[source] = translation


EXPANDED_TRANSLATIONS = {}
_apply_rows(EXPANDED_TRANSLATIONS, ('fa', 'tr', 'ar', 'az'), _NEW_ROWS)
_new_codes = tuple(code for code, _ in ADDITIONAL_LANGUAGES)
for _table in (_APP_ROWS, _CORE_ROWS, _CHAT_ROWS, _STATUS_ROWS):
    _apply_rows(EXPANDED_TRANSLATIONS, _new_codes, _table)


# Language names derived from ICU/CLDR via Intl.DisplayNames. Keep stable app
# language codes separate from display strings, especially Iranian Azerbaijani.
_SPEECH_ROWS = """
azb|Azerí iraní|Azéri iranien|Iranisches Aserbaidschanisch|Azerbaijano iraniano|Иранский азербайджанский|伊朗阿塞拜疆语|イラン・アゼルバイジャン語|İran Azerbaycancası|الأذربيجانية الإيرانية|İran Azərbaycan dili
fa|persa (Irán)|persan (Iran)|Persisch (Iran)|persa (Irã)|персидский (Иран)|波斯语（伊朗）|ペルシア語 (イラン)|Farsça (İran)|الفارسية (إيران)|fars (İran)
tr|turco|turc|Türkisch|turco|турецкий|土耳其语|トルコ語|Türkçe|التركية|türk
en|inglés|anglais|Englisch|inglês|английский|英语|英語|İngilizce|الإنجليزية|ingilis
ar|árabe|arabe|Arabisch|árabe|арабский|阿拉伯语|アラビア語|Arapça|العربية|ərəb
de|alemán|allemand|Deutsch|alemão|немецкий|德语|ドイツ語|Almanca|الألمانية|alman
fr|francés|français|Französisch|francês|французский|法语|フランス語|Fransızca|الفرنسية|fransız
es|español|espagnol|Spanisch|espanhol|испанский|西班牙语|スペイン語|İspanyolca|الإسبانية|ispan
ru|ruso|russe|Russisch|russo|русский|俄语|ロシア語|Rusça|الروسية|rus
it|italiano|italien|Italienisch|italiano|итальянский|意大利语|イタリア語|İtalyanca|الإيطالية|italyan
pt|portugués|portugais|Portugiesisch|português|португальский|葡萄牙语|ポルトガル語|Portekizce|البرتغالية|portuqal
nl|neerlandés|néerlandais|Niederländisch|holandês|нидерландский|荷兰语|オランダ語|Felemenkçe|الهولندية|holland
hi|hindi|hindi|Hindi|híndi|хинди|印地语|ヒンディー語|Hintçe|الهندية|hind
ur|urdu|ourdou|Urdu|urdu|урду|乌尔都语|ウルドゥー語|Urduca|الأوردية|urdu
zh|chino|chinois|Chinesisch|chinês|китайский|中文|中国語|Çince|الصينية|çin
ja|japonés|japonais|Japanisch|japonês|японский|日语|日本語|Japonca|اليابانية|yapon
ko|coreano|coréen|Koreanisch|coreano|корейский|韩语|韓国語|Korece|الكورية|koreya
uk|ucraniano|ukrainien|Ukrainisch|ucraniano|украинский|乌克兰语|ウクライナ語|Ukraynaca|الأوكرانية|ukrayna
pl|polaco|polonais|Polnisch|polonês|польский|波兰语|ポーランド語|Lehçe|البولندية|polyak
sv|sueco|suédois|Schwedisch|sueco|шведский|瑞典语|スウェーデン語|İsveççe|السويدية|isveç
el|griego|grec|Griechisch|grego|греческий|希腊语|ギリシャ語|Yunanca|اليونانية|yunan
he|hebreo|hébreu|Hebräisch|hebraico|иврит|希伯来语|ヘブライ語|İbranice|العبرية|ivrit
af|afrikáans|afrikaans|Afrikaans|africâner|африкаанс|南非荷兰语|アフリカーンス語|Afrikaanca|الأفريقانية|afrikaans
sq|albanés|albanais|Albanisch|albanês|албанский|阿尔巴尼亚语|アルバニア語|Arnavutça|الألبانية|alban
am|amárico|amharique|Amharisch|amárico|амхарский|阿姆哈拉语|アムハラ語|Amharca|الأمهرية|amhar
hy|armenio|arménien|Armenisch|armênio|армянский|亚美尼亚语|アルメニア語|Ermenice|الأرمنية|erməni
as|asamés|assamais|Assamesisch|assamês|ассамский|阿萨姆语|アッサム語|Assamca|الأسامية|assam
ba|baskir|bachkir|Baschkirisch|bashkir|башкирский|巴什基尔语|バシキール語|Başkırtça|الباشكيرية|başqırd
eu|euskera|basque|Baskisch|basco|баскский|巴斯克语|バスク語|Baskça|الباسكية|bask
be|bielorruso|biélorusse|Belarussisch|bielorrusso|белорусский|白俄罗斯语|ベラルーシ語|Belarusça|البيلاروسية|belarus
bn|bengalí|bengali|Bengalisch|bengali|бенгальский|孟加拉语|ベンガル語|Bengalce|البنغالية|benqal
bs|bosnio|bosniaque|Bosnisch|bósnio|боснийский|波斯尼亚语|ボスニア語|Boşnakça|البوسنية|bosniya
br|bretón|breton|Bretonisch|bretão|бретонский|布列塔尼语|ブルトン語|Bretonca|البريتونية|breton
bg|búlgaro|bulgare|Bulgarisch|búlgaro|болгарский|保加利亚语|ブルガリア語|Bulgarca|البلغارية|bolqar
ca|catalán|catalan|Katalanisch|catalão|каталанский|加泰罗尼亚语|カタロニア語|Katalanca|الكتالانية|katalan
hr|croata|croate|Kroatisch|croata|хорватский|克罗地亚语|クロアチア語|Hırvatça|الكرواتية|xorvat
cs|checo|tchèque|Tschechisch|tcheco|чешский|捷克语|チェコ語|Çekçe|التشيكية|çex
da|danés|danois|Dänisch|dinamarquês|датский|丹麦语|デンマーク語|Danca|الدانمركية|danimarka
et|estonio|estonien|Estnisch|estoniano|эстонский|爱沙尼亚语|エストニア語|Estonca|الإستونية|eston
fo|feroés|féroïen|Färöisch|feroês|фарерский|法罗语|フェロー語|Faroe dili|الفاروية|farer
fi|finés|finnois|Finnisch|finlandês|финский|芬兰语|フィンランド語|Fince|الفنلندية|fin
gl|gallego|galicien|Galicisch|galego|галисийский|加利西亚语|ガリシア語|Galiçyaca|الجاليكية|qalisiya
ka|georgiano|géorgien|Georgisch|georgiano|грузинский|格鲁吉亚语|ジョージア語|Gürcüce|الجورجية|gürcü
gu|guyaratí|goudjarati|Gujarati|guzerate|гуджарати|古吉拉特语|グジャラート語|Güceratça|الغوجاراتية|qucarat
ht|criollo haitiano|créole haïtien|Haiti-Kreolisch|haitiano|гаитянский|海地克里奥尔语|ハイチ・クレオール語|Haiti Kreyolu|الكريولية الهايتية|haiti kreol
ha|hausa|haoussa|Haussa|hauçá|хауса|豪萨语|ハウサ語|Hausa dili|الهوسا|hausa
haw|hawaiano|hawaïen|Hawaiisch|havaiano|гавайский|夏威夷语|ハワイ語|Hawaii dili|لغة هاواي|havay
hu|húngaro|hongrois|Ungarisch|húngaro|венгерский|匈牙利语|ハンガリー語|Macarca|الهنغارية|macar
is|islandés|islandais|Isländisch|islandês|исландский|冰岛语|アイスランド語|İzlandaca|الأيسلندية|island
id|indonesio|indonésien|Indonesisch|indonésio|индонезийский|印度尼西亚语|インドネシア語|Endonezce|الإندونيسية|indoneziya
jw|javanés|javanais|Javanisch|javanês|яванский|爪哇语|ジャワ語|Cava dili|الجاوية|yava
kn|canarés|kannada|Kannada|canarim|каннада|卡纳达语|カンナダ語|Kannada dili|الكانادا|kannada
kk|kazajo|kazakh|Kasachisch|cazaque|казахский|哈萨克语|カザフ語|Kazakça|الكازاخستانية|qazax
km|jemer|khmer|Khmer|khmer|кхмерский|高棉语|クメール語|Khmer dili|الخميرية|kxmer
lo|lao|lao|Laotisch|laosiano|лаосский|老挝语|ラオ語|Lao dili|اللاوية|laos
la|latín|latin|Latein|latim|латинский|拉丁语|ラテン語|Latince|اللاتينية|latın
lv|letón|letton|Lettisch|letão|латышский|拉脱维亚语|ラトビア語|Letonca|اللاتفية|latış
ln|lingala|lingala|Lingala|lingala|лингала|林加拉语|リンガラ語|Lingala|اللينجالا|linqala
lt|lituano|lituanien|Litauisch|lituano|литовский|立陶宛语|リトアニア語|Litvanca|الليتوانية|litva
lb|luxemburgués|luxembourgeois|Luxemburgisch|luxemburguês|люксембургский|卢森堡语|ルクセンブルク語|Lüksemburgca|اللكسمبورغية|lüksemburq
mk|macedonio|macédonien|Mazedonisch|macedônio|македонский|马其顿语|マケドニア語|Makedonca|المقدونية|makedon
mg|malgache|malgache|Malagasy|malgaxe|малагасийский|马拉加斯语|マダガスカル語|Malgaşça|الملغاشي|malaqas
ms|malayo|malais|Malaiisch|malaio|малайский|马来语|マレー語|Malayca|الماليزية|malay
ml|malayálam|malayalam|Malayalam|malaiala|малаялам|马拉雅拉姆语|マラヤーラム語|Malayalam dili|المالايالامية|malayalam
mt|maltés|maltais|Maltesisch|maltês|мальтийский|马耳他语|マルタ語|Maltaca|المالطية|malta
mi|maorí|maori|Māori|maori|маори|毛利语|マオリ語|Maori dili|الماورية|māori
mr|maratí|marathi|Marathi|marati|маратхи|马拉地语|マラーティー語|Marathi dili|الماراثية|marathi
mn|mongol|mongol|Mongolisch|mongol|монгольский|蒙古语|モンゴル語|Moğolca|المنغولية|monqol
my|birmano|birman|Birmanisch|birmanês|бирманский|缅甸语|ミャンマー語|Birman dili|البورمية|birman
ne|nepalí|népalais|Nepalesisch|nepalês|непальский|尼泊尔语|ネパール語|Nepalce|النيبالية|nepal
no|noruego|norvégien|Norwegisch|norueguês|норвежский|挪威语|ノルウェー語|Norveççe|النرويجية|norveç
nn|noruego nynorsk|norvégien nynorsk|Norwegisch (Nynorsk)|nynorsk norueguês|нюнорск|挪威尼诺斯克语|ノルウェー語(ニーノシュク)|Norveççe Nynorsk|النرويجية نينورسك|nünorsk norveç
oc|occitano|occitan|Okzitanisch|occitânico|окситанский|奥克语|オック語|Oksitan dili|الأوكسيتانية|oksitan
ps|pastún|pachto|Paschtu|pashto|пушту|普什图语|パシュトゥー語|Peştuca|البشتو|puştu
pa|punyabí|pendjabi|Punjabi|panjabi|панджаби|旁遮普语|パンジャブ語|Pencapça|البنجابية|pəncab
ro|rumano|roumain|Rumänisch|romeno|румынский|罗马尼亚语|ルーマニア語|Rumence|الرومانية|rumın
sa|sánscrito|sanskrit|Sanskrit|sânscrito|санскрит|梵语|サンスクリット語|Sanskrit|السنسكريتية|sanskrit
sr|serbio|serbe|Serbisch|sérvio|сербский|塞尔维亚语|セルビア語|Sırpça|الصربية|serb
sn|shona|shona|Shona|xona|шона|绍纳语|ショナ語|Şona dili|الشونا|şona
sd|sindi|sindhi|Sindhi|sindi|синдхи|信德语|シンド語|Sindhi dili|السندية|sindhi
si|cingalés|cingalais|Singhalesisch|cingalês|сингальский|僧伽罗语|シンハラ語|Sinhali dili|السنهالية|sinhala
sk|eslovaco|slovaque|Slowakisch|eslovaco|словацкий|斯洛伐克语|スロバキア語|Slovakça|السلوفاكية|slovak
sl|esloveno|slovène|Slowenisch|esloveno|словенский|斯洛文尼亚语|スロベニア語|Slovence|السلوفانية|sloven
so|somalí|somali|Somali|somali|сомали|索马里语|ソマリ語|Somalice|الصومالية|somali
su|sundanés|soundanais|Sundanesisch|sundanês|сунданский|巽他语|スンダ語|Sunda dili|السوندانية|sundan
sw|suajili|swahili|Suaheli|suaíli|суахили|斯瓦希里语|スワヒリ語|Svahili dili|السواحلية|suahili
tl|filipino|filipino|Filipino|filipino|филиппинский|菲律宾语|フィリピノ語|Filipince|الفلبينية|filippin
tg|tayiko|tadjik|Tadschikisch|tadjique|таджикский|塔吉克语|タジク語|Tacikçe|الطاجيكية|tacik
ta|tamil|tamoul|Tamil|tâmil|тамильский|泰米尔语|タミル語|Tamilce|التاميلية|tamil
tt|tártaro|tatar|Tatarisch|tártaro|татарский|鞑靼语|タタール語|Tatarca|التترية|tatar
te|telugu|télougou|Telugu|télugo|телугу|泰卢固语|テルグ語|Telugu dili|التيلوغوية|teluqu
th|tailandés|thaï|Thailändisch|tailandês|тайский|泰语|タイ語|Tayca|التايلاندية|tay
bo|tibetano|tibétain|Tibetisch|tibetano|тибетский|藏语|チベット語|Tibetçe|التبتية|tibet
tk|turcomano|turkmène|Turkmenisch|turcomeno|туркменский|土库曼语|トルクメン語|Türkmence|التركمانية|türkmən
uz|uzbeko|ouzbek|Usbekisch|uzbeque|узбекский|乌兹别克语|ウズベク語|Özbekçe|الأوزبكية|özbək
vi|vietnamita|vietnamien|Vietnamesisch|vietnamita|вьетнамский|越南语|ベトナム語|Vietnamca|الفيتنامية|vyetnam
cy|galés|gallois|Walisisch|galês|валлийский|威尔士语|ウェールズ語|Galce|الويلزية|uels
yi|yidis|yiddish|Jiddisch|iídiche|идиш|意第绪语|イディッシュ語|Yidiş|اليديشية|idiş
yo|yoruba|yoruba|Yoruba|iorubá|йоруба|约鲁巴语|ヨルバ語|Yorubaca|اليوروبا|yoruba
"""
SPEECH_NAMES = {}
_apply_rows(SPEECH_NAMES, (*_new_codes, 'tr', 'ar', 'az'), _SPEECH_ROWS)
