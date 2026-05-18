// Import Firebase
import { 
    auth, database, 
    ref, set, get, update, remove,
    signInWithEmailAndPassword, 
    createUserWithEmailAndPassword,
    updateProfile,
    signOut,
    onAuthStateChanged
} from './firebase-config.js';

// ==================== ESTADO GLOBAL ====================
let currentUser = null;
let currentRepoId = null;
let monacoEditor = null;

// ==================== FUNÇÕES AUXILIARES ====================
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = isError ? 'toast error' : 'toast';
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

function getLanguageColor(language) {
    const colors = {
        'JavaScript': '#f1e05a',
        'Python': '#3572A5',
        'TypeScript': '#3178c6',
        'Java': '#b07219',
        'Go': '#00ADD8',
        'Rust': '#dea584',
        'HTML': '#e34c26',
        'CSS': '#563d7c',
        'CookieScript': '#f78166'
    };
    return colors[language] || '#8b949e';
}

// ==================== AUTENTICAÇÃO ====================
async function login(email, password) {
    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        currentUser = userCredential.user;
        showToast(`✅ Bem-vindo, ${currentUser.displayName || currentUser.email}!`);
        return true;
    } catch (error) {
        let message = 'Erro ao fazer login';
        if (error.code === 'auth/invalid-credential') message = 'Email ou senha inválidos';
        if (error.code === 'auth/user-not-found') message = 'Usuário não encontrado';
        if (error.code === 'auth/wrong-password') message = 'Senha incorreta';
        showToast(`❌ ${message}`, true);
        return false;
    }
}

async function register(name, email, password) {
    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        currentUser = userCredential.user;
        await updateProfile(currentUser, { displayName: name });
        
        // Criar perfil no Realtime Database
        await set(ref(database, `users/${currentUser.uid}`), {
            name: name,
            email: email,
            bio: 'Desenvolvedor full-stack apaixonado por código',
            createdAt: Date.now(),
            repos: 0,
            stars: 0,
            forks: 0
        });
        
        showToast(`✅ Conta criada com sucesso! Bem-vindo, ${name}!`);
        return true;
    } catch (error) {
        let message = 'Erro ao criar conta';
        if (error.code === 'auth/email-already-in-use') message = 'Email já está em uso';
        if (error.code === 'auth/weak-password') message = 'Senha muito fraca (mínimo 6 caracteres)';
        if (error.code === 'auth/invalid-email') message = 'Email inválido';
        showToast(`❌ ${message}`, true);
        return false;
    }
}

async function logout() {
    try {
        await signOut(auth);
        showToast('👋 Até logo!');
        return true;
    } catch (error) {
        showToast(`❌ Erro ao sair: ${error.message}`, true);
        return false;
    }
}

// ==================== REPOSITÓRIOS ====================
async function loadUserRepos() {
    if (!currentUser) return [];
    
    const reposRef = ref(database, 'repositories');
    const snapshot = await get(reposRef);
    const repos = [];
    
    if (snapshot.exists()) {
        const data = snapshot.val();
        for (let id in data) {
            if (data[id].ownerId === currentUser.uid) {
                repos.push({ id, ...data[id] });
            }
        }
    }
    
    repos.sort((a, b) => b.updatedAt - a.updatedAt);
    renderUserRepos(repos);
    
    // Atualizar estatísticas
    document.getElementById('statRepos').textContent = repos.length;
    let totalStars = 0, totalForks = 0;
    repos.forEach(repo => {
        totalStars += repo.stars || 0;
        totalForks += repo.forks || 0;
    });
    document.getElementById('statStars').textContent = totalStars;
    document.getElementById('statForks').textContent = totalForks;
    
    // Atualizar contagem no perfil do usuário
    if (currentUser) {
        await update(ref(database, `users/${currentUser.uid}`), {
            repos: repos.length,
            stars: totalStars,
            forks: totalForks
        });
    }
    
    return repos;
}

