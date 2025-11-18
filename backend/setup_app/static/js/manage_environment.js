/**
 * System Configuration Page - Enhanced Features
 * Handles dark mode, testing, import/export, and audit history
 */

// ===== DARK MODE =====
const DarkMode = {
    init() {
        // Sincroniza com o tema do Vue (ui.theme no localStorage)
        const vueTheme = localStorage.getItem('ui.theme');
        const saved = vueTheme || localStorage.getItem('theme') || 'light';
        this.setTheme(saved);
        
        // Observa mudanças no tema do Vue
        window.addEventListener('storage', (e) => {
            if (e.key === 'ui.theme' && e.newValue) {
                this.setTheme(e.newValue);
            }
        });
    },
    
    setTheme(theme) {
        document.documentElement.classList.toggle('dark', theme === 'dark');
        // Salva em ambos os locais para compatibilidade
        localStorage.setItem('theme', theme);
        localStorage.setItem('ui.theme', theme);
    },
    
    toggle() {
        const isDark = document.documentElement.classList.contains('dark');
        this.setTheme(isDark ? 'light' : 'dark');
    },
    
    createToggle() {
        const container = document.querySelector('header .flex.items-center.space-x-2');
        if (!container) return;
        
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700';
        btn.title = 'Toggle dark mode';
        btn.innerHTML = `
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path class="sun-icon" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                <path class="moon-icon hidden" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
            </svg>
        `;
        
        const update = () => {
            const isDark = document.documentElement.classList.contains('dark');
            btn.querySelector('.sun-icon').classList.toggle('hidden', isDark);
            btn.querySelector('.moon-icon').classList.toggle('hidden', !isDark);
        };
        
        btn.onclick = () => { this.toggle(); update(); };
        update();
        container.appendChild(btn);
    }
};

// ===== UTILITIES =====
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    return parts.length === 2 ? parts.pop().split(';').shift() : null;
}

function notify(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500'
    };
    
    const div = document.createElement('div');
    div.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${colors[type]} text-white`;
    div.textContent = message;
    document.body.appendChild(div);
    
    setTimeout(() => {
        div.style.opacity = '0';
        div.style.transition = 'opacity 0.3s';
        setTimeout(() => div.remove(), 300);
    }, 3000);
}

// ===== CONNECTION TESTING =====
const ConnectionTester = {
    async testZabbix() {
        const btn = document.getElementById('test-zabbix-btn');
        const result = document.getElementById('zabbix-test-result');
        const formEl = document.querySelector('form');
        const data = new FormData(formEl);
        
        btn.disabled = true;
        btn.innerHTML = '<span class="animate-spin inline-block">⏳</span> Testing...';
        
        try {
            const resp = await fetch('/setup_app/api/test-zabbix/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    zabbix_api_url: data.get('zabbix_api_url'),
                    auth_type: document.querySelector('input[name="auth_method"]:checked')?.value || 'login',
                    zabbix_api_user: data.get('zabbix_api_user'),
                    zabbix_api_password: data.get('zabbix_api_password'),
                    zabbix_api_key: data.get('zabbix_api_key')
                })
            });
            
            const json = await resp.json();
            const cls = json.success ? 
                'bg-green-50 dark:bg-green-900 border-green-200 dark:border-green-700 text-green-800 dark:text-green-200' :
                'bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700 text-red-800 dark:text-red-200';
            
            result.innerHTML = `
                <div class="p-3 rounded-lg border ${cls} text-sm">
                    ${json.success ? '✓' : '✗'} ${json.message}
                </div>
            `;
        } catch (err) {
            result.innerHTML = `
                <div class="p-3 rounded-lg border bg-red-50 border-red-200 text-red-800 text-sm">
                    ✗ Network error: ${err.message}
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Test Connection';
        }
    },
    
    async testDatabase() {
        const btn = document.getElementById('test-database-btn');
        const result = document.getElementById('database-test-result');
        const formEl = document.querySelector('form');
        const data = new FormData(formEl);
        
        btn.disabled = true;
        btn.innerHTML = '<span class="animate-spin inline-block">⏳</span> Testing...';
        
        try {
            const resp = await fetch('/setup_app/api/test-database/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    db_host: data.get('db_host'),
                    db_port: data.get('db_port'),
                    db_name: data.get('db_name'),
                    db_user: data.get('db_user'),
                    db_password: data.get('db_password')
                })
            });
            
            const json = await resp.json();
            const cls = json.success ?
                'bg-green-50 dark:bg-green-900 border-green-200 dark:border-green-700 text-green-800 dark:text-green-200' :
                'bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700 text-red-800 dark:text-red-200';
            
            result.innerHTML = `
                <div class="p-3 rounded-lg border ${cls} text-sm">
                    ${json.success ? '✓' : '✗'} ${json.message}
                </div>
            `;
        } catch (err) {
            result.innerHTML = `
                <div class="p-3 rounded-lg border bg-red-50 border-red-200 text-red-800 text-sm">
                    ✗ Network error: ${err.message}
                </div>
            `;
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Test Connection';
        }
    }
};

