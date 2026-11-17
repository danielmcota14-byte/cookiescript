const api = (path, body) => fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
}).then(resp => resp.json());

const filePathInput = document.getElementById('filePath');
const codeArea = document.getElementById('codeArea');
const promptArea = document.getElementById('promptArea');
const outputArea = document.getElementById('outputArea');
const installMode = document.getElementById('installMode');
const languageSelect = document.getElementById('languageSelect');
const userNameInput = document.getElementById('userName');
const projectNameInput = document.getElementById('projectName');
const projectDescription = document.getElementById('projectDescription');
const currentProjectIdText = document.getElementById('currentProjectId');
const currentProjectVisibilityText = document.getElementById('currentProjectVisibility');
const projectListDiv = document.getElementById('projectList');
const tabBar = document.getElementById('tabBar');
const repoResourcesDiv = document.getElementById('repoResources');
const repoProjectName = document.getElementById('repoProjectName');
const repoProjectVisibility = document.getElementById('repoProjectVisibility');
const settingsTabBar = document.getElementById('settingsTabBar');
const settingsTabSections = {
    generate: document.getElementById('settingsTabGenerate'),
    repo: document.getElementById('settingsTabRepo'),
    wiki: document.getElementById('settingsTabWiki'),
    app: document.getElementById('settingsTabApp'),
    output: document.getElementById('settingsTabOutput'),
    projects: document.getElementById('settingsTabProjects'),
    git: document.getElementById('settingsTabGit'),
    canvas: document.getElementById('settingsTabCanvas')
};
const canvas = document.getElementById('ideCanvas');
const ctx = canvas.getContext('2d');
let currentProjectId = null;
let currentProjectVisibility = 'privado';
let tabs = [];
let activeTabIndex = -1;
let activeSettingsTab = 'generate';

const languageExtension = (language) => {
    if (language === 'python') return 'py';
    if (language === 'javascript') return 'js';
    return 'cookiescript';
};

const getCurrentTab = () => tabs[activeTabIndex] || null;

const getTabTitle = (tab) => {
    if (tab.title) return tab.title;
    if (tab.path) return tab.path.split('/').pop();
    return `novo.${languageExtension(tab.language)}`;
};

const setActiveTab = (index) => {
    if (index < 0 || index >= tabs.length) return;
    activeTabIndex = index;
    const tab = tabs[index];
    filePathInput.value = tab.path || '';
    languageSelect.value = tab.language || 'cookiescript';
    codeArea.value = tab.content || '';
    renderTabs();
    drawCanvas();
};

const renderTabs = () => {
    tabBar.innerHTML = '';
    if (!tabs.length) {
        tabBar.textContent = 'Nenhuma aba aberta';
        return;
    }
    tabs.forEach((tab, index) => {
        const tabItem = document.createElement('div');
        tabItem.className = 'tab-item' + (index === activeTabIndex ? ' active' : '');
        tabItem.title = tab.path || getTabTitle(tab);
        tabItem.textContent = `${getTabTitle(tab)}${tab.dirty ? ' *' : ''}`;
        tabItem.addEventListener('click', () => setActiveTab(index));

        const closeButton = document.createElement('span');
        closeButton.className = 'tab-close';
        closeButton.textContent = '×';
        closeButton.addEventListener('click', (event) => {
            event.stopPropagation();
            closeTab(index);
        });
        tabItem.appendChild(closeButton);
        tabBar.appendChild(tabItem);
    });
};

const createTab = ({ path = '', language = languageSelect.value, content = '', title = '', activate = true } = {}) => {
    const newTab = {
        id: `tab_${Date.now()}_${Math.random().toString(36).slice(2)}`,
        path,
        language,
        content,
        title: title || (path ? path.split('/').pop() : `novo.${languageExtension(language)}`),
        dirty: false
    };
    tabs.push(newTab);
    if (activate) {
        setActiveTab(tabs.length - 1);
    } else {
        renderTabs();
    }
};

const updateCurrentTab = () => {
    const tab = getCurrentTab();
    if (!tab) return;
    tab.content = codeArea.value;
    tab.path = filePathInput.value.trim() || tab.path;
    tab.language = languageSelect.value;
    tab.title = tab.path ? tab.path.split('/').pop() : tab.title;
    tab.dirty = true;
    renderTabs();
};