function renderUserRepos(repos) {
    const container = document.getElementById('userRepos');
    
    if (repos.length === 0) {
        container.innerHTML = `
            <div class="loading">
                ✨ Nenhum repositório ainda.<br>
                Clique em "Novo Repositório" para começar!
            </div>
        `;
        return;
    }
    
    container.innerHTML = repos.map(repo => `
        <div class="repo-card" data-id="${repo.id}">
            <div class="repo-name">
                📁 ${repo.name}
            </div>
            <div class="repo-desc">${repo.description || 'Sem descrição'}</div>
            <div class="repo-stats">
                <span class="repo-language">
                    <span class="language-dot" style="background: ${getLanguageColor(repo.language)}"></span>
                    ${repo.language || 'CookieScript'}
                </span>
                <span>⭐ ${repo.stars || 0}</span>
                <span>🔀 ${repo.forks || 0}</span>
                <span>${repo.visibility === 'private' ? '🔒 Privado' : '🌍 Público'}</span>
            </div>
            <div class="repo-actions">
                <button class="edit-repo" data-id="${repo.id}">✏️ Editar</button>
                <button class="delete-repo" data-id="${repo.id}">🗑️ Deletar</button>
                <button class="fork-repo" data-id="${repo.id}">🍴 Fork</button>
            </div>
        </div>
    `).join('');
    
    document.querySelectorAll('.repo-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.classList.contains('edit-repo') && 
                !e.target.classList.contains('delete-repo') &&
                !e.target.classList.contains('fork-repo')) {
                openRepository(card.dataset.id);
            }
        });
    });
    
    document.querySelectorAll('.edit-repo').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openRepository(btn.dataset.id);
        });
    });
    
    document.querySelectorAll('.delete-repo').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteRepository(btn.dataset.id);
        });
    });
    
    document.querySelectorAll('.fork-repo').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            forkRepository(btn.dataset.id);
        });
    });
}

async function loadPublicRepos() {
    const reposRef = ref(database, 'repositories');
    const snapshot = await get(reposRef);
    const repos = [];
    
    if (snapshot.exists()) {
        const data = snapshot.val();
        for (let id in data) {
            if (data[id].visibility === 'public') {
                repos.push({ id, ...data[id] });
            }
        }
    }
    
    repos.sort((a, b) => (b.stars || 0) - (a.stars || 0));
    renderPublicRepos(repos);
}

function renderPublicRepos(repos) {
    const container = document.getElementById('exploreRepos');
    
    if (repos.length === 0) {
        container.innerHTML = '<div class="loading">🌟 Nenhum repositório público encontrado</div>';
        return;
    }
    
    container.innerHTML = repos.map(repo => `
        <div class="repo-card" data-id="${repo.id}">
            <div class="repo-name">
                👤 ${repo.ownerName || 'Usuário'} / ${repo.name}
            </div>
            <div class="repo-desc">${repo.description || 'Sem descrição'}</div>
            <div class="repo-stats">
                <span class="repo-language">
                    <span class="language-dot" style="background: ${getLanguageColor(repo.language)}"></span>
                    ${repo.language || 'CookieScript'}
                </span>
                <span>⭐ ${repo.stars || 0}</span>
                <span>🔀 ${repo.forks || 0}</span>
            </div>
            <div class="repo-actions">
                <button class="star-repo" data-id="${repo.id}">⭐ Star</button>
                <button class="view-repo" data-id="${repo.id}">👁️ Ver</button>
            </div>
        </div>
    `).join('');
    
    document.querySelectorAll('#exploreRepos .repo-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.classList.contains('star-repo') && 
                !e.target.classList.contains('view-repo')) {
                viewPublicRepo(card.dataset.id);
            }
        });
    });
    
    document.querySelectorAll('.star-repo').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            await starRepository(btn.dataset.id);
        });
    });
    
    document.querySelectorAll('.view-repo').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            viewPublicRepo(btn.dataset.id);
        });
    });
}

