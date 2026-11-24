# -*- coding: utf-8 -*-
"""Shared localizations for the Python-owned controls and preview catalog."""
from __future__ import absolute_import, unicode_literals


LANGUAGES = ('de', 'en', 'es', 'fr', 'pl', 'ru', 'uk')
DECIMAL_COMMA_LANGUAGES = frozenset(LANGUAGES) - {'en'}
_ADDITIONAL = ('de', 'es', 'fr', 'ru', 'uk')

try:
    _TEXT = unicode
except NameError:
    _TEXT = str


def language_code(language):
    """Normalize the game locale, including byte strings and regional tags."""
    if isinstance(language, bytes):
        try:
            language = language.decode('ascii')
        except UnicodeDecodeError:
            return 'en'
    if not isinstance(language, _TEXT):
        return 'en'
    code = language.strip().lower().replace('_', '-').partition('-')[0]
    if code == 'ua':
        code = 'uk'
    return code if code in LANGUAGES else 'en'


def localize_decimal(text, language):
    return text.replace(str('.'), str(',')) if language_code(language) in DECIMAL_COMMA_LANGUAGES else text


def _rows(languages, rows):
    if any(len(values) != len(languages) for values in rows.values()):
        raise ValueError('Incomplete preview translations')
    return {key: dict(zip(languages, values)) for key, values in rows.items()}


_MESSAGES = _rows(LANGUAGES, {
    'saved': ('Gespeichert', 'Saved', 'Guardado', 'Enregistré', 'Zapisano', 'Сохранено', 'Збережено'),
    'save_failed': (
        'Die Einstellungen wurden nicht gespeichert. Die bisherigen Einstellungen bleiben aktiv.',
        'Settings were not saved. Previous settings remain active.',
        'No se guardaron los ajustes. Los ajustes anteriores siguen activos.',
        'Les paramètres n’ont pas été enregistrés. Les paramètres précédents restent actifs.',
        'Nie zapisano ustawień. Poprzednie ustawienia pozostają aktywne.',
        'Не удалось сохранить настройки. Предыдущие настройки остались активны.',
        'Не вдалося зберегти налаштування. Попередні налаштування залишаються активними.',
    ),
    'invalid_settings': (
        'Ungültige Einstellungen.', 'Invalid settings.', 'Ajustes no válidos.',
        'Paramètres non valides.', 'Nieprawidłowe ustawienia.', 'Недопустимые настройки.', 'Некоректні налаштування.',
    ),
    'load_failed': (
        'Die Einstellungsdatei konnte nicht gelesen werden. Siehe %s.',
        'Settings file could not be read. Check %s.',
        'No se pudo leer el archivo de ajustes. Consulta %s.',
        'Impossible de lire le fichier de paramètres. Consultez %s.',
        'Nie udało się odczytać pliku ustawień. Sprawdź %s.',
        'Не удалось прочитать файл настроек. Проверьте %s.',
        'Не вдалося прочитати файл налаштувань. Перевірте %s.',
    ),
    'window_unavailable': (
        'Das Einstellungsfenster ist nicht verfügbar.', 'Settings window unavailable.',
        'La ventana de ajustes no está disponible.', 'La fenêtre des paramètres est indisponible.',
        'Okno ustawień jest niedostępne.', 'Окно настроек недоступно.', 'Вікно налаштувань недоступне.',
    ),
})


def message(key, language):
    return _MESSAGES[key][language_code(language)]