const closeTab = (index) => {
    if (index < 0 || index >= tabs.length) return;
    const closingActive = index === activeTabIndex;
    tabs.splice(index, 1);
    if (!tabs.length) {
        activeTabIndex = -1;
        filePathInput.value = '';
        codeArea.value = '';
        renderTabs();
        return;
    }
    if (closingActive) {
        setActiveTab(Math.min(index, tabs.length - 1));
    } else if (index < activeTabIndex) {
        activeTabIndex -= 1;
        renderTabs();
    }
};

const newTab = () => {
    createTab({
        path: '',
        language: languageSelect.value,
        content: '',
        title: `novo.${languageExtension(languageSelect.value)}`
    });
};

const drawCanvas = () => {
    const lines = codeArea.value.split('\n').filter(line => line.trim());
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#111827';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#4f46e5';
    ctx.lineWidth = 2;
    ctx.font = '14px Arial';
    ctx.fillStyle = '#e5e7eb';

    ctx.fillText('Fluxo do CookieScript', 16, 28);
    ctx.beginPath();
    ctx.moveTo(18, 42);
    ctx.lineTo(canvas.width - 18, 42);
    ctx.stroke();

    const maxBlocks = 5;
    const blockCount = Math.min(maxBlocks, Math.max(1, lines.length));
    const blockHeight = 38;
    const gap = 16;
    let y = 70;

    for (let i = 0; i < blockCount; i++) {
        const text = lines[i] ? lines[i].slice(0, 32) : '...';
        ctx.fillStyle = '#1f2937';
        ctx.fillRect(18, y, canvas.width - 36, blockHeight);
        ctx.strokeStyle = '#4338ca';
        ctx.strokeRect(18, y, canvas.width - 36, blockHeight);
        ctx.fillStyle = '#f8fafc';
        ctx.fillText(text, 28, y + 24);
        if (i < blockCount - 1) {
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2, y + blockHeight);
            ctx.lineTo(canvas.width / 2, y + blockHeight + gap);
            ctx.stroke();
        }
        y += blockHeight + gap;
    }
};

const showOutput = (text) => {
    outputArea.textContent = text;
};

const showGitOutput = (text) => {
    const gitArea = document.getElementById('gitStatusArea');
    gitArea.textContent = text;
};

const refreshRepositoryResources = async () => {
    const result = await api('/api/files', {});
    if (result.success) {
        renderRepositoryResources(result.files);
        showOutput('Recursos do repositório atual atualizados.');
    } else {
        showOutput('Erro ao atualizar recursos do repositório: ' + (result.error || 'Falha desconhecida.'));
    }
};

const renderRepositoryResources = (resources) => {
    repoResourcesDiv.innerHTML = '';
    if (!resources || resources.length === 0) {
        repoResourcesDiv.textContent = 'Nenhum recurso encontrado no repositório.';
        return;
    }
    resources.forEach((path) => {
        const item = document.createElement('div');
        item.className = 'repo-resource-item';
        item.textContent = path;
        item.addEventListener('click', () => openFile(path));
        repoResourcesDiv.appendChild(item);
    });
};

const updateRepoMeta = () => {
    repoProjectName.textContent = currentProjectId || 'nenhum';
    repoProjectVisibility.textContent = currentProjectVisibility;
};

const openRepoProject = async () => {
    if (!currentProjectId) {
        showOutput('Nenhum projeto de repositório aberto atualmente.');
        return;
    }
    openProject(currentProjectId);
};

const setSettingsTab = (tabId) => {
    activeSettingsTab = tabId;
    Object.keys(settingsTabSections).forEach((key) => {
        const section = settingsTabSections[key];
        if (!section) return;
        section.classList.toggle('active', key === tabId);
    });
    document.querySelectorAll('.panel-tab').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === tabId);
    });
};

const switchSettingsTab = (event) => {
    const tabId = event.currentTarget.dataset.tab;
    if (tabId) {
        setSettingsTab(tabId);
    }
};

const determineLanguageFromPath = (path) => {
    const ext = path.split('.').pop().toLowerCase();
    if (ext === 'py') return 'python';
    if (ext === 'js') return 'javascript';
    return 'cookiescript';
};

const ensureTabOpen = () => {
    if (activeTabIndex < 0) newTab();
};


