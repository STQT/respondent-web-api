# 🎥 Руководство по записи видео с веб-камеры

## 📋 Обзор решения

Реализована **гибридная система** записи видео, которая поддерживает:
- ✅ **Загрузку частями** (рекомендуемый подход)
- ✅ **Загрузку одним файлом** (альтернативный подход)
- ✅ **Автоматическую склейку** частей в единый файл

## 🎯 Рекомендуемый подход: Загрузка частями

### Преимущества:
- **Надежность**: Меньше риск потери данных при сбоях
- **Производительность**: Меньше нагрузка на сервер
- **Гибкость**: Можно обрабатывать видео в реальном времени
- **Масштабируемость**: Подходит для длинных сессий

### Недостатки:
- Требует больше API запросов
- Нужна синхронизация на фронтенде

## 📡 Новые API Endpoints

### 1. Загрузка видео части (chunk)
```http
POST /api/proctor/upload-chunk/
Content-Type: multipart/form-data

{
  "session_id": "uuid-сессии",
  "chunk_number": 1,              // Номер части (начинается с 1)
  "video_chunk": "файл-видео",    // Бинарный файл видео
  "duration_seconds": 30.5,       // Длительность части в секундах
  "start_time": 0.0,              // Время начала относительно сессии
  "end_time": 30.5,               // Время окончания относительно сессии
  "has_audio": true,              // Есть ли аудио в части
  "resolution": "1280x720",       // Разрешение видео
  "fps": 30                       // Кадры в секунду
}
```

**Ответ:**
```json
{
  "chunk_id": 123,
  "status": "uploaded",
  "total_chunks": 5
}
```

### 2. Получение всех частей сессии
```http
GET /api/proctor/session/{session_id}/chunks/
```

**Ответ:**
```json
{
  "session_id": "uuid-сессии",
  "total_chunks": 5,
  "total_duration": 150.5,
  "chunks": [
    {
      "chunk_number": 1,
      "duration_seconds": 30.0,
      "file_size": 5242880,
      "start_time": 0.0,
      "end_time": 30.0,
      "uploaded_at": "2025-10-24T00:15:30Z",
      "has_audio": true,
      "resolution": "1280x720",
      "fps": 30
    }
    // ... остальные части
  ]
}
```

### 3. Склейка частей в единый файл
```http
POST /api/proctor/merge-chunks/
Content-Type: application/json

{
  "session_id": "uuid-сессии"
}
```

**Ответ:**
```json
{
  "status": "merged",
  "recording_id": 456,
  "total_duration": 150.5,
  "total_chunks": 5,
  "message": "Video chunks merged successfully"
}
```

### 4. Загрузка полного видео (альтернативный подход)
```http
POST /api/proctor/upload-recording/
Content-Type: multipart/form-data

{
  "session_id": "uuid-сессии",
  "video": "полный-видео-файл",
  "duration_seconds": 900
}
```

## 💻 Frontend Implementation

### JavaScript код для загрузки частями:

