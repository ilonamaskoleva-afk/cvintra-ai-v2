// ============================================================
// КОНФИГУРАЦИЯ API
// ============================================================
const API_BASE_URL = (() => {
    if (window.location && window.location.origin && window.location.origin !== 'null') {
        return `${window.location.origin}/api`;
    }
    return 'http://127.0.0.1:8000/api';
})();

console.log('API Base URL:', API_BASE_URL);

// ============================================================
// ИНИЦИАЛИЗАЦИЯ DOM
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initializeNavigation();
    initializeFormHandlers();
    initializeEventListeners();
    checkAPIHealth();
});

// ============================================================
// НАВИГАЦИЯ И UI
// ============================================================
function initializeNavigation() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    if (hamburger && navMenu) {
        hamburger.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });

        // Закрываем меню при клике на ссылку
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
            });
        });
    }
}

function smoothScroll(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// ============================================================
// ОБРАБОТЧИКИ ФОРМ
// ============================================================
function initializeFormHandlers() {
    const studyForm = document.getElementById('studyForm');
    const confidenceSlider = document.getElementById('confidence');

    // Обновление отображения значения confidence
    if (confidenceSlider) {
        confidenceSlider.addEventListener('input', (e) => {
            const valueDisplay = document.querySelector('.confidence-value');
            if (valueDisplay) {
                valueDisplay.textContent = e.target.value + '%';
            }
        });
    }

    // Форма отправки - генерация полного синопсиса
    if (studyForm) {
        studyForm.addEventListener('submit', (e) => {
            e.preventDefault();
            handleGenerateSynopsis();
        });
    }
}

function initializeEventListeners() {
    // Модальное окно
    const modal = document.getElementById('modal');
    const modalClose = document.querySelector('.modal-close');

    if (modalClose) {
        modalClose.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });
    }

    if (modal) {
        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

// ============================================================
// УТИЛИТЫ ДЛЯ UI
// ============================================================

// Enhanced loading with status messages
function showLoading(title = "Анализ данных в процессе...") {
    const loading = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    const errorContainer = document.getElementById('error');

    if (loading) {
        loading.style.display = 'block';
        // Update title
        const titleEl = loading.querySelector('.loading-text');
        if (titleEl) titleEl.textContent = title;
    }
    if (resultsContainer) resultsContainer.style.display = 'none';
    if (errorContainer) errorContainer.style.display = 'none';
}

function updateLoadingStatus(status) {
    const loading = document.getElementById('loading');
    if (loading) {
        const hintEl = loading.querySelector('.loading-hint');
        if (hintEl) hintEl.textContent = status;
    }
}

function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.style.display = 'none';
}

