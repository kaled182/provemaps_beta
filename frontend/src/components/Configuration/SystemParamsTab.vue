<template>
  <div class="space-y-0">

    <!-- Sub-tab navigation -->
    <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
      <nav class="-mb-px flex space-x-8">
        <button
          v-for="tab in subTabs"
          :key="tab.id"
          @click="activeSubTab = tab.id"
          class="whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors"
          :class="activeSubTab === tab.id
            ? 'border-primary-500 text-primary-600 dark:text-primary-400'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          {{ tab.label }}
        </button>
      </nav>
    </div>

    <!-- ═══════════════════════════════════════════════════
         INFRAESTRUTURA — DB + Redis
    ══════════════════════════════════════════════════════ -->
    <div v-if="activeSubTab === 'infra'" class="space-y-6 relative">
      <div v-if="loading" class="loading-overlay">
        <div class="loading-spinner"></div>
      </div>

      <!-- Redis -->
      <div class="card-section">
        <div class="flex items-center justify-between mb-4">
          <h3 class="section-title">Redis Cache</h3>
          <span v-if="config.REDIS_URL" class="badge-success">Configurado</span>
          <span v-else class="badge-gray">Não configurado</span>
        </div>
        <div class="space-y-4">
          <div>
            <label class="label-custom">Redis URL</label>
            <input v-model="config.REDIS_URL" type="text" class="input-custom"
              placeholder="redis://localhost:6379/1" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Senha do Redis</label>
            <input v-model="config.REDIS_PASSWORD" type="password" class="input-custom"
              placeholder="Deixe em branco se não houver senha" autocomplete="off" />
          </div>
          <div class="flex gap-2">
            <button @click="testRedis" :disabled="testingRedis" class="btn-secondary">
              <svg v-if="testingRedis" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Testar Conexão
            </button>
            <span v-if="testResults.redis" class="result-badge"
              :class="testResults.redis.success ? 'result-success' : 'result-error'">
              {{ testResults.redis.message }}
            </span>
          </div>
        </div>
      </div>

      <!-- Database -->
      <div class="card-section">
        <div class="flex items-center justify-between mb-4">
          <h3 class="section-title">Banco de Dados (PostGIS)</h3>
          <span v-if="config.DB_HOST && config.DB_NAME" class="badge-success">Configurado</span>
          <span v-else class="badge-gray">Não configurado</span>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Host</label>
            <input v-model="config.DB_HOST" type="text" class="input-custom"
              placeholder="localhost" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Porta</label>
            <input v-model="config.DB_PORT" type="text" class="input-custom"
              placeholder="5432" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Nome do Banco</label>
            <input v-model="config.DB_NAME" type="text" class="input-custom"
              placeholder="provemaps" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Usuário</label>
            <input v-model="config.DB_USER" type="text" class="input-custom"
              placeholder="postgres" autocomplete="off" />
          </div>
          <div class="col-span-2">
            <label class="label-custom">Senha</label>
            <input v-model="config.DB_PASSWORD" type="password" class="input-custom" autocomplete="off" />
          </div>
        </div>
        <div class="flex gap-2 mt-4">
          <button @click="testDatabase" :disabled="testingDatabase" class="btn-secondary">
            <svg v-if="testingDatabase" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
            </svg>
            Testar Conexão
          </button>
          <span v-if="testResults.database" class="result-badge"
            :class="testResults.database.success ? 'result-success' : 'result-error'">
            {{ testResults.database.message }}
          </span>
        </div>
      </div>

      <div class="flex justify-end gap-3">
        <button @click="handleReset" class="btn-secondary">Resetar</button>
        <button @click="handleSave" :disabled="saving || !isValid" class="btn-primary">
          <svg v-if="saving" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          Salvar Infraestrutura
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         SEGURANÇA
    ══════════════════════════════════════════════════════ -->
    <div v-else-if="activeSubTab === 'seguranca'" class="space-y-6">

      <!-- Chave Secreta -->
      <div class="card-section">
        <h3 class="section-title mb-4">Chave Secreta (SECRET_KEY)</h3>
        <div>
          <label class="label-custom">Valor atual</label>
          <div class="flex gap-2">
            <input
              v-model="config.SECRET_KEY"
              :type="showSecretKey ? 'text' : 'password'"
              class="input-custom font-mono text-xs"
              placeholder="Chave secreta do Django"
              autocomplete="off"
            />
            <button type="button" @click="showSecretKey = !showSecretKey"
              class="btn-secondary flex-none px-3" :title="showSecretKey ? 'Ocultar' : 'Revelar'">
              <svg v-if="showSecretKey" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 4.411m0 0L21 21"/>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
              </svg>
            </button>
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Alterar a chave invalida todas as sessões ativas e tokens CSRF.
          </p>
        </div>
      </div>

      <!-- Modo Debug & Hosts -->
      <div class="card-section space-y-4">
        <h3 class="section-title mb-2">Ambiente e Hosts</h3>

        <div class="flex items-center">
          <input v-model="config.DEBUG" type="checkbox" id="debug-mode"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
          <label for="debug-mode" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Modo Debug (verbose logging)
          </label>
        </div>

        <div class="flex items-center">
          <input v-model="config.ENABLE_DIAGNOSTIC_ENDPOINTS" type="checkbox" id="diag-endpoints"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
          <label for="diag-endpoints" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Habilitar endpoints de diagnóstico (<code class="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">/api/v1/diagnostics/</code>)
          </label>
        </div>

        <div>
          <label class="label-custom">Allowed Hosts</label>
          <input v-model="config.ALLOWED_HOSTS" type="text" class="input-custom"
            placeholder="localhost,127.0.0.1,app.example.com" autocomplete="off" />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Separados por vírgula.</p>
        </div>

        <div>
          <label class="label-custom">CSRF Trusted Origins</label>
          <input v-model="config.CSRF_TRUSTED_ORIGINS" type="text" class="input-custom"
            placeholder="https://app.example.com,https://api.example.com" autocomplete="off" />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            URLs completas com protocolo. Exigido para POST via domínio diferente do servidor.
          </p>
        </div>
      </div>

      <div class="flex justify-end gap-3">
        <button @click="handleReset" class="btn-secondary">Resetar</button>
        <button @click="handleSave" :disabled="saving" class="btn-primary">
          <svg v-if="saving" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          Salvar Segurança
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         EMPRESA
    ══════════════════════════════════════════════════════ -->
    <div v-else-if="activeSubTab === 'empresa'" class="space-y-6 relative">
      <div v-if="profileLoading" class="loading-overlay">
        <div class="loading-spinner"></div>
      </div>

      <!-- Logo -->
      <div class="card-section">
        <h3 class="section-title mb-4">Logotipo</h3>
        <div class="flex items-center gap-6">
          <div class="w-24 h-24 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600
                      flex items-center justify-center overflow-hidden bg-gray-50 dark:bg-gray-800 flex-none">
            <img v-if="logoPreview" :src="logoPreview" alt="Logo" class="w-full h-full object-contain" />
            <svg v-else class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="space-y-2">
            <label class="btn-secondary cursor-pointer text-sm">
              <input type="file" class="hidden" accept="image/*" @change="onLogoChange" />
              Selecionar imagem
            </label>
            <button v-if="logoPreview" @click="removeLogo" type="button"
              class="block text-xs text-red-500 hover:text-red-700 dark:text-red-400">
              Remover logo
            </button>
            <p class="text-xs text-gray-500 dark:text-gray-400">PNG, JPG ou SVG. Máx. 2 MB.</p>
          </div>
        </div>
      </div>

      <!-- Dados da Empresa -->
      <div class="card-section">
        <h3 class="section-title mb-4">Dados Cadastrais</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="label-custom">Razão Social</label>
            <input v-model="profile.company_legal_name" type="text" class="input-custom"
              placeholder="Empresa LTDA" autocomplete="off" />
          </div>
          <div class="col-span-2">
            <label class="label-custom">Nome Fantasia</label>
            <input v-model="profile.company_trade_name" type="text" class="input-custom"
              placeholder="Nome comercial" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">CNPJ</label>
            <input v-model="profile.company_doc" type="text" class="input-custom"
              placeholder="00.000.000/0001-00" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Data de Abertura</label>
            <input v-model="profile.company_created_date" type="text" class="input-custom"
              placeholder="01/01/2020" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Inscrição Estadual</label>
            <input v-model="profile.company_state_reg" type="text" class="input-custom"
              placeholder="Isento" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Inscrição Municipal</label>
            <input v-model="profile.company_city_reg" type="text" class="input-custom"
              placeholder="Isento" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Fistel (Anatel)</label>
            <input v-model="profile.company_fistel" type="text" class="input-custom"
              placeholder="50000000000" autocomplete="off" />
          </div>
        </div>

        <div class="flex items-center gap-6 mt-4">
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input v-model="profile.company_active" type="checkbox"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            Empresa ativa
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input v-model="profile.company_reports_active" type="checkbox"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded" />
            Emitir relatórios
          </label>
        </div>
      </div>

      <!-- Responsável -->
      <div class="card-section">
        <h3 class="section-title mb-4">Responsável Legal</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="label-custom">Nome completo</label>
            <input v-model="profile.company_owner_name" type="text" class="input-custom"
              placeholder="João da Silva" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">CPF</label>
            <input v-model="profile.company_owner_doc" type="text" class="input-custom"
              placeholder="000.000.000-00" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">Data de Nascimento</label>
            <input v-model="profile.company_owner_birth" type="text" class="input-custom"
              placeholder="01/01/1980" autocomplete="off" />
          </div>
        </div>
      </div>

      <!-- Certificado Digital -->
      <div class="card-section">
        <h3 class="section-title mb-4">Certificado Digital (A1)</h3>
        <div class="space-y-4">
          <div class="flex items-center gap-4">
            <label class="btn-secondary cursor-pointer text-sm flex-none">
              <input type="file" class="hidden" accept=".pfx,.p12,.pem,.cer,.crt" @change="onCertChange" />
              Selecionar certificado
            </label>
            <span v-if="certFile" class="text-sm text-gray-700 dark:text-gray-300 truncate max-w-xs">
              {{ certFile.name }}
            </span>
            <span v-else class="text-sm text-gray-400 dark:text-gray-500">Nenhum arquivo selecionado</span>
            <button v-if="certFile" @click="removeCert" type="button"
              class="text-xs text-red-500 hover:text-red-700 dark:text-red-400 flex-none">
              Remover
            </button>
          </div>
          <div>
            <label class="label-custom">Senha do Certificado</label>
            <input v-model="profile.assets_cert_password" type="password" class="input-custom"
              placeholder="Senha do arquivo .pfx / .p12" autocomplete="off" />
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            Usado para emissão de NF-e / NFS-e. Formatos aceitos: .pfx, .p12, .pem.
          </p>
        </div>
      </div>

      <!-- Endereço -->
      <div class="card-section">
        <h3 class="section-title mb-4">Endereço</h3>
        <div class="grid grid-cols-6 gap-4">
          <div class="col-span-2">
            <label class="label-custom">CEP</label>
            <input v-model="profile.address_zip" type="text" class="input-custom"
              placeholder="00000-000" autocomplete="off" />
          </div>
          <div class="col-span-4">
            <label class="label-custom">Logradouro</label>
            <input v-model="profile.address_street" type="text" class="input-custom"
              placeholder="Rua das Flores" autocomplete="off" />
          </div>
          <div class="col-span-1">
            <label class="label-custom">Número</label>
            <input v-model="profile.address_number" type="text" class="input-custom"
              placeholder="123" autocomplete="off" />
          </div>
          <div class="col-span-3">
            <label class="label-custom">Bairro</label>
            <input v-model="profile.address_district" type="text" class="input-custom"
              placeholder="Centro" autocomplete="off" />
          </div>
          <div class="col-span-2">
            <label class="label-custom">Complemento</label>
            <input v-model="profile.address_extra" type="text" class="input-custom"
              placeholder="Sala 201" autocomplete="off" />
          </div>
          <div class="col-span-3">
            <label class="label-custom">Cidade</label>
            <input v-model="profile.address_city" type="text" class="input-custom"
              placeholder="São Paulo" autocomplete="off" />
          </div>
          <div class="col-span-1">
            <label class="label-custom">Estado</label>
            <input v-model="profile.address_state" type="text" class="input-custom"
              placeholder="SP" maxlength="2" autocomplete="off" />
          </div>
          <div class="col-span-2">
            <label class="label-custom">País</label>
            <input v-model="profile.address_country" type="text" class="input-custom"
              placeholder="Brasil" autocomplete="off" />
          </div>
          <div class="col-span-6">
            <label class="label-custom">Ponto de Referência</label>
            <input v-model="profile.address_reference" type="text" class="input-custom"
              placeholder="Próximo ao mercado central" autocomplete="off" />
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3">
        <button @click="handleSaveProfile" :disabled="profileSaving" class="btn-primary">
          <svg v-if="profileSaving" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          Salvar Empresa
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         SERVIÇOS
    ══════════════════════════════════════════════════════ -->
    <div v-else-if="activeSubTab === 'servicos'" class="space-y-6">

      <!-- SSL / Domínio -->
      <div class="card-section">
        <div class="mb-4">
          <h3 class="section-title">SSL / Domínio</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Domínio público e e-mail para emissão automática de certificado Let's Encrypt via Certbot.
          </p>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Domínio</label>
            <input v-model="config.DOMAIN_NAME" type="text" class="input-custom"
              placeholder="meuapp.com.br" autocomplete="off" />
          </div>
          <div>
            <label class="label-custom">E-mail (Certbot / Let's Encrypt)</label>
            <input v-model="config.CERTBOT_EMAIL" type="email" class="input-custom"
              placeholder="admin@meuapp.com.br" autocomplete="off" />
          </div>
        </div>
      </div>

      <!-- Observabilidade -->
      <div class="card-section">
        <div class="mb-4">
          <h3 class="section-title">Observabilidade</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Integração com Sentry para rastreamento de erros em produção.
          </p>
        </div>
        <div>
          <label class="label-custom">Sentry DSN</label>
          <input v-model="config.SENTRY_DSN" type="text" class="input-custom"
            placeholder="https://xxxx@oXXX.ingest.sentry.io/YYYY" autocomplete="off" />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Deixe em branco para desativar o Sentry.
          </p>
        </div>
      </div>

      <!-- Reinício automático -->
      <div class="card-section">
        <div class="mb-4">
          <h3 class="section-title">Reinício Automático</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Comandos executados em background após salvar as configurações do sistema.
          </p>
        </div>
        <div>
          <label class="label-custom">Comandos (separados por <code class="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">;</code>)</label>
          <textarea v-model="config.SERVICE_RESTART_COMMANDS" rows="4" class="input-custom resize-y"
            placeholder="docker compose restart web; docker compose restart celery"></textarea>
        </div>
      </div>

      <!-- Limites ópticos -->
      <div class="card-section">
        <div class="mb-4">
          <h3 class="section-title">Limiares de Potência Óptica (RX)</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Valores de referência para alertas de sinal óptico recebido (dBm).
          </p>
        </div>
        <div class="grid grid-cols-2 gap-6">
          <div>
            <label class="label-custom flex items-center gap-2">
              <span class="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400"></span>
              Alerta (Warning)
            </label>
            <div class="flex items-center gap-2">
              <input v-model="config.OPTICAL_RX_WARNING_THRESHOLD" type="number" step="0.5"
                class="input-custom" placeholder="-24" autocomplete="off" />
              <span class="text-sm text-gray-500 dark:text-gray-400 flex-none">dBm</span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Padrão: -24 dBm</p>
          </div>
          <div>
            <label class="label-custom flex items-center gap-2">
              <span class="inline-block w-2.5 h-2.5 rounded-full bg-red-500"></span>
              Crítico (Critical)
            </label>
            <div class="flex items-center gap-2">
              <input v-model="config.OPTICAL_RX_CRITICAL_THRESHOLD" type="number" step="0.5"
                class="input-custom" placeholder="-27" autocomplete="off" />
              <span class="text-sm text-gray-500 dark:text-gray-400 flex-none">dBm</span>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Padrão: -27 dBm</p>
          </div>
        </div>
      </div>

      <div class="flex justify-end gap-3">
        <button @click="handleReset" class="btn-secondary">Resetar</button>
        <button @click="handleSave" :disabled="saving" class="btn-primary">
          <svg v-if="saving" class="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          Salvar Serviços
        </button>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════
         CRON
    ══════════════════════════════════════════════════════ -->
    <div v-else-if="activeSubTab === 'cron'" class="space-y-4">
      <CronTab />
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { useCompanyProfile } from '@/composables/useCompanyProfile'
import CronTab from '@/components/Configuration/CronTab.vue'

// ── System config composable ──────────────────────────────
const {
  config,
  testResults,
  loading,
  isValid,
  testingRedis,
  testingDatabase,
  loadSystemConfig,
  saveSystemConfig,
  testRedis,
  testDatabase,
  clearTestResults,
  resetForm,
} = useSystemConfig()

// ── Company profile composable ────────────────────────────
const {
  loading: profileLoading,
  saving: profileSaving,
  profile,
  logoPreview,
  certFile,
  loadProfile,
  saveProfile,
  onLogoChange,
  removeLogo,
  onCertChange,
  removeCert,
} = useCompanyProfile()

// ── Local state ───────────────────────────────────────────
const saving = ref(false)
const showSecretKey = ref(false)
const activeSubTab = ref('infra')

const subTabs = [
  { id: 'infra',     label: 'Infraestrutura' },
  { id: 'seguranca', label: 'Segurança' },
  { id: 'empresa',   label: 'Empresa' },
  { id: 'servicos',  label: 'Serviços' },
  { id: 'cron',      label: 'Cron' },
]

// ── Handlers ──────────────────────────────────────────────
const handleSave = async () => {
  saving.value = true
  try {
    const ok = await saveSystemConfig()
    if (ok) clearTestResults()
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (confirm('Resetar formulário? As alterações não salvas serão perdidas.')) {
    resetForm()
    clearTestResults()
  }
}

const handleSaveProfile = async () => {
  await saveProfile()
}

// Load empresa profile only when tab becomes active
watch(activeSubTab, (tab) => {
  if (tab === 'empresa' && !profile.value.company_legal_name) {
    loadProfile()
  }
})

// ── Lifecycle ─────────────────────────────────────────────
onMounted(async () => {
  await loadSystemConfig()
})
</script>

<style scoped>
.card-section {
  background-color: #ffffff;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  padding: 1.5rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.label-custom {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.375rem;
}

.input-custom {
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  color: #111827;
  transition: all 0.2s;
}

.input-custom::placeholder { color: #9ca3af; }

.input-custom:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #3b82f6;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) { background-color: #2563eb; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #ffffff;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  border: 1px solid #d1d5db;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover:not(:disabled) { background-color: #f9fafb; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.badge-success {
  display: inline-flex;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: #d1fae5;
  color: #065f46;
}

.badge-gray {
  display: inline-flex;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  background-color: #f3f4f6;
  color: #4b5563;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 0.375rem;
  font-size: 0.875rem;
}
.result-success { background-color: #d1fae5; color: #065f46; }
.result-error   { background-color: #fee2e2; color: #991b1b; }

.loading-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  border-radius: 0.5rem;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 4px solid #bfdbfe;
  border-top-color: #3b82f6;
  border-radius: 9999px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>

<style>
/* Dark mode — não-scoped para garantir herança */
html.dark .card-section,
.dark .card-section {
  background-color: #1f2937;
  border-color: #374151;
}

html.dark .section-title,
.dark .section-title { color: #f9fafb; }

html.dark .input-custom,
.dark .input-custom {
  border-color: #374151;
  background-color: #1f2937 !important;
  color: #e5e7eb;
}

html.dark .input-custom::placeholder,
.dark .input-custom::placeholder { color: #6b7280; }

html.dark .input-custom:focus,
.dark .input-custom:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

html.dark .label-custom,
.dark .label-custom { color: #e5e7eb; }

html.dark .btn-secondary,
.dark .btn-secondary {
  background-color: #374151;
  color: #f3f4f6;
  border-color: #4b5563;
}

html.dark .btn-secondary:hover:not(:disabled),
.dark .btn-secondary:hover:not(:disabled) { background-color: #4b5563; }

html.dark .badge-success,
.dark .badge-success {
  background-color: rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
}

html.dark .badge-gray,
.dark .badge-gray {
  background-color: #374151;
  color: #9ca3af;
}

html.dark .loading-overlay,
.dark .loading-overlay { background-color: rgba(17, 24, 39, 0.8); }

html.dark .loading-spinner,
.dark .loading-spinner {
  border-color: #1e3a8a;
  border-top-color: #60a5fa;
}

html.dark .result-success,
.dark .result-success {
  background-color: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
}

html.dark .result-error,
.dark .result-error {
  background-color: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
}
</style>