const openFile = async (pathOverride) => {
    const path = pathOverride || filePathInput.value.trim();
    if (!path) {
        showOutput('Informe o caminho do arquivo para abrir.');
        return;
    }
    const result = await api('/api/open', { path });
    if (result.success) {
        const language = determineLanguageFromPath(path);
        const existingIndex = tabs.findIndex((tab) => tab.path === path);
        if (existingIndex >= 0) {
            tabs[existingIndex].content = result.content;
            tabs[existingIndex].dirty = false;
            setActiveTab(existingIndex);
        } else {
            createTab({ path, language, content: result.content, title: path.split('/').pop() });
        }
        showOutput('Arquivo carregado com sucesso.');
    } else {
        showOutput('Erro: ' + (result.error || 'Falha ao carregar arquivo.'));
    }
};

const saveFile = async () => {
    ensureTabOpen();
    const tab = getCurrentTab();
    const language = languageSelect.value;
    const extension = language === 'python' ? 'py' : language === 'javascript' ? 'js' : 'cookiescript';
    const path = (tab?.path && tab.path.trim()) || filePathInput.value.trim() || `novo_script.${extension}`;
    const content = codeArea.value;
    const result = await api('/api/save', { path, content });
    if (result.success) {
        showOutput('Arquivo salvo em: ' + result.path);
        if (tab) {
            tab.path = path;
            tab.title = path.split('/').pop();
            tab.language = language;
            tab.content = content;
            tab.dirty = false;
        } else {
            createTab({ path, language, content, title: path.split('/').pop() });
        }
        filePathInput.value = path;
        renderTabs();
        refreshFileList();
    } else {
        showOutput('Erro: ' + (result.error || 'Falha ao salvar arquivo.'));
    }
};

const executeCode = async () => {
    const content = codeArea.value;
    const language = languageSelect.value;
    const result = await api('/api/execute', { content, language });
    if (result.success) {
        showOutput('Execução concluída. Resultado: ' + JSON.stringify(result.result, null, 2));
    } else {
        showOutput('Erro de execução: ' + (result.error || 'Falha desconhecida.'));
    }
};

const generateCode = async () => {
    const prompt = promptArea.value.trim();
    const language = languageSelect.value;
    const result = await api('/api/generate', { prompt, language });
    if (result.success) {
        codeArea.value = result.code;
        showOutput('Código gerado com sucesso.');
        drawCanvas();
    } else {
        showOutput('Erro: ' + (result.error || 'Falha ao gerar código.'));
    }
};

const searchCode = async () => {
    const query = document.getElementById('searchInput').value.trim();
    const language = languageSelect.value;
    if (!query) {
        showOutput('Digite uma consulta de pesquisa.');
        return;
    }
    showOutput('Pesquisando códigos e módulos...');
    const result = await api('/api/search', { query, language });
    if (result.success) {
        codeArea.value = result.code;
        showOutput('Código encontrado para: ' + result.query);
        drawCanvas();
    } else {
        showOutput('Erro: ' + (result.error || 'Falha na pesquisa.'));
    }
};

const installLanguages = async () => {
    const mode = installMode.value;
    showOutput('Instalando ' + mode + '... aguarde.');
    const result = await api('/api/install', { mode });
    if (result.success) {
        showOutput('Instalação concluída. Veja os resultados no console.');
        console.log(result.results);
    } else {
        showOutput('Erro: ' + (result.error || 'Falha na instalação.'));
    }
};

const refreshFileList = async () => {
    const result = await api('/api/files', {});
    if (result.success) {
        populateFileList(result.files);
    } else {
        showOutput('Erro ao carregar lista de arquivos: ' + (result.error || 'Falha desconhecida.'));
    }
};

const populateFileList = (files) => {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    if (!files || files.length === 0) {
        fileList.textContent = 'Nenhum arquivo encontrado.';
        return;
    }
    files.forEach(path => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.textContent = path;
        item.addEventListener('click', () => openFile(path));
        fileList.appendChild(item);
    });
};

const gitStatus = async () => {
    const result = await api('/api/cokie/status', {});
    if (result.success) {
        showGitOutput(result.status.output || 'Repositório Cokie vazio.');
    } else {
        showGitOutput('Erro Cokie: ' + (result.error || 'Não foi possível obter status.'));
    }
};

