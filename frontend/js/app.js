const API_BASE_URL = 'http://localhost:5000/api';

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

// Поиск данных в базах
searchBtn.addEventListener('click', async () => {
    const inn = document.getElementById('inn').value;
    
    if (!inn) {
        showError('Пожалуйста, введите МНН препарата');
        return;
    }
    
    showLoading();
    
    try {
        // Параллельный поиск во всех базах
        const [pubmedData, drugbankData, grlsData] = await Promise.all([
            fetch(`${API_BASE_URL}/search/pubmed`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inn })
            }).then(res => res.json()),
            
            fetch(`${API_BASE_URL}/search/drugbank`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inn })
            }).then(res => res.json()),
            
            fetch(`${API_BASE_URL}/search/grls`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ inn })
            }).then(res => res.json())
        ]);
        
        hideLoading();
        showResults();
        
        // Отображение результатов литературы
        displayLiteratureResults(pubmedData, drugbankData, grlsData);
        
        // Если CVintra не указан, попытаться определить из литературы
        if (!document.getElementById('cvintra').value) {
            // Здесь можно добавить логику извлечения CVintra
            console.log('CVintra auto-detection not implemented yet');
        }
        
    } catch (err) {
        hideLoading();
        showError(`Ошибка поиска данных: ${err.message}`);
    }
});

// Генерация полного синопсиса
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
        // Полный пайплайн
        const response = await fetch(`${API_BASE_URL}/full_pipeline`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Скачивание файла
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
        
        // Показать сообщение об успехе
        document.getElementById('downloadSection').innerHTML = `
            <div class="result-card" style="border-left-color: #28a745;">
                <h3>✅ Синопсис успешно сгенерирован!</h3>
                <p>Файл автоматически загружен. Если загрузка не началась, проверьте папку "Загрузки".</p>
            </div>
        `;
        showElement(document.getElementById('downloadSection'));
        
    } catch (err) {
        hideLoading();
        showError(`Ошибка генерации синопсиса: ${err.message}`);
    }
});

// Отображение результатов поиска литературы
function displayLiteratureResults(pubmedData, drugbankData, grlsData) {
    const literatureContent = document.getElementById('literatureContent');
    
    let html = '<h4>PubMed</h4>';
    if (pubmedData.articles && pubmedData.articles.length > 0) {
        html += '<ul>';
        pubmedData.articles.slice(0, 5).forEach(article => {
            html += `
                <li>
                    <strong>${article.title}</strong><br>
                    <small>${article.authors.join(', ')} (${article.year})</small><br>
                    <a href="${article.url}" target="_blank">Открыть в PubMed</a>
                </li>
            `;
        });
        html += '</ul>';
    } else {
        html += '<p>Статей не найдено</p>';
    }
    
    html += '<h4>DrugBank</h4>';
    if (drugbankData.pharmacokinetics) {
        html += `<p>${drugbankData.pharmacokinetics.substring(0, 300)}...</p>`;
        html += `<a href="${drugbankData.url}" target="_blank">Открыть в DrugBank</a>`;
    } else {
        html += '<p>Данных не найдено</p>';
    }
    
    html += '<h4>ГРЛС (РФ)</h4>';
    if (grlsData.registered_drugs && grlsData.registered_drugs.length > 0) {
        html += `<p>Найдено ${grlsData.registered_drugs.length} зарегистрированных препаратов</p>`;
    } else {
        html += '<p>Препарат не найден в ГРЛС</p>';
    }
    
    literatureContent.innerHTML = html;
}

// Проверка здоровья API при загрузке
window.addEventListener('load', async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('API Status:', data);
    } catch (err) {
        console.error('API не доступен:', err);
        showError('Не удается подключиться к серверу. Убедитесь, что backend запущен.');
    }
});