# Languages in each row are German, Spanish, French, Russian and Ukrainian.
# The catalog already owns the original Polish and English strings.
_MECHANICS = _rows(_ADDITIONAL, {
    'standard': ('Standardgeschütz', 'Cañón estándar', 'Canon standard', 'Обычное орудие', 'Звичайна гармата'),
    'cassette': ('Ladeautomat mit Magazin', 'Cargador automático', 'Chargeur automatique', 'Барабанный магазин', 'Барабанний магазин'),
    'forced_reload': ('Erzwungenes Nachladen des Magazins', 'Recarga forzada del cargador', 'Rechargement forcé du chargeur', 'Принудительная перезарядка магазина', 'Примусове перезаряджання магазина'),
    'autoreloader': ('Nachladeautomatik', 'Recarga automática por proyectil', 'Rechargement automatique obus par obus', 'Автоматическое дозаряжание', 'Автоматичне дозаряджання'),
    'extra_shot': ('Nachladeautomatik mit Reservegranate', 'Recarga automática con proyectil de reserva', 'Rechargement automatique avec obus de réserve', 'Дозаряжание с резервным снарядом', 'Дозаряджання з резервним снарядом'),
    'controllable_reload': ('Kontrolliertes Nachladen', 'Recarga controlada', 'Rechargement contrôlé', 'Управляемая перезарядка', 'Кероване перезаряджання'),
    'unlimited': ('Unbegrenztes Magazin', 'Cargador ilimitado', 'Chargeur illimité', 'Неограниченный магазин', 'Необмежений магазин'),
    'shell_calibration': ('Granatenkalibrierung', 'Calibración de proyectiles', 'Calibrage des obus', 'Калибровка снаряда', 'Калібрування снаряда'),
    'dualgun': ('Doppelläufiges Geschütz', 'Cañón de doble tubo', 'Canon à double tube', 'Двуствольное орудие', 'Двоствольна гармата'),
    'twingun': ('Zwillingsgeschütz / Salve', 'Cañones gemelos / salva', 'Canons jumelés / salve', 'Спаренные орудия / залп', 'Спарені гармати / залп'),
    'dual_accuracy': ('Zwei Genauigkeitsstufen', 'Dos niveles de precisión', 'Deux niveaux de précision', 'Два уровня точности', 'Два рівні точності'),
    'accuracy_stacks': ('Genauigkeitsstufen', 'Niveles de precisión', 'Niveaux de précision', 'Уровни точности', 'Рівні точності'),
    'charge_shot': ('Aufgeladener Schuss', 'Disparo cargado', 'Tir chargé', 'Заряжаемый выстрел', 'Заряджуваний постріл'),
    'low_charge_shot': ('Schuss bei teilweiser Nachladung', 'Disparo con recarga parcial', 'Tir après rechargement partiel', 'Выстрел при неполной перезарядке', 'Постріл за неповного перезаряджання'),
    'auxiliary_rocket_launcher': ('Zusätzlicher Raketenwerfer', 'Lanzacohetes auxiliar', 'Lance-roquettes auxiliaire', 'Вспомогательная ракетная установка', 'Допоміжна ракетна установка'),
    'autoreloader_surge': ('Beschleunigtes Nachladen', 'Recarga acelerada', 'Rechargement accéléré', 'Ускоренное дозаряжание', 'Прискорене дозаряджання'),
    'battle_fury': ('Kampfwut', 'Furia de combate', 'Fureur de combat', 'Боевая ярость', 'Бойова лють'),
    'chargeable_burst': ('Aufladbare Salve', 'Ráfaga cargable', 'Rafale rechargeable', 'Заряжаемая очередь', 'Заряджувана черга'),
    'heating_zones_gun': ('Heizzonen des Geschützes', 'Zonas de calentamiento del cañón', 'Zones de chauffe du canon', 'Зоны нагрева орудия', 'Зони нагрівання гармати'),
    'overheat_stacks': ('Überhitzungsstufen', 'Niveles de sobrecalentamiento', 'Niveaux de surchauffe', 'Уровни перегрева', 'Рівні перегрівання'),
    'pillbox_siege': ('Bunker-Belagerungsmodus', 'Modo de asedio fortificado', 'Mode siège fortifié', 'Осадный режим ДОТа', 'Облоговий режим вогневої точки'),
    'propellant_gun': ('Geschütz mit zusätzlicher Treibladung', 'Cañón con carga propulsora adicional', 'Canon à charge propulsive supplémentaire', 'Орудие с дополнительным метательным зарядом', 'Гармата з додатковим метальним зарядом'),
    'stance_dance': ('Kampfmodus / schnelleres Nachladen', 'Modo de combate / recarga más rápida', 'Mode combat / rechargement accéléré', 'Боевой режим / ускоренная перезарядка', 'Бойовий режим / прискорене перезаряджання'),
    'stationary_reload': ('Nachladen im Stand', 'Recarga en posición fija', 'Rechargement à l’arrêt', 'Перезарядка на месте', 'Перезаряджання на місці'),
    'concentration': ('Konzentration', 'Concentración', 'Concentration', 'Концентрация', 'Концентрація'),
    'overheat': ('Geschützüberhitzung', 'Sobrecalentamiento del cañón', 'Surchauffe du canon', 'Перегрев орудия', 'Перегрівання гармати'),
    'temperature_autocannon': ('Automatikgeschütz mit Überhitzung', 'Cañón automático con sobrecalentamiento', 'Canon automatique avec surchauffe', 'Автоматическое орудие с перегревом', 'Автоматична гармата з перегріванням'),
    'bustle_feed': ('Nachladen mit externem Zuführsystem', 'Recarga con alimentador externo', 'Rechargement par alimentation externe', 'Перезарядка с внешней подачей', 'Перезаряджання із зовнішньою подачею'),
})