const gitLog = async () => {
    const result = await api('/api/cokie/log', {});
    if (result.success) {
        showGitOutput(result.log.output || 'Nenhum comint encontrado.');
    } else {
        showGitOutput('Erro Cokie: ' + (result.error || 'Não foi possível obter log.'));
    }
};

const gitCommit = async () => {
    const message = document.getElementById('gitMessage').value.trim();
    if (!message) {
        showGitOutput('Informe uma mensagem de comint.');
        return;
    }
    const result = await api('/api/cokie/comint', { message });
    if (result.success) {
        showGitOutput('Comint realizado.\n' + (result.cominted.output || result.cominted));
        gitStatus();
    } else {
        showGitOutput('Erro Cokie: ' + (result.error || 'Falha no comint.'));
    }
};

const getUserName = () => {
    const name = userNameInput.value.trim();
    return name || 'anônimo';
};

const setCurrentProject = (projectId, visibility) => {
    currentProjectId = projectId;
    currentProjectVisibility = visibility || 'privado';
    currentProjectIdText.textContent = `Projeto: ${projectId || 'nenhum'}`;
    currentProjectVisibilityText.textContent = `Visibilidade: ${currentProjectVisibility}`;
    updateRepoMeta();
};

const createProject = async () => {
    if (!window.firebaseDB) {
        showOutput('Firebase não inicializado.');
        return;
    }
    const user = getUserName();
    const name = projectNameInput.value.trim();
    const description = projectDescription.value.trim();
    if (!name) {
        showOutput('Informe um nome para o projeto.');
        return;
    }

    const projectId = `proj_${Date.now()}`;
    const projectRef = window.firebaseRef(window.firebaseDB, `projects/${projectId}`);
    const code = codeArea.value;
    const language = languageSelect.value;
    const payload = {
        id: projectId,
        name,
        description,
        owner: user,
        visibility: 'privado',
        language,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        files: {
            [filePathInput.value.trim() || `main.${language === 'python' ? 'py' : language === 'javascript' ? 'js' : 'cookiescript'}`]: code
        },
        versions: {
            [`v_${Date.now()}`]: {
                message: 'Versão inicial',
                code,
                language,
                author: user,
                timestamp: Date.now()
            }
        }
    };

    try {
        await window.firebaseSet(projectRef, payload);
        setCurrentProject(projectId, 'privado');
        showOutput(`Projeto criado: ${name}`);
        loadProjects();
    } catch (error) {
        showOutput('Erro ao criar projeto: ' + error.message);
    }
};

const publishProject = async () => {
    if (!window.firebaseDB) {
        showOutput('Firebase não inicializado.');
        return;
    }
    if (!currentProjectId) {
        showOutput('Abra ou crie um projeto antes de publicar.');
        return;
    }
    try {
        const projectRef = window.firebaseRef(window.firebaseDB, `projects/${currentProjectId}/visibility`);
        await window.firebaseSet(projectRef, 'public');
        setCurrentProject(currentProjectId, 'public');
        showOutput('Projeto publicado na rede!');
    } catch (error) {
        showOutput('Erro ao publicar projeto: ' + error.message);
    }
};

const saveProjectVersion = async () => {
    if (!window.firebaseDB) {
        showOutput('Firebase não inicializado.');
        return;
    }
    if (!currentProjectId) {
        showOutput('Abra ou crie um projeto antes de salvar uma versão.');
        return;
    }
    const user = getUserName();
    const message = document.getElementById('gitMessage').value.trim() || 'Atualização rápida';
    const versionId = `v_${Date.now()}`;
    const code = codeArea.value;
    const language = languageSelect.value;

    try {
        const versionRef = window.firebaseRef(window.firebaseDB, `projects/${currentProjectId}/versions/${versionId}`);
        await window.firebaseSet(versionRef, {
            message,
            code,
            language,
            author: user,
            timestamp: Date.now()
        });
        const metaRef = window.firebaseRef(window.firebaseDB, `projects/${currentProjectId}/updatedAt`);
        await window.firebaseSet(metaRef, Date.now());
        showOutput('Versão salva no projeto.');
    } catch (error) {
        showOutput('Erro ao salvar versão: ' + error.message);
    }
};

