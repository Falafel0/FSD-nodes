# FSD Nodes for ComfyUI

Унифицированное расширение, объединяющее 4 custom_nodes под брендингом **FSD**:

| Модуль | Назначение | Узлов |
|--------|-----------|-------|
| **FSD_PIPE** | Пайплайн-ориентированная архитектура с единым контекстом (`FSD_PIPE`), A1111-синтаксис промптов, HiresFix, Inpaint, ControlNet | 60 |
| **Standalone** | Динамические Switch/Diverter (до 20 портов), Boolean Gate, Node Bypasser, Toggle | 8 |
| **Danbooru Gallery** | Поиск и импорт изображений с Danbooru, автодополнение тегов, очистка промптов, интеграция с Krita | 28 |
| **Style Selector** | Визуальный выбор стилей с превью, множественный выбор, поиск, локальные базы данных, drag-and-drop загрузка превью | 1 |

**Всего: ~97 узлов**

## Установка

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/fsd/comfyui-fsd-nodes.git
cd comfyui-fsd-nodes
pip install -r requirements.txt
```

## Зависимости

- Python >= 3.8
- requests, aiohttp, Pillow, torch, numpy, aiosqlite, psutil

## Структура

```
ComfyUI-FSD-nodes/
├── __init__.py              # Единая точка входа
├── pipe_nodes.py            # FSD_PIPE узлы (ядро)
├── standalone_nodes.py      # Switch, Bypasser, Toggle
├── utils.py                 # FSD_PIPE инфраструктура
├── py/
│   ├── danbooru_gallery/    # Danbooru Gallery (28 узлов)
│   ├── style_selector/      # Style Selector (1 узел)
│   ├── utils/               # Logger, Config
│   └── shared/db/           # Tag DB Manager
├── js/                      # Фронтенд
│   ├── fsd/                 # FSD JS (bypasser, mutator, switches)
│   ├── danbooru_gallery/    # Danbooru JS (галерея, autocomplete)
│   └── style_selector/      # Style Selector JS (галерея, drag-drop)
├── data/                    # Данные
│   ├── zh_cn/               # Китайские переводы тегов
│   ├── style_databases/     # Локальные базы стилей
│   └── styleselector_ui_state.json
└── assets/                  # Медиа-ресурсы
```

## API Routes

- `/danbooru/logs/batch` — приём логов с фронтенда
- `/danbooru_gallery/get_sampler_node_types` — список KSampler-типов
- `/styleselector/*` — 10 эндпоинтов для управления стилями и базами

## FSD_PIPE

Ключевая концепция — словарь `FSD_PIPE`, передающийся между узлами как единый контекст:

```
{
  model, clip, vae, positive, negative, latent, image, mask,
  seed, steps, cfg, sampler_name, scheduler, denoise,
  pos_text, neg_text, syntax_mode, ...custom keys
}
```

Поддерживает A1111-синтаксис: веса `(tag:1.2)`, чередование `[A|B]`, расписание `[from:to:when]`, wildcards `{A|B|C}`.

## Лицензия

MIT
