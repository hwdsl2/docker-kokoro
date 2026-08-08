[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Kokoro — синтез речи на Docker

[![Статус сборки](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml) &nbsp;[![Docker Pulls](https://raw.githubusercontent.com/hwdsl2/badges/main/img/docker-pulls-kokoro-server.svg)](https://hub.docker.com/r/hwdsl2/kokoro-server) &nbsp;[![Лицензия: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT) &nbsp;[![Открыть в Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://vpnsetup.net/kokoro-notebook)

Часть [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-ru.md) — разверните полный самостоятельно размещённый AI-стек одной командой.

Docker-образ для запуска сервера синтеза речи [Kokoro](https://github.com/hexgrad/kokoro). Предоставляет API синтеза речи, совместимый с OpenAI. Основан на Debian (python:3.12-slim). Разработан для простого, приватного, самостоятельно размещаемого развёртывания.

**Возможности:**

- Совместимый с OpenAI эндпоинт `POST /v1/audio/speech` — любое приложение, использующее OpenAI TTS API, переключается с изменением одной строки
- 54 высококачественных голоса на 9 языках (английский, японский, китайский, испанский, французский, итальянский и другие)
- Поддерживает псевдонимы имён голосов OpenAI (`alloy`, `nova`, `echo`, ...), которые сопоставляются с локальными голосами Kokoro, а также нативные идентификаторы Kokoro (`af_heart`, `bm_george`, ...)
- Аудио остаётся на вашем сервере — данные не передаются третьим лицам
- Все основные форматы вывода: `mp3`, `wav`, `flac`, `opus`, `aac`, `pcm`
- Поддержка стриминга — установите `stream_format` в `"audio"` или `"sse"`, чтобы получать аудио по мере синтеза каждого предложения, сокращая время до первого звука
- Аппаратное ускорение на GPU NVIDIA (CUDA) для более быстрого вывода (тег образа `:cuda`)
- Офлайн/изолированный режим — работа без интернета с предварительно кешированной моделью (`KOKORO_LOCAL_ONLY`)
- Автоматическая сборка и публикация через [GitHub Actions](https://github.com/hwdsl2/docker-kokoro/actions)
- Постоянный кеш модели через том Docker
- Мультиархитектурный: `linux/amd64`, `linux/arm64`

**Также доступно:**

- AI-стек: [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-ru.md)
- Попробовать онлайн: [Открыть в Colab](https://vpnsetup.net/kokoro-notebook) — Docker и установка не требуются
- Связанные AI-сервисы: [Whisper](https://github.com/hwdsl2/docker-whisper/blob/main/README-ru.md), [Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-ru.md), [LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-ru.md), [Ollama](https://github.com/hwdsl2/docker-ollama/blob/main/README-ru.md), [Docling](https://github.com/hwdsl2/docker-docling/blob/main/README-ru.md), [MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-ru.md)
- Книга: [The Self-Hosted AI Builder’s Guide](https://books2read.com/aiguide?store=amazon) — используйте этот сервис в составе полного приватного AI-стека

## Сообщество

- 📬 [Подписаться на обновления проектов](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai-ru) (1–2 письма в месяц) — получить бесплатные руководства по развёртыванию AI и VPN (PDF, на английском)
- 💬 Присоединяйтесь к сообществу [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) для обсуждений и демонстрации проектов
- ⭐ Поставьте звезду репозиторию, если он оказался вам полезен — это поможет другим пользователям его найти.

<details>
<summary>Самостоятельно размещаемые VPN и сетевые проекты</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn/blob/master/README-ru.md)
- [IPsec VPN на Docker](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-ru.md)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-ru.md)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-ru.md)
- [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-ru.md)

</details>

## Быстрый старт

Запустите сервер Kokoro TTS следующей командой:

```bash
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

<details>
<summary><strong>Быстрый старт с GPU (NVIDIA CUDA)</strong></summary>

Если у вас есть GPU NVIDIA, используйте образ `:cuda` для аппаратного ускорения:

```bash
docker run \
    --name kokoro \
    --restart=always \
    --gpus=all \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server:cuda
```

**Требования:** GPU NVIDIA, [драйвер NVIDIA](https://www.nvidia.com/en-us/drivers/) 575.57.08+ (Linux) или 576.57+ (Windows), а также [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), установленные на хосте. Образ `:cuda` поддерживает только `linux/amd64`.

</details>

**Важно:** Этот образ требует не менее 1,5 ГБ свободной оперативной памяти из-за среды выполнения PyTorch и модели Kokoro. Системы с 1 ГБ ОЗУ и менее не поддерживаются.

**Примечание:** Для развёртываний, доступных из интернета, **настоятельно рекомендуется** использовать [обратный прокси](#использование-обратного-прокси) для добавления HTTPS. В этом случае также замените `-p 8880:8880` на `-p 127.0.0.1:8880:8880` в команде `docker run`, чтобы предотвратить прямой доступ к незашифрованному порту.

Модель Kokoro (~320 МБ) загружается и кешируется при первом запуске. Проверьте журналы, чтобы убедиться, что сервер готов:

```bash
docker logs kokoro
```

После появления сообщения «Kokoro text-to-speech server is ready» синтезируйте первый аудиофайл:

```bash
curl http://IP_вашего_сервера:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Привет, мир!","voice":"af_heart"}' \
    --output speech.mp3
```

## Требования

- Сервер Linux (локальный или облачный) с установленным Docker
- Поддерживаемые архитектуры: `amd64` (x86_64), `arm64` (например, Raspberry Pi 4/5, AWS Graviton)
- Минимальная свободная ОЗУ: ~1,5 ГБ (модель ~320 МБ; среде выполнения PyTorch требуется дополнительная память)
- Интернет-доступ для первоначальной загрузки модели (после этого модель кешируется локально). Не требуется при использовании `KOKORO_LOCAL_ONLY=true` с предварительно кешированной моделью.

**Требования для ускорения на GPU (образ `:cuda`):**

- GPU NVIDIA с поддержкой CUDA (Compute Capability 6.0+)
- [Драйвер NVIDIA](https://www.nvidia.com/en-us/drivers/) 575.57.08+ (Linux) или 576.57+ (Windows), установленный на хосте
- Установленный [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- Образ `:cuda` поддерживает только `linux/amd64`

Для развёртываний, доступных из интернета, см. [Использование обратного прокси](#использование-обратного-прокси).

## Скачать

Получите доверенную сборку из [Docker Hub](https://hub.docker.com/r/hwdsl2/kokoro-server/):

```bash
docker pull hwdsl2/kokoro-server
```

Для ускорения на GPU NVIDIA загрузите тег `:cuda`:

```bash
docker pull hwdsl2/kokoro-server:cuda
```

Либо скачайте из [Quay.io](https://quay.io/repository/hwdsl2/kokoro-server):

```bash
docker pull quay.io/hwdsl2/kokoro-server
docker image tag quay.io/hwdsl2/kokoro-server hwdsl2/kokoro-server
```

Поддерживаемые платформы: `linux/amd64` и `linux/arm64`. Тег `:cuda` поддерживает только `linux/amd64`.

## Переменные окружения

Все переменные необязательны. Новые установки с подключённым томом `/var/lib/kokoro` автоматически генерируют Bearer-токен. Существующие установки без ключа остаются открытыми для обратной совместимости.

Этот Docker-образ использует следующие переменные, которые можно объявить в файле `env` (см. [пример](kokoro.env.example)):

| Переменная | Описание | По умолчанию |
|---|---|---|
| `KOKORO_VOICE` | Голос по умолчанию для синтеза. См. [доступные голоса](#доступные-голоса). Принимает идентификаторы голосов Kokoro (`af_heart`) или псевдонимы OpenAI (`alloy`, `ballad` и т. д.). | `af_heart` |
| `KOKORO_SPEED` | Скорость речи по умолчанию. Диапазон: `0.25` (медленнее) до `4.0` (быстрее). | `1.0` |
| `KOKORO_PORT` | HTTP-порт для API (1–65535). | `8880` |
| `KOKORO_LANG_CODE` | Если задано, при запуске загружается только конвейер для указанного языка (`a`=американский английский, `b`=британский английский, `e`=испанский, `f`=французский, `h`=хинди, `i`=итальянский, `j`=японский, `p`=бразильский португальский, `z`=китайский мандаринский). Если не задано, конвейер выбирается автоматически по префиксу `KOKORO_VOICE`. Конвейеры для других языков создаются по запросу при необходимости. | *(не задано)* |
| `KOKORO_API_KEY` | Необязательный Bearer-токен. В новых постоянных установках генерируется автоматически. Если задан, все запросы к API должны содержать `Authorization: Bearer <key>`. Явно пустое значение отключает аутентификацию. | Автоматически для новых постоянных установок |
| `KOKORO_LOG_LEVEL` | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `KOKORO_LOCAL_ONLY` | При установке любого непустого значения (например, `true`) отключает все загрузки моделей с HuggingFace. Для офлайн или изолированных развёртываний с предварительно кешированной моделью. | *(не задано)* |
| `KOKORO_DISABLE_USAGE_COUNTS` | Установите `1`, чтобы отключить анонимные агрегированные счётчики использования. | *(не задано)* |

**Примечание:** В файле `env` значения можно заключать в одинарные кавычки, например `VAR='value'`. Не добавляйте пробелы вокруг `=`. При изменении `KOKORO_PORT` обновите флаг `-p` в команде `docker run` соответствующим образом.

Пример использования файла `env`:

```bash
cp kokoro.env.example kokoro.env
# Отредактируйте kokoro.env, затем:
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -v ./kokoro.env:/kokoro.env:ro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

Файл env монтируется в контейнер, изменения применяются при каждом перезапуске без пересоздания контейнера.

<details>
<summary>Либо передайте через <code>--env-file</code></summary>

```bash
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    --env-file=kokoro.env \
    -d hwdsl2/kokoro-server
```

</details>

## Использование docker-compose

```bash
cp kokoro.env.example kokoro.env
# Отредактируйте kokoro.env при необходимости, затем:
docker compose up -d
docker logs kokoro
```

Пример `docker-compose.yml` (уже включён в проект):

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # Для хост-обратного прокси замените на "127.0.0.1:8880:8880/tcp"
    volumes:
      - kokoro-data:/var/lib/kokoro
      - ./kokoro.env:/kokoro.env:ro

volumes:
  kokoro-data:
    name: kokoro-data
```

**Примечание:** Для развёртываний, доступных из интернета, настоятельно рекомендуется добавить HTTPS с помощью [обратного прокси](#использование-обратного-прокси). В этом случае замените `"8880:8880/tcp"` на `"127.0.0.1:8880:8880/tcp"` в `docker-compose.yml`, чтобы предотвратить прямой доступ к незашифрованному порту.

<details>
<summary><strong>Использование docker-compose с GPU (NVIDIA CUDA)</strong></summary>

Для развёртывания с GPU предусмотрен отдельный файл `docker-compose.cuda.yml`:

```bash
cp kokoro.env.example kokoro.env
# Отредактируйте kokoro.env при необходимости, затем:
docker compose -f docker-compose.cuda.yml up -d
docker logs kokoro
```

Пример `docker-compose.cuda.yml` (уже включён в проект):

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server:cuda
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # Для хост-обратного прокси замените на "127.0.0.1:8880:8880/tcp"
    volumes:
      - kokoro-data:/var/lib/kokoro
      - ./kokoro.env:/kokoro.env:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  kokoro-data:
    name: kokoro-data
```

</details>

## Справочник API

API совместим с [эндпоинтом синтеза речи OpenAI](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create). Любое приложение, уже вызывающее `https://api.openai.com/v1/audio/speech`, может переключиться на самостоятельно размещённый сервер, установив:

Имена голосов OpenAI принимаются как локальные псевдонимы для совместимости клиентов. Эти псевдонимы сопоставляются с голосами Kokoro и не воспроизводят проприетарные голоса OpenAI. Поле `voice` может быть строкой или объектом с полем `id`; неизвестные голоса возвращают `400`.

```
OPENAI_BASE_URL=http://IP_вашего_сервера:8880
```

### Синтез речи

```
POST /v1/audio/speech
Content-Type: application/json
```

**Тело запроса:**

| Поле | Тип | Обязательно | Описание |
|---|---|---|---|
| `model` | строка | ✅ | Передайте `tts-1`, `tts-1-hd` или `kokoro` (все используют Kokoro-82M). |
| `input` | строка | ✅ | Текст для синтеза. Максимум 4096 символов. |
| `voice` | строка или объект | ✅ | Используемый голос. См. [доступные голоса](#доступные-голоса). Принимает идентификаторы Kokoro, псевдонимы OpenAI, сопоставляемые с локальными голосами Kokoro, или объект с полем `id`. Неизвестные голоса возвращают `400`. |
| `response_format` | строка | — | Формат вывода. По умолчанию: `mp3`. Варианты: `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`. `pcm` — это необработанный моноаудиопоток 24 кГц без заголовка: 16-битные знаковые сэмплы little-endian. |
| `speed` | число | — | Скорость речи. По умолчанию: `1.0`. Диапазон: `0.25`–`4.0`. |
| `instructions` | строка | — | Управление голосом с помощью дополнительных инструкций. Принимается для совместимости с API, но в настоящее время не поддерживается движком Kokoro (игнорируется). |
| `stream_format` | строка | — | Формат потоковой передачи аудио. Варианты: `audio`, `sse`. При значении `audio` аудио передаётся через chunked transfer encoding. При значении `sse` ответ использует Server-Sent Events с событиями `speech.audio.delta` и `speech.audio.done` (потоковый протокол речи OpenAI). Для SSE WAV первый delta содержит потоковый WAV-заголовок, последующие delta — необработанный PCM_S16LE, 24 kHz mono. SSE PCM delta — это необработанный PCM_S16LE, 24 kHz mono, без заголовка. При отсутствии возвращается полное аудио. |
| `volume_multiplier` | число | — | Множитель громкости вывода. По умолчанию: `1.0`. Диапазон: `0.1`–`2.0`. Значения выше `1.0` усиливают, ниже `1.0` ослабляют сигнал. Сэмплы обрезаются после масштабирования для предотвращения искажений. |

**Пример:**

```bash
curl http://IP_вашего_сервера:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Быстрая коричневая лиса прыгает через ленивую собаку.","voice":"af_heart"}' \
    --output speech.mp3
```

С другим голосом и форматом:

```bash
curl http://IP_вашего_сервера:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello from London.","voice":"bm_george","response_format":"wav","speed":0.9}' \
    --output speech.wav
```

С аутентификацией по API-ключу:

```bash
curl http://IP_вашего_сервера:8880/v1/audio/speech \
    -H "Authorization: Bearer your_api_key" \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello world","voice":"nova"}' \
    --output speech.mp3
```

**Ответ:** Бинарные аудиоданные с соответствующим заголовком `Content-Type`.

### Список голосов

```
GET /v1/voices
```

Возвращает все доступные идентификаторы голосов Kokoro и их сопоставление с псевдонимами OpenAI.

```bash
curl http://IP_вашего_сервера:8880/v1/voices
```

### Список моделей

```
GET /v1/models
```

Возвращает активные модели в совместимом с OpenAI формате.

```bash
curl http://IP_вашего_сервера:8880/v1/models
```

### Интерактивная документация API

Интерактивный Swagger UI доступен по адресу:

```
http://IP_вашего_сервера:8880/docs
```

## Доступные голоса

В любое время используйте `kokoro_manage --listvoices` для просмотра полного списка:

```bash
docker exec kokoro kokoro_manage --listvoices
```

**Американский английский:**

| Идентификатор голоса | Пол | Стиль |
|---|---|---|
| `af_heart` | Женский | Тёплый, естественный — **по умолчанию** |
| `af_aoede` | Женский | |
| `af_bella` | Женский | Выразительный |
| `af_jessica` | Женский | Энергичный |
| `af_kore` | Женский | |
| `af_nicole` | Женский | Дружелюбный |
| `af_nova` | Женский | Чёткий |
| `af_river` | Женский | Спокойный |
| `af_sarah` | Женский | Разговорный |
| `af_sky` | Женский | Нейтральный, универсальный |
| `af_alloy` | Женский | Сбалансированный |
| `am_adam` | Мужской | Глубокий |
| `am_michael` | Мужской | Чёткий |
| `am_echo` | Мужской | Нейтральный |
| `am_eric` | Мужской | Авторитетный |
| `am_fenrir` | Мужской | Своеобразный |
| `am_liam` | Мужской | Разговорный |
| `am_onyx` | Мужской | Насыщенный |
| `am_puck` | Мужской | Выразительный |
| `am_santa` | Мужской | Тёплый |

**Британский английский:**

| Идентификатор голоса | Пол | Стиль |
|---|---|---|
| `bf_emma` | Женский | Чёткий, профессиональный |
| `bf_isabella` | Женский | Тёплый |
| `bf_alice` | Женский | Звонкий |
| `bf_lily` | Женский | Мягкий |
| `bm_george` | Мужской | Авторитетный |
| `bm_lewis` | Мужской | Плавный |
| `bm_daniel` | Мужской | Спокойный |
| `bm_fable` | Мужской | Выразительный |

**Японский:** `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`

**Китайский (мандаринский):** `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`

**Испанский:** `ef_dora`, `em_alex`, `em_santa`

**Французский:** `ff_siwis`

**Хинди:** `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`

**Итальянский:** `if_sara`, `im_nicola`

**Бразильский португальский:** `pf_dora`, `pm_alex`, `pm_santa`

**Псевдонимы голосов OpenAI:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`, `ash`, `coral`, `sage`, `verse`, `ballad`, `marin`, `cedar` (сопоставляются с локальными голосами Kokoro).

> **Совет:** Сервер автоматически выбирает нужный языковой конвейер по префиксу идентификатора голоса — никакой настройки не требуется. Например, `jf_alpha` загружает японский конвейер, `bf_emma` — британский английский. Конвейеры для других языков создаются по запросу при необходимости.

Все голоса используют один общий файл модели (~320 МБ). При переключении голосов повторная загрузка не требуется.

## Постоянные данные

Все данные сервера хранятся в Docker-томе (`/var/lib/kokoro` внутри контейнера):

```
/var/lib/kokoro/
├── hub/                           # Кэшированные файлы модели Kokoro (загружены с HuggingFace)
├── .port                          # Активный порт (используется kokoro_manage)
├── .voice                         # Активный голос по умолчанию (используется kokoro_manage)
└── .server_addr                   # Кэшированный IP сервера (используется kokoro_manage)
```

Создайте резервную копию Docker-тома для сохранения загруженной модели. Модель занимает ~320 МБ и загружается только один раз.

## Управление сервером

Используйте `kokoro_manage` внутри работающего контейнера для проверки и управления сервером.

**Показать информацию о сервере:**

```bash
docker exec kokoro kokoro_manage --showinfo
```

**Список доступных голосов:**

```bash
docker exec kokoro kokoro_manage --listvoices
```

## Смена голоса

Чтобы изменить голос по умолчанию, обновите `KOKORO_VOICE` в файле `kokoro.env` и перезапустите контейнер. Повторная загрузка модели не требуется — все голоса используют одну модель Kokoro-82M.

```bash
# Отредактируйте kokoro.env: задайте KOKORO_VOICE=bm_george
docker restart kokoro
```

> **Примечание:** В отдельных запросах к API всегда можно указать другой голос через поле `voice`, независимо от значения по умолчанию в контейнере.

## Защита сервера

Если ваш сервер Kokoro TTS доступен из публичной сети — даже кратковременно — примените как минимум следующие меры защиты. Kokoro требует значительных ресурсов CPU/GPU, поэтому неаутентифицированная конечная точка может быть использована для расходования ваших вычислительных ресурсов.

**1. Используйте API-ключ.** Новые установки с подключённым томом `/var/lib/kokoro` автоматически генерируют API-ключ. Его можно посмотреть командой `docker exec kokoro kokoro_manage --showkey`; в скриптах используйте `docker exec kokoro kokoro_manage --getkey`. Существующие установки без ключа остаются открытыми для обратной совместимости; также можно задать `KOKORO_API_KEY` в env-файле вручную. Все аутентифицированные запросы должны содержать `Authorization: Bearer <key>`.

```bash
# Сгенерировать 32-байтовый случайный ключ
openssl rand -hex 32
```

**2. Привяжите к localhost при использовании обратного прокси.** Замените `-p 8880:8880` на `-p 127.0.0.1:8880:8880` (или измените `"8880:8880/tcp"` на `"127.0.0.1:8880:8880/tcp"` в `docker-compose.yml`), чтобы незашифрованный порт нельзя было достичь напрямую снаружи хоста.

**3. Ограничьте размер тела запроса на прокси.** Запросы к TTS содержат текстовый ввод; настройте обратный прокси на отклонение слишком больших тел запросов (например, nginx `client_max_body_size 1M;`).

**4. Следите за уровнем журналирования.** При `KOKORO_LOG_LEVEL=DEBUG` входной текст может попадать в журналы. На общих системах сохраняйте уровень `INFO` или выше.

**5. Включите CORS на прокси при вызове из браузера.** Сервер по умолчанию не устанавливает заголовки `Access-Control-Allow-Origin`; добавьте их на обратном прокси, если планируете вызывать API напрямую с веб-страницы другого источника.

**6. Рассмотрите ограничение частоты запросов.** Разместите перед сервером ограничитель частоты (например, nginx `limit_req_zone`, Caddy `rate_limit`), чтобы ограничить количество одновременных запросов на синтез на один IP-адрес клиента.

## Использование обратного прокси

Для развёртываний, доступных из интернета, разместите обратный прокси перед TTS-сервером для обработки завершения HTTPS.

Используйте один из следующих адресов для доступа к контейнеру TTS из обратного прокси:

- **`kokoro:8880`** — если обратный прокси работает как контейнер в **той же сети Docker**, что и TTS-сервер.
- **`127.0.0.1:8880`** — если обратный прокси работает **на хосте** и порт `8880` опубликован.

**Пример с [Caddy](https://caddyserver.com/docs/) ([Docker-образ](https://hub.docker.com/_/caddy))** (автоматический TLS через Let's Encrypt, обратный прокси в той же Docker-сети):

`Caddyfile`:
```
kokoro.example.com {
  reverse_proxy kokoro:8880
}
```

**Пример с nginx** (обратный прокси на хосте):

```nginx
server {
    listen 443 ssl;
    server_name kokoro.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass         http://127.0.0.1:8880;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

## Обновление Docker-образа

Для обновления Docker-образа и контейнера сначала [скачайте](#скачать) последнюю версию:

```bash
docker pull hwdsl2/kokoro-server
```

Если образ уже актуален, вы увидите:

```
Status: Image is up to date for hwdsl2/kokoro-server:latest
```

В противном случае будет скачана последняя версия. Удалите и пересоздайте контейнер:

```bash
docker rm -f kokoro
# Затем повторно выполните команду docker run из раздела «Быстрый старт» с теми же томом и портом.
```

Скачанные модели сохранятся в томе `kokoro-data`.

## Использование с другими AI-сервисами

Kokoro можно использовать как службу синтеза речи в более широком self-hosted AI-стеке.

Готовые полные и облегчённые стеки Docker Compose, примеры ручного запуска через `docker run`, а также примеры голосовых, RAG- и MCP-конвейеров с Kokoro, Embeddings, LiteLLM, Ollama, Docling и MCP Gateway см. в [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-ru.md).

## Счётчики использования

Этот образ использует публичные счётчики скачиваний GitHub Release assets для анонимной агрегированной статистики использования. Эти числа приблизительны и не являются количеством уникальных пользователей или активных установок. Образ не отправляет telemetry payload и не использует частный сборщик. Он выполняет только best-effort запрос после успешного запуска сервера с подключённым томом `/var/lib/kokoro`, а также при первом запуске другой сборки образа для этой постоянной установки. Чтобы отключить это, задайте `KOKORO_DISABLE_USAGE_COUNTS=1`.

## Технические подробности

- Базовый образ: `python:3.12-slim` (Debian)
- Среда выполнения: Python 3 (виртуальное окружение в `/opt/venv`)
- TTS-движок: [Kokoro](https://github.com/hexgrad/kokoro) (Kokoro-82M, Apache 2.0) с PyTorch (CPU и CUDA GPU)
- API-фреймворк: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- Аудиокодирование: [soundfile](https://github.com/bastibe/python-soundfile) (wav/flac), [ffmpeg](https://ffmpeg.org/) (mp3/aac/opus)
- Директория данных: `/var/lib/kokoro` (Docker-том)
- Хранение модели: формат HuggingFace Hub внутри тома — загружается один раз, переиспользуется при перезапусках
- Частота дискретизации: 24 кГц (нативный вывод Kokoro)

## Лицензия

**Примечание:** Программные компоненты внутри готового образа (такие как Kokoro и его зависимости) распространяются под лицензиями, выбранными соответствующими правообладателями. При использовании готового образа пользователь несёт ответственность за соблюдение всех соответствующих лицензий на программное обеспечение, содержащееся в образе.

Copyright (C) 2026 Lin Song   
Данная работа распространяется под [лицензией MIT](https://opensource.org/licenses/MIT).

**Kokoro TTS** является собственностью hexgrad и распространяется под [лицензией Apache 2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE).

Этот проект является независимой Docker-оболочкой для Kokoro и не связан с hexgrad или OpenAI, не одобрен и не спонсирован ими.