```javascript
class VideoRecorder {
    constructor(sessionId, chunkDurationSeconds = 30) {
        this.sessionId = sessionId;
        this.chunkDuration = chunkDurationSeconds;
        this.mediaRecorder = null;
        this.chunks = [];
        this.chunkNumber = 1;
        this.sessionStartTime = Date.now();
        this.isRecording = false;
    }

    async startRecording() {
        try {
            // Запрос доступа к камере
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 }
                },
                audio: true
            });

            // Создание MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm;codecs=vp9,opus'
            });

            // Обработка данных
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.chunks.push(event.data);
                }
            };

            // Обработка остановки
            this.mediaRecorder.onstop = () => {
                this.uploadChunk();
            };

            // Запуск записи
            this.mediaRecorder.start();
            this.isRecording = true;

            // Периодическая отправка частей
            this.startChunkInterval();

            return true;
        } catch (error) {
            console.error('Ошибка при запуске записи:', error);
            return false;
        }
    }

    startChunkInterval() {
        this.chunkInterval = setInterval(() => {
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.stop(); // Остановить для отправки части
                
                // Запустить новую запись
                setTimeout(() => {
                    if (this.isRecording) {
                        this.mediaRecorder.start();
                    }
                }, 100);
            }
        }, this.chunkDuration * 1000);
    }

    async uploadChunk() {
        if (this.chunks.length === 0) return;

        // Создать blob из частей
        const blob = new Blob(this.chunks, { type: 'video/webm' });
        this.chunks = []; // Очистить массив

        // Подготовить данные для отправки
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        formData.append('chunk_number', this.chunkNumber);
        formData.append('video_chunk', blob, `chunk_${this.chunkNumber}.webm`);
        
        const startTime = (this.chunkNumber - 1) * this.chunkDuration;
        const endTime = this.chunkNumber * this.chunkDuration;
        
        formData.append('duration_seconds', this.chunkDuration);
        formData.append('start_time', startTime);
        formData.append('end_time', endTime);
        formData.append('has_audio', 'true');
        formData.append('resolution', '1280x720');
        formData.append('fps', '30');

        try {
            const response = await fetch('/api/proctor/upload-chunk/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                console.log(`Chunk ${this.chunkNumber} uploaded successfully`);
                this.chunkNumber++;
            } else {
                console.error('Ошибка загрузки части:', result);
            }
        } catch (error) {
            console.error('Ошибка при загрузке части:', error);
        }
    }

    async stopRecording() {
        this.isRecording = false;
        
        if (this.chunkInterval) {
            clearInterval(this.chunkInterval);
        }

        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }

        // Загрузить оставшиеся части
        if (this.chunks.length > 0) {
            await this.uploadChunk();
        }

        // Склеить все части
        await this.mergeChunks();
    }

    async mergeChunks() {
        try {
            const response = await fetch('/api/proctor/merge-chunks/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                console.log('Видео успешно склеено:', result);
                return result;
            } else {
                console.error('Ошибка склейки видео:', result);
            }
        } catch (error) {
            console.error('Ошибка при склейке видео:', error);
        }
    }

    async getChunks() {
        try {
            const response = await fetch(`/api/proctor/session/${this.sessionId}/chunks/`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            const result = await response.json();
            
            if (response.ok) {
                return result;
            } else {
                console.error('Ошибка получения частей:', result);
            }
        } catch (error) {
            console.error('Ошибка при получении частей:', error);
        }
    }

    getAuthToken() {
        // Получить токен аутентификации
        return localStorage.getItem('access_token') || '';
    }
}

// Использование
const recorder = new VideoRecorder('session-uuid', 30); // 30 секунд на часть

// Начать запись
await recorder.startRecording();

// Остановить запись
await recorder.stopRecording();
```

## 📊 Рекомендации по размеру частей

### Оптимальные размеры:
- **30 секунд** - для стабильного интернета
- **60 секунд** - для быстрого интернета
- **15 секунд** - для медленного интернета

### Размеры файлов:
- 30 сек видео 720p ≈ 5-10 MB
- 60 сек видео 720p ≈ 10-20 MB
- 15 сек видео 720p ≈ 2-5 MB

## 🔧 Настройки для продакшена

### Рекомендуемые параметры:
```javascript
const videoConstraints = {
    width: { ideal: 1280 },
    height: { ideal: 720 },
    frameRate: { ideal: 30 },
    facingMode: 'user'
};

const audioConstraints = {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
};
```

### Форматы видео:
- **WebM** - лучший для веб (поддерживается всеми браузерами)
- **MP4** - альтернативный формат
- **Кодек**: VP9 для видео, Opus для аудио

## 🚨 Обработка ошибок

### Основные сценарии ошибок:
1. **Потеря соединения** - повторная отправка части
2. **Большой размер файла** - сжатие на клиенте
3. **Недостаток места** - очистка старых записей
4. **Ошибки кодирования** - fallback на другие форматы

### Стратегия восстановления:
```javascript
async uploadChunkWithRetry(chunkData, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const result = await this.uploadChunk(chunkData);
            return result;
        } catch (error) {
            if (i === maxRetries - 1) throw error;
            
            // Экспоненциальная задержка
            await new Promise(resolve => 
                setTimeout(resolve, Math.pow(2, i) * 1000)
            );
        }
    }
}
```

## 📈 Мониторинг и аналитика

### Метрики для отслеживания:
- Количество загруженных частей
- Время загрузки каждой части
- Размеры файлов
- Количество ошибок загрузки
- Качество видео (разрешение, FPS)

### Логирование:
```javascript
console.log(`Chunk ${chunkNumber} uploaded:`, {
    size: blob.size,
    duration: duration,
    uploadTime: Date.now() - startTime,
    timestamp: new Date().toISOString()
});
```

## ✅ Готово к использованию!

Система записи видео частями полностью реализована и готова к использованию:

- ✅ **Модель VideoChunk** создана
- ✅ **API endpoints** реализованы
- ✅ **Миграции** применены
- ✅ **Документация** готова
- ✅ **Примеры кода** предоставлены

**Следующий шаг**: Интеграция с фронтендом согласно примерам выше.

Система готова записывать видео с веб-камеры респондентов! 🎥