// ===== IMPORT/EXPORT =====
const ConfigManager = {
    async exportConfig() {
        try {
            const resp = await fetch('/setup_app/api/export/');
            if (resp.ok) {
                const blob = await resp.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `mapsprove_config_${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
                notify('Configuration exported successfully!', 'success');
            } else {
                notify('Export failed', 'error');
            }
        } catch (err) {
            notify(`Export error: ${err.message}`, 'error');
        }
    },
    
    async importConfig(file) {
        const fd = new FormData();
        fd.append('config_file', file);
        
        try {
            const resp = await fetch('/setup_app/api/import/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: fd
            });
            
            const json = await resp.json();
            notify(json.message, json.success ? 'success' : 'error');
            
            if (json.success) {
                setTimeout(() => location.reload(), 2000);
            }
        } catch (err) {
            notify(`Import error: ${err.message}`, 'error');
        }
    },
    
    showImportDialog() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file && confirm(`Import from "${file.name}"? This will overwrite current settings (except passwords).`)) {
                this.importConfig(file);
            }
        };
        input.click();
    }
};

// ===== AUDIT HISTORY =====
const AuditViewer = {
    async load() {
        const modal = document.getElementById('audit-modal');
        const tbody = document.getElementById('audit-table-body');
        
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Loading...</td></tr>';
        modal.classList.remove('hidden');
        
        try {
            const resp = await fetch('/setup_app/api/audit-history/?limit=100');
            const json = await resp.json();
            
            if (json.success && json.audits.length > 0) {
                tbody.innerHTML = json.audits.map(a => `
                    <tr class="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td class="px-4 py-3 text-sm">${new Date(a.timestamp).toLocaleString()}</td>
                        <td class="px-4 py-3 text-sm">${a.user}</td>
                        <td class="px-4 py-3 text-sm">
                            <span class="px-2 py-1 rounded text-xs ${this.getBadgeClass(a.action)}">${a.action}</span>
                        </td>
                        <td class="px-4 py-3 text-sm">${a.section}</td>
                        <td class="px-4 py-3 text-sm font-mono text-xs">${a.field_name || '-'}</td>
                        <td class="px-4 py-3 text-sm">
                            ${a.success ? '✓' : `<span title="${a.error_message}">✗</span>`}
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">No records</td></tr>';
            }
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-red-600">Error: ${err.message}</td></tr>`;
        }
    },
    
    getBadgeClass(action) {
        const map = {
            'Created': 'bg-green-100 text-green-800',
            'Updated': 'bg-blue-100 text-blue-800',
            'Deleted': 'bg-red-100 text-red-800',
            'Exported': 'bg-purple-100 text-purple-800',
            'Imported': 'bg-indigo-100 text-indigo-800',
            'Connection Tested': 'bg-yellow-100 text-yellow-800'
        };
        return map[action] || 'bg-gray-100 text-gray-800';
    }
};

// ===== MAIN INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    DarkMode.init();
    
    // Password visibility toggle
    document.querySelectorAll('input[type="password"]').forEach(field => {
        const container = field.parentElement;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'absolute right-3 top-9 text-gray-400 hover:text-gray-600';
        btn.innerHTML = '👁️';
        container.style.position = 'relative';
        container.appendChild(btn);
        
        btn.onclick = () => {
            field.type = field.type === 'password' ? 'text' : 'password';
            btn.innerHTML = field.type === 'password' ? '👁️' : '🙈';
        };
    });
    
    // Zabbix auth method switcher
    const userField = document.getElementById('id_zabbix_api_user');
    const passField = document.getElementById('id_zabbix_api_password');
    const keyField = document.getElementById('id_zabbix_api_key');
    
    if (userField && keyField) {
        const section = keyField.closest('section');
        const switcher = document.createElement('div');
        switcher.className = 'px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700';
        switcher.innerHTML = `
            <div class="flex items-center space-x-4">
                <span class="text-sm font-medium">Auth Method:</span>
                <label class="inline-flex items-center">
                    <input type="radio" name="auth_method" value="login" class="form-radio" ${userField.value ? 'checked' : ''}>
                    <span class="ml-2 text-sm">User & Password</span>
                </label>
                <label class="inline-flex items-center">
                    <input type="radio" name="auth_method" value="token" class="form-radio" ${keyField.value ? 'checked' : ''}>
                    <span class="ml-2 text-sm">API Token</span>
                </label>
            </div>
        `;
        
        section.querySelector('.px-6.py-5').before(switcher);
        
        const update = () => {
            const method = switcher.querySelector('input:checked').value;
            const showLogin = method === 'login';
            userField.closest('.space-y-2').style.display = showLogin ? '' : 'none';
            passField.closest('.space-y-2').style.display = showLogin ? '' : 'none';
            keyField.closest('.space-y-2').style.display = showLogin ? 'none' : '';
            
            if (showLogin) {
                keyField.value = '';
                userField.required = true;
            } else {
                userField.value = '';
                passField.value = '';
                keyField.required = true;
            }
        };
        
        switcher.querySelectorAll('input').forEach(r => r.onchange = update);
        update();
    }
    
    // Bind global functions
    window.testZabbix = () => ConnectionTester.testZabbix();
    window.testDatabase = () => ConnectionTester.testDatabase();
    window.exportConfig = () => ConfigManager.exportConfig();
    window.importConfig = () => ConfigManager.showImportDialog();
    window.showAuditHistory = () => AuditViewer.load();
    window.closeAuditModal = () => document.getElementById('audit-modal').classList.add('hidden');
});