function showResults() {
    const resultsContainer = document.getElementById('results-container');
    const errorContainer = document.getElementById('error');

    if (resultsContainer) resultsContainer.style.display = 'grid';
    if (errorContainer) errorContainer.style.display = 'none';

    // Плавная прокрутка к результатам
    setTimeout(() => {
        const resultsSection = document.getElementById('results');
        if (resultsSection) {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 100);
}

function showError(message) {
    const errorContainer = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    const resultsContainer = document.getElementById('results-container');

    if (errorMessage) errorMessage.textContent = message;
    if (errorContainer) errorContainer.style.display = 'block';
    if (resultsContainer) resultsContainer.style.display = 'none';
}

function closeError() {
    const errorContainer = document.getElementById('error');
    if (errorContainer) errorContainer.style.display = 'none';
}

// ============================================================
// ПОЛУЧЕНИЕ ДАННЫХ ФОРМЫ
// ============================================================
function getFormData() {
    return {
        inn: document.getElementById('inn')?.value || '',
        dosageForm: document.getElementById('dosageForm')?.value || '',
        dosage: document.getElementById('dosage')?.value || '',
        administrationMode: document.getElementById('administrationMode')?.value || '',
        cvintra: document.getElementById('cvintra')?.value || null,
        confidence: parseFloat(document.getElementById('confidence')?.value || 70),
        outputFormat: document.getElementById('outputFormat')?.value || 'json'
    };
}

// ============================================================
// ГЕНЕРАЦИЯ ПОЛНОГО СИНОПСИСА (ONE BUTTON TO RULE THEM ALL)
// ============================================================
async function handleGenerateSynopsis() {
    const formData = getFormData();

    if (!formData.inn.trim()) {
        showError('Пожалуйста, введите МНН препарата');
        return;
    }

    showLoading('Генерирую полный синопсис...');

    try {
        // Show status updates sequentially
        setTimeout(() => updateLoadingStatus('📍 Поиск в локальной БД...'), 500);
        setTimeout(() => updateLoadingStatus('🌍 Проверка PubMed...'), 2000);
        setTimeout(() => updateLoadingStatus('🔄 Анализ данных и расчет дизайна...'), 4000);

        const response = await fetch(`${API_BASE_URL}/full-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                inn: formData.inn,
                dosage_form: formData.dosageForm,
                dosage: formData.dosage,
                administration_mode: formData.administrationMode,
                cvintra: formData.cvintra || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Ошибка HTTP: ${response.status}`);
        }

        const result = await response.json();
        window.lastAnalysisResult = result;

        hideLoading();
        displayCompleteResults(result);
        showResults();

    } catch (err) {
        hideLoading();
        console.error('Ошибка генерации синопсиса:', err);
        showError(`Ошибка генерации синопсиса: ${err.message}`);
    }
}

// ============================================================
// ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ПОИСКА
// ============================================================
function displaySearchResults(result) {
    // CVintra
    const cvintraResults = document.getElementById('cvintraResults');
    if (cvintraResults) {
        const cvintra = result.cvintra || result.design_recommendation?.cvintra || 25;  // Fallback to 25%
        const source = result.cvintra_source || result.design_recommendation?.cvintra_source || 'default';
        const confidence = (result.confidence || result.cvintra_confidence || 0);
        
        // Format source label
        let sourceLabel = '';
        if (source === 'user_input') sourceLabel = ' (пользователь)';
        else if (source === 'pubmed') sourceLabel = ' (PubMed)';
        else if (source === 'database') sourceLabel = ' (база данных)';
        else if (source === 'default') sourceLabel = ' (стандартное значение)';
        
        cvintraResults.innerHTML = `
            <div class="stat-box">
                <div class="stat-value">${cvintra.toFixed(1)}%</div>
                <div class="stat-label">CVintra${sourceLabel}</div>
                <div class="stat-confidence">
                    Уверенность: ${(confidence * 100).toFixed(1)}%
                </div>
            </div>
        `;
    }

    // PK параметры
    displayPKResults(result);

    // Источники
    displaySourceResults(result);

    // Статистика
    displayStatsResults(result);
}

function displayPKResults(result) {
    const pkResults = document.getElementById('pkResults');
    if (!pkResults) return;

    if (!result.articles || result.articles.length === 0) {
        pkResults.innerHTML = '<p class="placeholder-text">Статьи не найдены</p>';
        return;
    }

    let html = '<div style="max-height: 400px; overflow-y: auto;">';
    result.articles.slice(0, 5).forEach(article => {
        html += `
            <div style="padding: 0.75rem; border-bottom: 1px solid var(--color-accent); margin-bottom: 0.75rem;">
                <h5 style="margin: 0 0 0.5rem 0; font-weight: 600; color: var(--color-primary);">
                    ${article.title || 'Без названия'}
                </h5>
                <p style="margin: 0.25rem 0; font-size: 0.9rem; color: var(--color-accent);">
                    ${article.authors?.join(', ') || 'Автор неизвестен'} (${article.year || 'N/A'})
                </p>
                <a href="https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/" target="_blank" 
                   style="color: var(--color-secondary); font-size: 0.85rem; text-decoration: none;">
                    Открыть в PubMed
                </a>
            </div>
        `;
    });
    html += '</div>';

    pkResults.innerHTML = html;
}

function displaySourceResults(result) {
    const sourceResults = document.getElementById('sourceResults');
    if (!sourceResults) return;

    let html = '<div style="space-y: 1rem;">';

    if (result.sources) {
        result.sources.forEach(source => {
            const level = source.reliability >= 0.8 ? 'Высокая' :
                          source.reliability >= 0.6 ? 'Средняя' : 'Низкая';
            
            html += `
                <div style="padding: 1rem; margin-bottom: 0.75rem; background: var(--color-light); border-radius: 8px;">
                    <p style="margin: 0 0 0.5rem 0;">
                        <strong>${source.name}</strong>
                    </p>
                    <p style="margin: 0.25rem 0; font-size: 0.9rem; color: var(--color-accent);">
                        Надежность: <strong>${level} (${(source.reliability * 100).toFixed(0)}%)</strong>
                    </p>
                    ${source.url ? `<a href="${source.url}" target="_blank" style="color: var(--color-secondary); font-size: 0.85rem;">Перейти</a>` : ''}
                </div>
            `;
        });
    }

    html += '</div>';
    sourceResults.innerHTML = html;
}

function displayStatsResults(result) {
    const statsResults = document.getElementById('statsResults');
    if (!statsResults) return;

    const articleCount = result.articles?.length || 0;
    const avgConfidence = result.confidence ? (result.confidence * 100).toFixed(1) : 'N/A';

    statsResults.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="text-align: center; padding: 1rem; background: var(--color-light); border-radius: 8px;">
                <div style="font-size: 1.8rem; font-weight: 700; color: var(--color-primary);">${articleCount}</div>
                <div style="font-size: 0.9rem; color: var(--color-accent);">Статей найдено</div>
            </div>
            <div style="text-align: center; padding: 1rem; background: var(--color-light); border-radius: 8px;">
                <div style="font-size: 1.8rem; font-weight: 700; color: var(--color-secondary);">${avgConfidence}%</div>
                <div style="font-size: 0.9rem; color: var(--color-accent);">Средняя уверенность</div>
            </div>
        </div>
    `;
}

// ============================================================
// ОТОБРАЖЕНИЕ ПОЛНЫХ РЕЗУЛЬТАТОВ АНАЛИЗА
// ============================================================
function displayCompleteResults(result) {
    // Используем те же функции отображения + добавим дизайн исследования
    displaySearchResults(result);

    // Дизайн исследования
    const designResults = document.getElementById('designResults');
    if (designResults) {
        if (result.design_recommendation) {
            designResults.innerHTML = `
                <h4 style="color: var(--color-primary); margin: 0 0 1rem 0;">
                    ${result.design_recommendation.design || result.design_recommendation.recommended_design || 'N/A'}
                </h4>
                <p style="color: var(--color-accent); line-height: 1.6;">
                    ${result.design_recommendation.rationale || 'N/A'}
                </p>
            `;
        } else {
            designResults.innerHTML = '<p class="placeholder-text">Данные не доступны</p>';
        }
    }

    // Размер выборки
    const sampleSizeResults = document.getElementById('sampleSizeResults');
    if (sampleSizeResults) {
        if (result.sample_size) {
            const ss = result.sample_size;
            sampleSizeResults.innerHTML = `
                <div style="background: linear-gradient(135deg, var(--color-light), var(--color-light)); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="font-size: 0.9rem; color: var(--color-accent); margin-bottom: 0.5rem;">Рекомендуемый размер:</div>
                    <div style="font-size: 2rem; font-weight: 700; color: var(--color-primary);">
                        ${ss.final_sample_size || ss.base_sample_size || 'N/A'} участников
                    </div>
                </div>
                <div style="font-size: 0.9rem; color: var(--color-accent);">
                    <p><strong>Дизайн:</strong> ${ss.design || 'N/A'}</p>
                    <p><strong>CVintra:</strong> ${ss.cvintra || 'N/A'}%</p>
                    <p><strong>Expected Drop-out:</strong> ${ss.dropout_rate || 'N/A'}%</p>
                </div>
            `;
        } else {
            sampleSizeResults.innerHTML = '<p class="placeholder-text">Данные не доступны</p>';
        }
    }
}

// ============================================================
// ПРОВЕРКА ЗДОРОВЬЯ API
// ============================================================
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('API healthy:', data);
    } catch (err) {
        console.warn('API unavailable:', err.message);
        // Не показываем ошибку при загрузке, только в консоль
    }
}

// ============================================================
// СТИЛИ ДЛЯ STAT BOXES
// ============================================================
const stylesheet = document.createElement('style');
stylesheet.textContent = `
    .stat-box {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, var(--color-light) 0%, var(--color-light) 100%);
        border-radius: 12px;
        border: 2px solid var(--color-primary);
    }

    .stat-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--color-primary);
        margin-bottom: 0.5rem;
    }

    .stat-label {
        font-size: 0.9rem;
        color: var(--color-accent);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }

    .stat-confidence {
        font-size: 0.85rem;
        color: var(--color-secondary);
        font-weight: 600;
    }
`;
document.head.appendChild(stylesheet);

// Экспортируем функции для использования в HTML
window.smoothScroll = smoothScroll;
window.closeError = closeError;