const loadProjects = async () => {
    if (!window.firebaseDB) {
        showOutput('Firebase não inicializado.');
        return;
    }
    try {
        const projectsRef = window.firebaseRef(window.firebaseDB, 'projects');
        const snapshot = await window.firebaseGet(projectsRef);
        if (!snapshot.exists()) {
            projectListDiv.textContent = 'Nenhum projeto disponível.';
            return;
        }
        const projects = snapshot.val();
        const projectArray = Object.values(projects).sort((a, b) => b.updatedAt - a.updatedAt);
        renderProjectList(projectArray);
        showOutput('Lista de projetos carregada.');
    } catch (error) {
        showOutput('Erro ao carregar projetos: ' + error.message);
    }
};

const renderProjectList = (projects) => {
    projectListDiv.innerHTML = '';
    if (!projects.length) {
        projectListDiv.textContent = 'Nenhum projeto disponível.';
        return;
    }
    projects.forEach(project => {
        const item = document.createElement('div');
        item.className = 'project-item';
        item.innerHTML = `
            <strong>${project.name}</strong> <em>(${project.visibility})</em><br />
            ${project.description || 'Sem descrição'}<br />
            <small>Autor: ${project.owner || 'anônimo'}</small>
        `;
        item.addEventListener('click', () => openProject(project.id));
        projectListDiv.appendChild(item);
    });
};

const openProject = async (projectId) => {
    if (!window.firebaseDB) {
        showOutput('Firebase não inicializado.');
        return;
    }
    try {
        const projectRef = window.firebaseRef(window.firebaseDB, `projects/${projectId}`);
        const snapshot = await window.firebaseGet(projectRef);
        if (!snapshot.exists()) {
            showOutput('Projeto não encontrado.');
            return;
        }
        const project = snapshot.val();
        projectNameInput.value = project.name || '';
        projectDescription.value = project.description || '';
        tabs = [];
        const files = project.files || {};
        const fileNames = Object.keys(files);
        if (!fileNames.length) {
            createTab({ path: `main.${languageExtension(project.language || 'cookiescript')}`, language: project.language || 'cookiescript', content: '', title: `main.${languageExtension(project.language || 'cookiescript')}` });
        } else {
            fileNames.forEach((fileName, index) => {
                createTab({
                    path: fileName,
                    language: determineLanguageFromPath(fileName),
                    content: files[fileName],
                    title: fileName,
                    activate: false
                });
            });
            setActiveTab(0);
        }
        setCurrentProject(projectId, project.visibility || 'privado');
        showOutput(`Projeto carregado: ${project.name}`);
        drawCanvas();
    } catch (error) {
        showOutput('Erro ao abrir projeto: ' + error.message);
    }
};

window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btnOpen').addEventListener('click', () => openFile());
    document.getElementById('btnSave').addEventListener('click', saveFile);
    document.getElementById('btnNewTab').addEventListener('click', newTab);
    document.getElementById('btnRun').addEventListener('click', executeCode);
    document.getElementById('btnGenerate').addEventListener('click', generateCode);
    document.getElementById('btnSearch').addEventListener('click', searchCode);
    document.getElementById('btnInstall').addEventListener('click', installLanguages);
    document.getElementById('btnCreateProject').addEventListener('click', createProject);
    document.getElementById('btnLoadProjects').addEventListener('click', loadProjects);
    document.getElementById('btnPublishProject').addEventListener('click', publishProject);
    document.getElementById('btnSaveProjectVersion').addEventListener('click', saveProjectVersion);
    document.getElementById('btnRefreshFiles').addEventListener('click', refreshFileList);
    document.getElementById('btnRefreshRepo').addEventListener('click', refreshRepositoryResources);
    document.getElementById('btnOpenRepoProject').addEventListener('click', openRepoProject);
    document.getElementById('btnGitStatus').addEventListener('click', gitStatus);
    document.getElementById('btnGitLog').addEventListener('click', gitLog);
    document.getElementById('btnGitCommit').addEventListener('click', gitCommit);
    document.querySelectorAll('.panel-tab').forEach((button) => button.addEventListener('click', switchSettingsTab));
    codeArea.addEventListener('input', updateCurrentTab);
    languageSelect.addEventListener('change', () => {
        const tab = getCurrentTab();
        if (tab) {
            tab.language = languageSelect.value;
            tab.dirty = true;
            renderTabs();
        }
    });
    refreshFileList();
    gitStatus();
    loadProjects();
    newTab();
    setSettingsTab('generate');
    drawCanvas();
    setInterval(drawCanvas, 2500);
});
