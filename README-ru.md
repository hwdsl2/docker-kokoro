[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Kokoro — синтез речи на Docker

[![Статус сборки](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml) &nbsp;[![Лицензия: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT) &nbsp;[![Открыть в Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://vpnsetup.net/kokoro-notebook)

Docker-образ для запуска сервера синтеза речи [Kokoro](https://github.com/hexgrad/kokoro). Предоставляет API синтеза речи, совместимый с OpenAI. Основан на Debian (python:3.12-slim). Разработан для простого, приватного, самостоятельно размещаемого развёртывания.

**Возможности:**

- Совместимый с OpenAI эндпоинт `POST /v1/audio/speech` — любое приложение, использующее OpenAI TTS API, переключается с изменением одной строки
- 54 высококачественных голоса на 9 языках (английский, японский, китайский, испанский, французский, итальянский и другие)
- Поддерживает как имена голосов OpenAI (`alloy`, `nova`, `echo`, ...), так и нативные идентификаторы Kokoro (`af_heart`, `bm_george`, ...)
- Аудио остаётся на вашем сервере — данные не передаются третьим лицам
- Все основные форматы вывода: `mp3`, `wav`, `flac`, `opus`, `aac`, `pcm`
- Поддержка стриминга — установите `stream=true`, чтобы получать аудио по мере синтеза каждого предложения, сокращая время до первого звука
- Аппаратное ускорение на GPU NVIDIA (CUDA) для более быстрого вывода (тег образа `:cuda`)
- Офлайн/изолированный режим — работа без интернета с предварительно кешированной моделью (`KOKORO_LOCAL_ONLY`)
- Автоматическая сборка и публикация через [GitHub Actions](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml)
- Постоянный кеш модели через том Docker
- Мультиархитектурный: `linux/amd64`, `linux/arm64`

**Также доступно:**

- Попробовать онлайн: [Открыть в Colab](https://vpnsetup.net/kokoro-notebook) — Docker и установка не требуются
- ИИ/Аудио: [Whisper (STT)](https://github.com/hwdsl2/docker-whisper/blob/main/README-ru.md), [Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-ru.md), [LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-ru.md), [Ollama (LLM)](https://github.com/hwdsl2/docker-ollama/blob/main/README-ru.md)
- VPN: [WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-ru.md), [OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-ru.md), [IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-ru.md), [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-ru.md)
- Инструменты: [MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-ru.md)

**Совет:** Whisper, Kokoro, Embeddings, LiteLLM, Ollama и MCP-шлюз можно [использовать совместно](#использование-с-другими-ai-сервисами) для построения полного self-hosted AI-стека на собственном сервере. См. [Docker AI Stack](https://github.com/hwdsl2/docker-ai-stack) — готовые конфигурации и примеры конвейеров.

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

**Требования:** GPU NVIDIA, [драйвер NVIDIA](https://www.nvidia.com/en-us/drivers/) 535+, а также [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), установленные на хосте. Образ `:cuda` поддерживает только `linux/amd64`.

</details>

**Важно:** Этот образ требует не менее 1,5 ГБ свободной оперативной памяти из-за среды выполнения PyTorch и модели Kokoro. Системы с 1 ГБ ОЗУ и менее не поддерживаются.

**Примечание:** Для развёртываний, доступных из интернета, **настоятельно рекомендуется** использовать [обратный прокси](#использование-обратного-прокси) для добавления HTTPS. В этом случае также замените `-p 8880:8880` на `-p 127.0.0.1:8880:8880` в команде `docker run`, чтобы предотвратить прямой доступ к незашифрованному порту. Установите `KOKORO_API_KEY` в файле `env`, когда сервер доступен из публичного интернета.

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
- [Драйвер NVIDIA](https://www.nvidia.com/en-us/drivers/) версии 535 или выше, установленный на хосте
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

Все переменные необязательны. Задайте `KOKORO_API_KEY` для включения аутентификации Bearer Token.

Этот Docker-образ использует следующие переменные, которые можно объявить в файле `env` (см. [пример](kokoro.env.example)):

| Переменная | Описание | По умолчанию |
|---|---|---|
| `KOKORO_VOICE` | Голос по умолчанию для синтеза. См. [доступные голоса](#доступные-голоса). Принимает идентификаторы голосов Kokoro (`af_heart`) или псевдонимы OpenAI (`alloy`). | `af_heart` |
| `KOKORO_SPEED` | Скорость речи по умолчанию. Диапазон: `0.25` (медленнее) до `4.0` (быстрее). | `1.0` |
| `KOKORO_PORT` | HTTP-порт для API (1–65535). | `8880` |
| `KOKORO_LANG_CODE` | Если задано, при запуске загружается только конвейер для указанного языка (`a`=американский английский, `b`=британский английский, `e`=испанский, `f`=французский, `h`=хинди, `i`=итальянский, `j`=японский, `p`=бразильский португальский, `z`=китайский мандаринский). Если не задано, конвейер выбирается автоматически по префиксу `KOKORO_VOICE`. Конвейеры для других языков создаются по запросу при необходимости. | *(не задано)* |
| `KOKORO_API_KEY` | Необязательный Bearer-токен. Если задан, все запросы к API должны содержать `Authorization: Bearer <key>`. | *(не задано)* |
| `KOKORO_LOG_LEVEL` | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `KOKORO_LOCAL_ONLY` | При установке любого непустого значения (например, `true`) отключает все загрузки моделей с HuggingFace. Для офлайн или изолированных развёртываний с предварительно кешированной моделью. | *(не задано)* |

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
```

**Примечание:** Для развёртываний, доступных из интернета, настоятельно рекомендуется добавить HTTPS с помощью [обратного прокси](#использование-обратного-прокси). В этом случае замените `"8880:8880/tcp"` на `"127.0.0.1:8880:8880/tcp"` в `docker-compose.yml`, чтобы предотвратить прямой доступ к незашифрованному порту. Установите `KOKORO_API_KEY` в файле `env`, когда сервер доступен из публичного интернета.

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
```

</details>

## Справочник API

API полностью совместим с [эндпоинтом синтеза речи OpenAI](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create). Любое приложение, уже вызывающее `https://api.openai.com/v1/audio/speech`, может переключиться на самостоятельно размещённый сервер, установив:

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
| `voice` | строка | ✅ | Используемый голос. См. [доступные голоса](#доступные-голоса). Принимает идентификаторы Kokoro или псевдонимы OpenAI. |
| `response_format` | строка | — | Формат вывода. По умолчанию: `mp3`. Варианты: `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`. |
| `speed` | число | — | Скорость речи. По умолчанию: `1.0`. Диапазон: `0.25`–`4.0`. |
| `stream` | булево | — | Потоковая передача аудио по мере синтеза. По умолчанию: `false`. При значении `true` фрагменты аудио передаются через chunked transfer encoding по мере готовности каждого предложения, сокращая время до первого звука. `pcm` и `wav` — наиболее эффективные форматы для стриминга; `mp3` и `aac` также поддерживают потоковую передачу. |
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

При доступе сервера из публичного интернета установите `KOKORO_API_KEY` в файле `env`.

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

Образы [Whisper (STT)](https://github.com/hwdsl2/docker-whisper/blob/main/README-ru.md), [Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-ru.md), [LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-ru.md), [Kokoro (TTS)](https://github.com/hwdsl2/docker-kokoro/blob/main/README-ru.md), [Ollama (LLM)](https://github.com/hwdsl2/docker-ollama/blob/main/README-ru.md) и [MCP-шлюз](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-ru.md) можно объединить для создания полного self-hosted AI-стека на собственном сервере — от голосового ввода/вывода до RAG-поиска с ответами. Whisper, Kokoro и Embeddings работают полностью локально. Ollama выполняет весь инференс LLM локально, данные не отправляются третьим сторонам. Если вы настроите LiteLLM с внешними провайдерами (например, OpenAI, Anthropic), ваши данные будут переданы этим провайдерам для обработки.

| Сервис | Назначение | Порт по умолчанию |
|---|---|---|
| **[Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-ru.md)** | Преобразует текст в векторы для семантического поиска и RAG | `8000` |
| **[Whisper (STT)](https://github.com/hwdsl2/docker-whisper/blob/main/README-ru.md)** | Транскрибирует речь в текст | `9000` |
| **[LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-ru.md)** | AI-шлюз — маршрутизирует запросы к OpenAI, Anthropic, Ollama и 100+ другим провайдерам | `4000` |
| **[Kokoro (TTS)](https://github.com/hwdsl2/docker-kokoro/blob/main/README-ru.md)** | Синтезирует естественно звучащую речь из текста | `8880` |
| **[Ollama (LLM)](https://github.com/hwdsl2/docker-ollama/blob/main/README-ru.md)** | Запускает локальные LLM-модели (llama3, qwen, mistral и др.) | `11434` |
| **[MCP-шлюз](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-ru.md)** | Предоставляет сервисы ИИ как MCP-инструменты для ИИ-ассистентов (Claude, Cursor и др.) | `3000` |

**См. также: [Docker AI Stack](https://github.com/hwdsl2/docker-ai-stack)** — готовые docker-compose конфигурации и примеры конвейеров. Узнайте больше о развёртывании полного AI-стека.

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