async function createRepository(name, description, visibility) {
    if (!name) {
        showToast('Nome do repositório é obrigatório', true);
        return false;
    }
    
    const repoId = `repo_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
    const repoData = {
        name: name,
        description: description || '',
        visibility: visibility,
        language: 'CookieScript',
        ownerId: currentUser.uid,
        ownerName: currentUser.displayName || currentUser.email,
        stars: 0,
        forks: 0,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        files: {
            'README.md': `# ${name}\n\n${description || 'Um projeto incrível!'}\n\n## Como usar\n\n1. Clone o repositório\n2. Instale as dependências\n3. Execute o projeto\n\n## Tecnologias\n- CookieScript`
        }
    };
    
    try {
        await set(ref(database, `repositories/${repoId}`), repoData);
        showToast(`✅ Repositório "${name}" criado com sucesso!`);
        await loadUserRepos();
        await loadPublicRepos();
        return true;
    } catch (error) {
        showToast(`❌ Erro: ${error.message}`, true);
        return false;
    }
}

async function deleteRepository(repoId) {
    if (!confirm('Tem certeza que deseja deletar este repositório? Esta ação não pode ser desfeita.')) {
        return;
    }
    
    try {
        await remove(ref(database, `repositories/${repoId}`));
        showToast('🗑️ Repositório deletado com sucesso!');
        await loadUserRepos();
        await loadPublicRepos();
    } catch (error) {
        showToast(`❌ Erro: ${error.message}`, true);
    }
}

async function openRepository(repoId) {
    currentRepoId = repoId;
    const snapshot = await get(ref(database, `repositories/${repoId}`));
    
    if (snapshot.exists()) {
        const repo = snapshot.val();
        document.getElementById('editorTitle').textContent = `${repo.name} - Editor`;
        
        const files = repo.files || {};
        const fileNames = Object.keys(files);
        const firstFile = fileNames[0] || 'README.md';
        const content = files[firstFile] || '';
        
        document.getElementById('fileName').value = firstFile;
        
        const modal = document.getElementById('editorModal');
        modal.classList.add('active');
        
        if (!monacoEditor) {
            require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
            require(['vs/editor/editor.main'], function() {
                monacoEditor = monaco.editor.create(document.getElementById('monacoEditor'), {
                    value: content,
                    language: 'javascript',
                    theme: 'vs-dark',
                    automaticLayout: true,
                    fontSize: 14,
                    minimap: { enabled: false }
                });
            });
        } else {
            monacoEditor.setValue(content);
            monacoEditor.updateOptions({ readOnly: false });
        }
    }
}

async function saveRepositoryFile() {
    if (!currentRepoId) return;
    
    const fileName = document.getElementById('fileName').value;
    const content = monacoEditor ? monacoEditor.getValue() : '';
    
    try {
        await update(ref(database, `repositories/${currentRepoId}/files/${fileName}`), content);
        await update(ref(database, `repositories/${currentRepoId}`), { updatedAt: Date.now() });
        showToast(`💾 Arquivo "${fileName}" salvo com sucesso!`);
        document.getElementById('editorModal').classList.remove('active');
    } catch (error) {
        showToast(`❌ Erro: ${error.message}`, true);
    }
}

async function starRepository(repoId) {
    if (!currentUser) {
        showToast('Faça login para dar estrelas!', true);
        return;
    }
    
    const snapshot = await get(ref(database, `repositories/${repoId}`));
    if (snapshot.exists()) {
        const repo = snapshot.val();
        const newStars = (repo.stars || 0) + 1;
        await update(ref(database, `repositories/${repoId}`), { stars: newStars });
        showToast(`⭐ Você deu uma estrela em ${repo.name}!`);
        await loadPublicRepos();
        await loadUserRepos();
    }
}

