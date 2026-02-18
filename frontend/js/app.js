const API_BASE_URL = 'http://127.0.0.1:5000/api';

// DOM элементы
const studyForm = document.getElementById('studyForm');
const searchBtn = document.getElementById('searchBtn');
const generateBtn = document.getElementById('generateBtn');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const error = document.getElementById('error');

// Функция для показа/скрытия элементов
function showElement(element) {
    element.style.display = 'block';
}

function hideElement(element) {
    element.style.display = 'none';
}

function showLoading() {
    showElement(loading);
    hideElement(results);
    hideElement(error);
}

function hideLoading() {
    hideElement(loading);
}

function showError(message) {
    error.textContent = message;
    showElement(error);
    hideElement(results);
}

function showResults() {
    showElement(results);
    hideElement(error);
}

// ============= ПОИСК ДАННЫХ =============
searchBtn.addEventListener('click', async () => {
    const inn = document.getElementById('inn').value;
    
    if (!inn) {
        showError('Пожалуйста, введите МНН препарата');
        return;
    }
    
    showLoading();
    
    try {
        const formData = {
            inn: inn,
            dosage_form: document.getElementById('dosageForm').value,
            dosage: document.getElementById('dosage').value,
            administration_mode: document.getElementById('administrationMode').value,
            cvintra: document.getElementById('cvintra').value ? parseFloat(document.getElementById('cvintra').value) : null
        };
        
        console.log('Отправляю запрос:', formData);
        
        const response = await fetch(`${API_BASE_URL}/full-analysis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Результаты:', result);
        
        hideLoading();
        showResults();
        
        // Отображение всех результатов
        displayLiteratureResults(result);
        displayPKParameters(result);
        displayDesignResults(result);
        displaySampleSizeResults(result);
        displayRegulatoryResults(result);
        
        // Показываем кнопку скачивания
        document.getElementById('downloadSection').style.display = 'block';
        document.getElementById('downloadBtn').onclick = () => downloadSynopsis(result);
        
    } catch (err) {
        hideLoading();
        console.error('Ошибка:', err);
        showError(`Ошибка поиска данных: ${err.message}`);
    }
});

// ============= ОТОБРАЖЕНИЕ ЛИТЕРАТУРЫ =============
function displayLiteratureResults(result) {
    const literatureContent = document.getElementById('literatureContent');
    
    let html = '';
    
    // PubMed
    html += '<h4>📰 PubMed</h4>';
    const pubmed = result.literature?.pubmed || {};
    if (pubmed.articles && pubmed.articles.length > 0) {
        html += '<ul>';
        pubmed.articles.slice(0, 5).forEach(article => {
            html += `
                <li>
                    <strong>${article.title || 'No title'}</strong><br>
                    <small>${article.authors ? article.authors.join(', ') : 'Unknown'} (${article.year || 'N/A'})</small><br>
                    <a href="${article.url || '#'}" target="_blank" style="color: #667eea;">Открыть</a>
                </li>
            `;
        });
        html += '</ul>';
    } else {
        html += '<p>ℹ️ Статей не найдено (проверьте значение МНН)</p>';
    }
    
    // DrugBank
    html += '<h4>💊 DrugBank</h4>';
    const drugbank = result.literature?.drugbank || {};
    if (drugbank.pharmacokinetics) {
        html += `<p><strong>Препарат:</strong> ${drugbank.name}</p>`;
        html += `<p><strong>Фармакокинетика:</strong> ${drugbank.pharmacokinetics.substring(0, 400)}...</p>`;
        html += `<a href="${drugbank.url || '#'}" target="_blank" style="color: #667eea;">Открыть в DrugBank</a>`;
    } else if (drugbank.name) {
        html += `<p><strong>${drugbank.name}</strong></p>`;
    } else {
        html += '<p>ℹ️ Данных не найдено</p>';
    }
    
    // ГРЛС
    html += '<h4>🏥 ГРЛС (РФ)</h4>';
    const grls = result.literature?.grls || {};
    if (grls.registered_drugs && grls.registered_drugs.length > 0) {
        html += `<p>✅ Найдено ${grls.registered_drugs.length} зарегистрированных препаратов:</p>`;
        html += '<ul>';
        grls.registered_drugs.slice(0, 5).forEach(drug => {
            html += `<li><strong>${drug.name}</strong> - ${drug.dosage_form} (${drug.manufacturer})</li>`;
        });
        html += '</ul>';
    } else {
        html += '<p>ℹ️ Препарат не найден в ГРЛС</p>';
    }
    
    literatureContent.innerHTML = html;
}

// ============= ОТОБРАЖЕНИЕ ФК ПАРАМЕТРОВ =============
function displayPKParameters(result) {
    const pkContent = document.getElementById('pkContent');
    
    let html = `
        <p><strong>Источники данных:</strong></p>
        <ul>
            <li>PubMed - научные публикации и клинические исследования</li>
            <li>DrugBank - фармакокинетические параметры</li>
            <li>ГРЛС - регистрация препарата в РФ</li>
        </ul>
        <p style="color: #888; font-size: 0.9em;">
            💡 Данные обновляются из открытых источников в реальном времени.
            Для полного подробного анализа рекомендуется ручная проверка найденных статей.
        </p>
    `;
    
    pkContent.innerHTML = html;
}

// ============= ОТОБРАЖЕНИЕ ДИЗАЙНА =============
function displayDesignResults(result) {
    const designContent = document.getElementById('designContent');
    
    const design = result.design_recommendation || {};
    let html = `
        <h4 style="color: #667eea;">${design.recommended_design || 'Недостаточно данных'}</h4>
        <p><strong>Обоснование:</strong></p>
        <p>${design.rationale || 'N/A'}</p>
        <p style="color: #666; font-size: 0.9em;">
            Дизайн выбран на основе значения CVintra (внутрисубъектная вариабельность).
        </p>
    `;
    
    designContent.innerHTML = html;
}

// ============= ОТОБРАЖЕНИЕ РАЗМЕРА ВЫБОРКИ =============
function displaySampleSizeResults(result) {
    const sampleSizeContent = document.getElementById('sampleSizeContent');
    
    const ss = result.sample_size || {};
    let html = `
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;"><strong>Параметр</strong></td>
                <td style="padding: 10px;"><strong>Значение</strong></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">Дизайн исследования</td>
                <td style="padding: 10px;"><strong>${ss.design || 'N/A'}</strong></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">CVintra</td>
                <td style="padding: 10px;"><strong>${ss.cvintra || 'N/A'}%</strong></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">Базовый размер (N)</td>
                <td style="padding: 10px;"><strong>${ss.base_sample_size || 'N/A'}</strong></td>
            </tr>
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 10px;">Ожидаемый drop-out</td>
                <td style="padding: 10px;"><strong>${ss.dropout_rate || 'N/A'}%</strong></td>
            </tr>
            <tr style="background-color: #f0f4ff;">
                <td style="padding: 10px; font-weight: bold;">🎯 Итоговый размер выборки</td>
                <td style="padding: 10px; color: #667eea; font-size: 1.2em; font-weight: bold;">${ss.final_sample_size || 'N/A'} участников</td>
            </tr>
        </table>
        
        <h5 style="margin-top: 20px;">📊 Пошаговый расчет:</h5>
        <ol style="line-height: 2;">
    `;
    
    if (ss.calculation_steps && Array.isArray(ss.calculation_steps)) {
        ss.calculation_steps.forEach(step => {
            html += `<li style="font-family: monospace; font-size: 0.9em;">${step}</li>`;
        });
    }
    
    html += '</ol>';
    
    sampleSizeContent.innerHTML = html;
}

// ============= ОТОБРАЖЕНИЕ РЕГУЛЯТОРНЫХ ТРЕБОВАНИЙ =============
function displayRegulatoryResults(result) {
    const regulatoryContent = document.getElementById('regulatoryContent');
    
    const reg = result.regulatory_check || {};
    let html = `
        <h4>Соответствие требованиям</h4>
        
        <div style="padding: 10px; margin: 10px 0; border-radius: 5px; background-color: #f0fff0;">
            <h5>🇷🇺 Решение № 85 (РФ)</h5>
            <p style="color: ${reg.decision_85?.compliant ? 'green' : 'red'};">
                ${reg.decision_85?.compliant ? '✅ Соответствует' : '❌ Не соответствует'}
            </p>
            <p style="font-size: 0.9em;">${reg.decision_85?.requirements || 'N/A'}</p>
        </div>
        
        <div style="padding: 10px; margin: 10px 0; border-radius: 5px; background-color: #f0f8ff;">
            <h5>🇪🇺 EMA Guidelines</h5>
            <p style="color: ${reg.ema?.compliant ? 'green' : 'red'};">
                ${reg.ema?.compliant ? '✅ Соответствует' : '❌ Не соответствует'}
            </p>
            <p style="font-size: 0.9em;">${reg.ema?.requirements || 'N/A'}</p>
        </div>
        
        <div style="padding: 10px; margin: 10px 0; border-radius: 5px; background-color: #fff0f5;">
            <h5>🇺🇸 FDA Guidance</h5>
            <p style="color: ${reg.fda?.compliant ? 'green' : 'red'};">
                ${reg.fda?.compliant ? '✅ Соответствует' : '❌ Не соответствует'}
            </p>
            <p style="font-size: 0.9em;">${reg.fda?.requirements || 'N/A'}</p>
        </div>
    `;
    
    regulatoryContent.innerHTML = html;
}

// ============= ГЕНЕРАЦИЯ СИНОПСИСА =============
studyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        inn: document.getElementById('inn').value,
        dosage_form: document.getElementById('dosageForm').value,
        dosage: document.getElementById('dosage').value,
        administration_mode: document.getElementById('administrationMode').value,
        output_format: document.getElementById('outputFormat').value
    };
    
    const cvintra = document.getElementById('cvintra').value;
    if (cvintra) {
        formData.cvintra = parseFloat(cvintra);
    }
    
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-full-synopsis`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `synopsis_${formData.inn}_${new Date().getTime()}.${formData.output_format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        hideLoading();
        showResults();
        
        document.getElementById('downloadSection').innerHTML = `
            <div class="result-card" style="border-left-color: #28a745; background-color: #f0fff0;">
                <h3>✅ Синопсис успешно сгенерирован!</h3>
                <p>Файл отправлен на скачивание. Проверьте папку "Загрузки".</p>
            </div>
        `;
        
    } catch (err) {
        hideLoading();
        showError(`Ошибка генерации синопсиса: ${err.message}`);
    }
});

// ============= СКАЧИВАНИЕ СИНОПСИСА =============
function downloadSynopsis(result) {
    const format = document.getElementById('outputFormat').value;
    
    const data = {
        inn: result.inn,
        dosage_form: result.dosage_form,
        dosage: result.dosage,
        administration_mode: result.administration_mode,
        literature: result.literature,
        design_recommendation: result.design_recommendation,
        sample_size: result.sample_size,
        regulatory_check: result.regulatory_check,
        output_format: format
    };
    
    showLoading();
    
    fetch(`${API_BASE_URL}/generate-full-synopsis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `synopsis_${data.inn}_${new Date().getTime()}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        hideLoading();
    })
    .catch(err => {
        hideLoading();
        showError(`Ошибка скачивания: ${err.message}`);
    });
}

// ============= ПРОВЕРКА API ПРИ ЗАГРУЗКЕ =============
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('✅ API Status:', data);
    } catch (err) {
        console.error('❌ API недоступен:', err);
        showError('Не удается подключиться к серверу. Убедитесь, что backend запущен на http://127.0.0.1:5000');
    }
});