def mechanic_label(row, language):
    locale = language_code(language)
    return _MECHANICS.get(row['id'], {}).get(locale) or row.get('label_' + locale, row['label_en'])


_VEHICLES = _rows(_ADDITIONAL, {
    'xi_bz_79': (
        'Die Anzeige der wiederaufladbaren Raketenbeschleuniger gehört zum separaten Gefechtsfeld.',
        'El indicador de los propulsores recargables está en un panel de batalla aparte.',
        'L’indicateur des propulseurs rechargeables se trouve dans un panneau de bataille distinct.',
        'Индикатор перезаряжаемых ракетных ускорителей находится на отдельной панели боя.',
        'Індикатор перезаряджуваних ракетних прискорювачів розташований на окремій панелі бою.',
    ),
    'xi_ptz_78': (
        'Die Stufen der Strahlbeschleuniger werden in einem separaten Gefechtsfeld angezeigt.',
        'El indicador de los propulsores por etapas está en un panel de batalla aparte.',
        'L’indicateur des propulseurs à plusieurs étages se trouve dans un panneau de bataille distinct.',
        'Индикатор многоступенчатых реактивных ускорителей находится на отдельной панели боя.',
        'Індикатор багатоступеневих реактивних прискорювачів розташований на окремій панелі бою.',
    ),
    'xi_wz_219': (
        'Die Anzeige des Entfernungsmessers mit Zielerfassung gehört zum separaten Gefechtsfeld.',
        'El indicador del telémetro de detección de objetivos está en un panel de batalla aparte.',
        'L’indicateur du télémètre de détection des cibles figure dans un panneau de bataille distinct.',
        'Индикатор дальномера обнаружения целей находится на отдельной панели боя.',
        'Індикатор далекоміра виявлення цілей розташований на окремій панелі бою.',
    ),
    'xi_vz_63p': (
        'Das Fadenkreuz zeigt die Granatenkalibrierung und das Zweischussmagazin. Die Mechanikanzeige gehört zum Gefechtsfeld.',
        'La retícula muestra la calibración de proyectiles y el cargador de dos proyectiles. El indicador propio está en el panel de batalla.',
        'Le réticule indique le calibrage des obus et le chargeur à deux obus. L’indicateur dédié se trouve dans le panneau de bataille.',
        'Прицел показывает калибровку снаряда и магазин на два снаряда. Индикатор механики находится на панели боя.',
        'Приціл показує калібрування снаряда й магазин на два снаряди. Індикатор механіки розташований на панелі бою.',
    ),
    'xi_as_xx_40_t': (
        'Das Fadenkreuz zeigt das Magazin und das Nachladen im Stand. Bedingungen und Zeit stehen im separaten Gefechtsfeld.',
        'La retícula muestra el cargador y la recarga en posición fija. El panel de batalla indica las condiciones y el tiempo.',
        'Le réticule affiche le chargeur et le rechargement à l’arrêt. Les conditions et la durée sont indiquées dans le panneau de bataille.',
        'Прицел показывает магазин и перезарядку на месте. Условия и время отображаются на отдельной панели боя.',
        'Приціл показує магазин і перезаряджання на місці. Умови й час відображаються на окремій панелі бою.',
    ),
    'xi_amx_67_imbattable': (
        'Vierschussmagazin mit der Möglichkeit, eine Reservegranate nachzuladen.',
        'Cargador de cuatro proyectiles con recarga de un proyectil de reserva.',
        'Chargeur à quatre obus avec possibilité de recharger un obus de réserve.',
        'Магазин на четыре снаряда с возможностью дозарядить резервный снаряд.',
        'Магазин на чотири снаряди з можливістю дозарядити резервний снаряд.',
    ),
    'xi_fauteur': (
        'Im Scharfschützenmodus steht die Zoomanzeige an einer anderen Stelle. Die Treibladungsskala gehört zum Gefechtsfeld.',
        'En modo francotirador cambia la posición del indicador de zoom. La escala de carga está en el panel de batalla.',
        'En mode sniper, la position de l’indicateur de zoom change. La jauge de charge se trouve dans le panneau de bataille.',
        'В снайперском режиме меняется положение индикатора увеличения. Шкала заряда находится на панели боя.',
        'У снайперському режимі змінюється розташування індикатора збільшення. Шкала заряду є на панелі бою.',
    ),
    'xi_leopard_120_verbessert': (
        'Vier Genauigkeitsstufen und eine vollständig gefüllte Fortschrittsanzeige.',
        'Cuatro niveles de precisión y una barra de progreso completa.',
        'Quatre niveaux de précision et une barre de progression pleine.',
        'Четыре уровня точности и заполненная шкала прогресса.',
        'Чотири рівні точності й заповнена шкала поступу.',
    ),
    'xi_taschenratte': (
        'Die Anzeige des Zusatzgeschützes gehört zum separaten Gefechtsfeld.',
        'El indicador del cañón auxiliar está en un panel de batalla aparte.',
        'L’indicateur du canon auxiliaire figure dans un panneau de bataille distinct.',
        'Индикатор вспомогательного орудия находится на отдельной панели боя.',
        'Індикатор допоміжної гармати розташований на окремій панелі бою.',
    ),
    'xi_hirschkafer': (
        'Überhitzungsstufen und die zugehörige Anzeige am Fadenkreuz.',
        'Niveles de sobrecalentamiento e indicador alrededor de la retícula.',
        'Niveaux de surchauffe et indicateur autour du réticule.',
        'Уровни перегрева и индикатор вокруг прицела.',
        'Рівні перегрівання й індикатор навколо прицілу.',
    ),
    'xi_lekpz_borkenkafer': (
        'Die Zielmarkierungsanzeige steht in einem separaten Gefechtsfeld.',
        'El indicador de designación de objetivos está en un panel de batalla aparte.',
        'L’indicateur de désignation des cibles figure dans un panneau de bataille distinct.',
        'Индикатор обозначения целей находится на отдельной панели боя.',
        'Індикатор позначення цілей розташований на окремій панелі бою.',
    ),
    'xi_pz_kpfw_neu': (
        'Die Anzeige für den Modus mit geänderten Granatenparametern gehört zum separaten Gefechtsfeld.',
        'El modo que modifica los parámetros de los proyectiles tiene un indicador en un panel de batalla aparte.',
        'L’indicateur du mode qui modifie les paramètres des obus se trouve dans un panneau de bataille distinct.',
        'Индикатор режима изменения параметров снарядов находится на отдельной панели боя.',
        'Індикатор режиму зміни параметрів снарядів розташований на окремій панелі бою.',
    ),
    'xi_cav_mod_71': (
        'Vierschussmagazin und drei verfügbare Ladungen für beschleunigtes Nachladen.',
        'Cargador de cuatro proyectiles y tres cargas de recarga acelerada disponibles.',
        'Chargeur à quatre obus et trois charges de rechargement accéléré disponibles.',
        'Магазин на четыре снаряда и три доступных заряда ускоренного дозаряжания.',
        'Магазин на чотири снаряди й три доступні заряди прискореного дозаряджання.',
    ),
    'xi_ho_ri_shugo': (
        'Das Fadenkreuz des Raketenwerfers ist sichtbar. Seine Zustandsanzeige gehört zum separaten Gefechtsfeld.',
        'La retícula muestra el lanzacohetes. Su estado se indica en un panel de batalla aparte.',
        'Le réticule du lance-roquettes est affiché. Son indicateur d’état figure dans le panneau de bataille.',
        'Показан прицел ракетной установки. Индикатор её состояния находится на отдельной панели боя.',
        'Показано приціл ракетної установки. Індикатор її стану розташований на окремій панелі бою.',
    ),
    'xi_stk_2': (
        'Das Fadenkreuz zeigt den Zustand des Streukreises. Die Heizzonenskala gehört zum Gefechtsfeld.',
        'La retícula muestra el estado del círculo de dispersión. La escala de calentamiento está en el panel de batalla.',
        'Le réticule affiche l’état du cercle de dispersion. La jauge des zones de chauffe figure dans le panneau de bataille.',
        'Прицел показывает состояние круга разброса. Шкала зон нагрева находится на панели боя.',
        'Приціл показує стан кола розкиду. Шкала зон нагрівання розташована на панелі бою.',
    ),
    'xi_cs_67_szakal': (
        'Das Fadenkreuz zeigt den Nachladebonus. Das Gefechtsfeld enthält Anzeigen für Kampf- und Turbomodus.',
        'La retícula muestra la bonificación a la recarga. El panel de batalla contiene los indicadores de combate y turbo.',
        'Le réticule indique le bonus de rechargement. Le panneau de bataille affiche les modes combat et turbo.',
        'Прицел показывает бонус к перезарядке. Индикаторы боевого и турборежима находятся на панели боя.',
        'Приціл показує бонус до перезаряджання. Індикатори бойового режиму й турборежиму є на панелі бою.',
    ),
    'xi_strv_107_12': (
        'Das Fadenkreuz zeigt den Bunker-Belagerungsmodus. Zustand und Vorrichtungen werden im Gefechtsfeld angezeigt.',
        'La retícula muestra el modo de asedio fortificado. El panel de batalla indica el estado y los dispositivos.',
        'Le réticule indique le mode siège fortifié. Le panneau de bataille affiche l’état et les dispositifs.',
        'Прицел показывает осадный режим ДОТа. Состояние и устройства отображаются на панели боя.',
        'Приціл показує облоговий режим вогневої точки. Стан і пристрої відображаються на панелі бою.',
    ),
    'xi_bv_111': (
        'Die Nachladeanzeige zählt die längere Zeit mit externer Zuführung herunter. Die eigene Anzeige steht im Gefechtsfeld.',
        'El contador de la retícula muestra la recarga más larga con el alimentador externo. El indicador específico está en el panel de batalla.',
        'Le compteur du réticule indique le rechargement plus lent avec l’alimentation externe. L’indicateur dédié se trouve dans le panneau de bataille.',
        'Прицел отсчитывает увеличенное время перезарядки с внешней подачей. Индикатор подачи находится на панели боя.',
        'Приціл відраховує довший час перезаряджання із зовнішньою подачею. Індикатор подачі є на панелі бою.',
    ),
    'xi_at_fv230_breaker': (
        'Die Anzeige des Motorleistungsmodus steht in einem separaten Gefechtsfeld.',
        'El indicador del modo de potencia del motor está en un panel de batalla aparte.',
        'L’indicateur du mode de puissance moteur se trouve dans un panneau de bataille distinct.',
        'Индикатор режима мощности двигателя находится на отдельной панели боя.',
        'Індикатор режиму потужності двигуна розташований на окремій панелі бою.',
    ),
    'xi_fv4025_contriver': (
        'Fadenkreuz der Zwillingsgeschütze im Salvenmodus.',
        'Retícula de los cañones gemelos en modo de salva.',
        'Réticule des canons jumelés en mode salve.',
        'Прицел спаренных орудий в режиме залпа.',
        'Приціл спарених гармат у режимі залпу.',
    ),
    'xi_executor': (
        'Die Beschleunigungsanzeige des Radfahrzeugs gehört zum separaten Gefechtsfeld.',
        'El indicador de aceleración del vehículo de ruedas está en un panel de batalla aparte.',
        'L’indicateur d’accélération du véhicule à roues se trouve dans un panneau de bataille distinct.',
        'Индикатор ускорения колёсной машины находится на отдельной панели боя.',
        'Індикатор прискорення колісної машини розташований на окремій панелі бою.',
    ),
    'xi_xm69_hacker': (
        'Die Vorschau zeigt die Konzentrationsanzeige am Fadenkreuz. Der separate Fortschritt gehört zum Gefechtsfeld.',
        'La vista previa muestra el efecto de concentración en la retícula. El progreso tiene un indicador aparte en el panel de batalla.',
        'L’aperçu affiche l’effet de concentration autour du réticule. Un indicateur de progression distinct figure dans le panneau de bataille.',
        'В предпросмотре показан эффект концентрации у прицела. Отдельный индикатор прогресса находится на панели боя.',
        'У попередньому перегляді показано ефект концентрації біля прицілу. Окремий індикатор поступу є на панелі бою.',
    ),
    'xi_black_rock': (
        'Das Fadenkreuz zeigt den Modus der aufladbaren Salve. Durchschläge und verfügbare Salven stehen im Gefechtsfeld.',
        'La retícula muestra el modo de ráfaga cargable. Las penetraciones y ráfagas disponibles se indican en el panel de batalla.',
        'Le réticule indique le mode rafale rechargeable. Les pénétrations et les rafales disponibles figurent dans le panneau de bataille.',
        'Прицел показывает режим заряжаемой очереди. Пробития и доступные очереди отображаются на панели боя.',
        'Приціл показує режим заряджуваної черги. Пробиття й доступні черги відображаються на панелі бою.',
    ),
    'xi_ares_90_c': (
        'Das Fadenkreuz zeigt das Automatikgeschützmagazin und die Überhitzungsanzeige. Die vollständige Temperaturskala gehört zum Gefechtsfeld.',
        'La retícula muestra el cargador del cañón automático y el efecto de sobrecalentamiento. La escala completa está en el panel de batalla.',
        'Le réticule affiche le chargeur du canon automatique et l’effet de surchauffe. La jauge complète figure dans le panneau de bataille.',
        'На прицеле показаны магазин автоматического орудия и эффект перегрева. Полная шкала температуры находится на панели боя.',
        'На прицілі показано магазин автоматичної гармати й ефект перегрівання. Повна шкала температури є на панелі бою.',
    ),
    'xi_t803': (
        'Das Fadenkreuz zeigt Kampfwut und den damit verbundenen Nachladebonus.',
        'La retícula muestra la furia de combate y su bonificación a la recarga.',
        'Le réticule affiche la fureur de combat et son bonus de rechargement.',
        'Прицел показывает боевую ярость и её бонус к перезарядке.',
        'Приціл показує бойову лють та її бонус до перезаряджання.',
    ),
    'xi_gorilla': (
        'Das Fadenkreuz zeigt den Schuss bei teilweiser Nachladung. Die Anzeige beider Phasen gehört zum Gefechtsfeld.',
        'La retícula muestra el disparo con recarga parcial. Las dos fases tienen un indicador aparte en el panel de batalla.',
        'Le réticule affiche le tir après rechargement partiel. Les deux phases sont indiquées dans le panneau de bataille.',
        'Прицел показывает выстрел при неполной перезарядке. Индикатор обеих фаз находится на панели боя.',
        'Приціл показує постріл за неповного перезаряджання. Індикатор обох фаз розташований на панелі бою.',
    ),
    'xi_kr_1': (
        'Die verbesserte Rammfähigkeit ändert das Fadenkreuz nicht.',
        'El embate mejorado no modifica la retícula.',
        'L’éperonnage amélioré ne modifie pas le réticule.',
        'Улучшенный таран не меняет прицел.',
        'Поліпшений таран не змінює приціл.',
    ),
    'xi_object_432u': (
        'Das Fadenkreuz zeigt den Ladezustand des Schusses. Die separate Schadensanzeige gehört zum Gefechtsfeld.',
        'La retícula muestra la carga del disparo. El indicador específico de daño está en el panel de batalla.',
        'Le réticule indique la charge du tir. L’indicateur de dégâts dédié figure dans le panneau de bataille.',
        'Прицел показывает заряд выстрела. Отдельный индикатор урона находится на панели боя.',
        'Приціл показує заряд пострілу. Окремий індикатор шкоди розташований на панелі бою.',
    ),
})


def vehicle_note(vehicle, language):
    locale = language_code(language)
    return _VEHICLES.get(vehicle['id'], {}).get(locale) or vehicle.get('detail_' + locale, vehicle['detail_en'])