async function forkRepository(repoId) {
    if (!currentUser) {
        showToast('Faça login para fazer fork!', true);
        return;
    }
    
    const snapshot = await get(ref(database, `repositories/${repoId}`));
    if (snapshot.exists()) {
        const originalRepo = snapshot.val();
        const forkedId = `repo_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
        const forkedRepo = {
            ...originalRepo,
            id: forkedId,
            name: `${originalRepo.name}-fork`,
            ownerId: currentUser.uid,
            ownerName: currentUser.displayName || currentUser.email,
            stars: 0,
            forks: 0,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            forkedFrom: repoId
        };
        delete forkedRepo.id;
        
        await set(ref(database, `repositories/${forkedId}`), forkedRepo);
        
        const newForks = (originalRepo.forks || 0) + 1;
        await update(ref(database, `repositories/${repoId}`), { forks: newForks });
        
        showToast(`🍴 Fork criado: ${forkedRepo.name}`);
        await loadUserRepos();
        await loadPublicRepos();
    }
}

async function viewPublicRepo(repoId) {
    const snapshot = await get(ref(database, `repositories/${repoId}`));
    if (snapshot.exists()) {
        const repo = snapshot.val();
        showToast(`👁️ Visualizando: ${repo.name}`);
        
        const files = repo.files || {};
        const firstFile = Object.keys(files)[0];
        if (firstFile) {
            document.getElementById('editorTitle').textContent = `${repo.name} - Visualização`;
            document.getElementById('fileName').value = firstFile;
            
            const modal = document.getElementById('editorModal');
            modal.classList.add('active');
            
            if (!monacoEditor) {
                require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } });
                require(['vs/editor/editor.main'], function() {
                    monacoEditor = monaco.editor.create(document.getElementById('monacoEditor'), {
                        value: files[firstFile],
                        language: 'javascript',
                        theme: 'vs-dark',
                        automaticLayout: true,
                        readOnly: true,
                        fontSize: 14
                    });
                });
            } else {
                monacoEditor.setValue(files[firstFile]);
                monacoEditor.updateOptions({ readOnly: true });
            }
        }
    }
}

// ==================== PERFIL ====================
async function updateUserProfile(name, bio) {
    if (!currentUser) return;
    
    try {
        await updateProfile(currentUser, { displayName: name });
        await update(ref(database, `users/${currentUser.uid}`), {
            name: name,
            bio: bio
        });
        
        document.getElementById('profileName').textContent = name;
        document.getElementById('profileBio').textContent = bio;
        document.getElementById('profileAvatar').textContent = name.charAt(0).toUpperCase();
        document.querySelector('.avatar').textContent = name.charAt(0).toUpperCase();
        
        showToast('✅ Perfil atualizado com sucesso!');
    } catch (error) {
        showToast(`❌ Erro: ${error.message}`, true);
    }
}

async function loadUserProfile() {
    if (!currentUser) return;
    
    const snapshot = await get(ref(database, `users/${currentUser.uid}`));
    const userData = snapshot.exists() ? snapshot.val() : {};
    const name = currentUser.displayName || userData.name || currentUser.email.split('@')[0];
    const bio = userData.bio || 'Desenvolvedor full-stack apaixonado por código';
    
    document.getElementById('profileName').textContent = name;
    document.getElementById('profileEmail').textContent = currentUser.email;
    document.getElementById('profileBio').textContent = bio;
    document.getElementById('profileAvatar').textContent = name.charAt(0).toUpperCase();
    document.querySelector('.avatar').textContent = name.charAt(0).toUpperCase();
}

// ==================== PESQUISA ====================
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', async (e) => {
        const term = e.target.value.toLowerCase();
        
        if (term.length < 2) {
            await loadUserRepos();
            return;
        }
        
        const reposRef = ref(database, 'repositories');
        const snapshot = await get(reposRef);
        const filtered = [];
        
        if (snapshot.exists()) {
            const data = snapshot.val();
            for (let id in data) {
                if (data[id].ownerId === currentUser?.uid && 
                    (data[id].name.toLowerCase().includes(term) || 
                     (data[id].description || '').toLowerCase().includes(term))) {
                    filtered.push({ id, ...data[id] });
                }
            }
        }
        
        renderUserRepos(filtered);
    });
}

// ==================== NAVEGAÇÃO ====================
function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
    
    document.getElementById(`${page}Page`).classList.add('active');
    document.querySelector(`[data-page="${page}"]`).classList.add('active');
}

// ==================== GESTÃO DE TELAS ====================
function showAuthPage() {
    document.getElementById('authPage').classList.add('active');
    document.getElementById('appPage').classList.remove('active');
}

function showAppPage() {
    document.getElementById('authPage').classList.remove('active');
    document.getElementById('appPage').classList.add('active');
}

// ==================== LISTENERS DE AUTENTICAÇÃO ====================
function setupAuthListeners() {
    // Switch entre login e registro
    document.getElementById('showRegister').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('loginForm').classList.remove('active');
        document.getElementById('registerForm').classList.add('active');
    });
    
    document.getElementById('showLogin').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('registerForm').classList.remove('active');
        document.getElementById('loginForm').classList.add('active');
    });
    
    // Login
    document.getElementById('loginBtn').addEventListener('click', async () => {
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        
        if (!email || !password) {
            showToast('Preencha todos os campos', true);
            return;
        }
        
        const success = await login(email, password);
        if (success) {
            showAppPage();
            await loadUserProfile();
            await loadUserRepos();
            await loadPublicRepos();
            setupSearch();
        }
    });
    
    // Register
    document.getElementById('registerBtn').addEventListener('click', async () => {
        const name = document.getElementById('registerName').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        
        if (!name || !email || !password) {
            showToast('Preencha todos os campos', true);
            return;
        }
        
        if (password.length < 6) {
            showToast('Senha deve ter pelo menos 6 caracteres', true);
            return;
        }
        
        const success = await register(name, email, password);
        if (success) {
            showAppPage();
            await loadUserProfile();
            await loadUserRepos();
            await loadPublicRepos();
            setupSearch();
        }
    });
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', async () => {
        await logout();
        showAuthPage();
    });
    
    // Monitorar estado de autenticação
    onAuthStateChanged(auth, (user) => {
        currentUser = user;
        if (user) {
            showAppPage();
            loadUserProfile();
            loadUserRepos();
            loadPublicRepos();
            setupSearch();
        } else {
            showAuthPage();
        }
    });
}

// ==================== EVENT LISTENERS ====================
document.addEventListener('DOMContentLoaded', () => {
    // Navegação
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navigateTo(link.dataset.page);
        });
    });
    
    // Avatar dropdown
    const avatarBtn = document.getElementById('avatarBtn');
    const dropdown = document.getElementById('dropdownMenu');
    avatarBtn.addEventListener('click', () => {
        dropdown.classList.toggle('show');
    });
    
    document.addEventListener('click', (e) => {
        if (!avatarBtn.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
    
    // Criar repositório
    document.getElementById('createRepoBtn').addEventListener('click', () => {
        document.getElementById('repoModal').classList.add('active');
    });
    
    document.getElementById('refreshReposBtn').addEventListener('click', async () => {
        await loadUserRepos();
        showToast('Repositórios atualizados!');
    });
    
    // Fechar modais
    document.querySelectorAll('.close-modal, .close-editor, .close-profile, #cancelRepoBtn, #cancelEditorBtn, #cancelProfileBtn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('repoModal').classList.remove('active');
            document.getElementById('editorModal').classList.remove('active');
            document.getElementById('profileModal').classList.remove('active');
        });
    });
    
    // Confirmar criação
    document.getElementById('confirmRepoBtn').addEventListener('click', async () => {
        const name = document.getElementById('repoName').value;
        const desc = document.getElementById('repoDesc').value;
        const visibility = document.getElementById('repoVisibility').value;
        
        await createRepository(name, desc, visibility);
        
        document.getElementById('repoModal').classList.remove('active');
        document.getElementById('repoName').value = '';
        document.getElementById('repoDesc').value = '';
    });
    
    // Salvar arquivo
    document.getElementById('saveFileBtn').addEventListener('click', saveRepositoryFile);
    
    // Editar perfil
    document.getElementById('editProfileBtn').addEventListener('click', async () => {
        const snapshot = await get(ref(database, `users/${currentUser?.uid}`));
        const userData = snapshot.exists() ? snapshot.val() : {};
        
        document.getElementById('editName').value = currentUser?.displayName || userData.name || '';
        document.getElementById('editBio').value = userData.bio || '';
        document.getElementById('profileModal').classList.add('active');
    });
    
    document.getElementById('saveProfileBtn').addEventListener('click', async () => {
        const name = document.getElementById('editName').value;
        const bio = document.getElementById('editBio').value;
        await updateUserProfile(name, bio);
        document.getElementById('profileModal').classList.remove('active');
    });
    
    // Configurar listeners de autenticação
    setupAuthListeners();
});