<template>
  <div class="h-full overflow-auto bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
    <div class="max-w-5xl mx-auto space-y-6 py-6 px-4">
      <!-- Header -->
      <header class="space-y-3">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
              System Configuration
            </h1>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Manage environment variables and integration settings. Changes are saved to
              <code class="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">.env</code>
              and database.
            </p>
          </div>
          <div class="flex items-center space-x-2">
            <button
              type="button"
              @click="exportConfig"
              title="Export Configuration"
              class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ph-download class="h-4 w-4 mr-1.5" />
              Export
            </button>

            <button
              type="button"
              @click="importConfig"
              title="Import Configuration"
              class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ph-upload class="h-4 w-4 mr-1.5" />
              Import
            </button>

            <button
              type="button"
              @click="showAuditHistory"
              title="View Audit History"
              class="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <ph-clock-counter-clockwise class="h-4 w-4 mr-1.5" />
              History
            </button>
          </div>
        </div>
      </header>

      <!-- Success/Error Messages -->
      <div v-if="successMessage" class="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4">
        <div class="flex items-center">
          <ph-check-circle class="h-5 w-5 text-green-600 dark:text-green-400 mr-3" weight="fill" />
          <p class="text-sm text-green-800 dark:text-green-300">{{ successMessage }}</p>
        </div>
      </div>

      <div v-if="errorMessage" class="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4">
        <div class="flex items-center">
          <ph-x-circle class="h-5 w-5 text-red-600 dark:text-red-400 mr-3" weight="fill" />
          <p class="text-sm text-red-800 dark:text-red-300">{{ errorMessage }}</p>
        </div>
      </div>

      <!-- Configuration Form -->
      <form @submit.prevent="saveConfiguration" class="space-y-6">
        <!-- Django Core Settings -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Django Core Settings</h2>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Security and debug configuration</p>
          </div>
          <div class="px-6 py-5 space-y-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <!-- SECRET_KEY -->
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Secret Key <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.SECRET_KEY"
                  type="text"
                  required
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
                />
              </div>

              <!-- DEBUG -->
              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="config.DEBUG"
                    type="checkbox"
                    class="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">Debug Mode</span>
                </label>
              </div>

              <!-- ALLOWED_HOSTS -->
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Allowed Hosts
                </label>
                <input
                  v-model="config.ALLOWED_HOSTS"
                  type="text"
                  placeholder="localhost,127.0.0.1,example.com"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- ENABLE_DIAGNOSTIC_ENDPOINTS -->
              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="config.ENABLE_DIAGNOSTIC_ENDPOINTS"
                    type="checkbox"
                    class="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">Enable Diagnostic Endpoints</span>
                </label>
              </div>
            </div>
          </div>
        </section>

        <!-- Zabbix Integration -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <div class="flex items-center justify-between mb-3">
              <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Zabbix Integration</h2>
                <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Monitoring server connection settings</p>
              </div>
              <button
                type="button"
                @click="testZabbixConnection"
                :disabled="testingZabbix"
                :class="[
                  'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50',
                  zabbixTestResult === 'success' ? 'bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600' :
                  zabbixTestResult === 'error' ? 'bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600' :
                  'bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600'
                ]"
              >
                <ph-spinner v-if="testingZabbix" class="h-4 w-4 animate-spin" />
                <ph-check-circle v-else-if="zabbixTestResult === 'success'" class="h-4 w-4" weight="fill" />
                <ph-x-circle v-else-if="zabbixTestResult === 'error'" class="h-4 w-4" weight="fill" />
                <ph-check-circle v-else class="h-4 w-4" />
                Test Connection
              </button>
            </div>
            
            <!-- Zabbix Test Result Message -->
            <div v-if="zabbixTestMessage" class="text-right">
              <p 
                :class="[
                  'text-sm',
                  zabbixTestResult === 'success' 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                ]"
              >
                {{ zabbixTestMessage }}
              </p>
            </div>
          </div>

          <div class="px-6 py-5 space-y-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <!-- ZABBIX_API_URL -->
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Zabbix API URL <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.ZABBIX_API_URL"
                  type="url"
                  required
                  placeholder="https://zabbix.example.com/api_jsonrpc.php"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- ZABBIX_API_USER -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Zabbix User
                </label>
                <input
                  v-model="config.ZABBIX_API_USER"
                  type="text"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- ZABBIX_API_PASSWORD -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Zabbix Password
                </label>
                <input
                  v-model="config.ZABBIX_API_PASSWORD"
                  type="password"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- ZABBIX_API_KEY -->
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Zabbix API Key (alternative to user/password)
                </label>
                <input
                  v-model="config.ZABBIX_API_KEY"
                  type="text"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- External Services -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">External Services</h2>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Third-party integrations and APIs</p>
          </div>
          <div class="px-6 py-5 space-y-5">
            <!-- GOOGLE_MAPS_API_KEY -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Google Maps API Key
              </label>
              <input
                v-model="config.GOOGLE_MAPS_API_KEY"
                type="text"
                class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
              />
            </div>
          </div>
        </section>

        <!-- Database Configuration -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <div class="flex items-center justify-between mb-3">
              <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Database Configuration</h2>
                <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">PostgreSQL connection settings</p>
              </div>
              <button
                type="button"
                @click="testDatabaseConnection"
                :disabled="testingDatabase"
                :class="[
                  'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50',
                  databaseTestResult === 'success' ? 'bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600' :
                  databaseTestResult === 'error' ? 'bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600' :
                  'bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600'
                ]"
              >
                <ph-spinner v-if="testingDatabase" class="h-4 w-4 animate-spin" />
                <ph-database v-else-if="databaseTestResult === 'success'" class="h-4 w-4" weight="fill" />
                <ph-x-circle v-else-if="databaseTestResult === 'error'" class="h-4 w-4" weight="fill" />
                <ph-database v-else class="h-4 w-4" />
                Test Connection
              </button>
            </div>
            
            <!-- Database Test Result Message -->
            <div v-if="databaseTestMessage" class="text-right">
              <p 
                :class="[
                  'text-sm',
                  databaseTestResult === 'success' 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                ]"
              >
                {{ databaseTestMessage }}
              </p>
            </div>
          </div>

          <div class="px-6 py-5 space-y-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <!-- DB_HOST -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Database Host <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.DB_HOST"
                  type="text"
                  required
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- DB_PORT -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Database Port <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.DB_PORT"
                  type="text"
                  required
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- DB_NAME -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Database Name <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.DB_NAME"
                  type="text"
                  required
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- DB_USER -->
              <div class="space-y-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Database User <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="config.DB_USER"
                  type="text"
                  required
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>

              <!-- DB_PASSWORD -->
              <div class="space-y-2 md:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Database Password
                </label>
                <input
                  v-model="config.DB_PASSWORD"
                  type="password"
                  class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- Redis & Caching -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <div class="flex items-center justify-between mb-3">
              <div>
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Redis & Caching</h2>
                <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Cache and Celery broker configuration</p>
              </div>
              <button
                type="button"
                @click="testRedisConnection"
                :disabled="testingRedis"
                :class="[
                  'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50',
                  redisTestResult === 'success' ? 'bg-green-600 dark:bg-green-500 hover:bg-green-700 dark:hover:bg-green-600' :
                  redisTestResult === 'error' ? 'bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600' :
                  'bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600'
                ]"
              >
                <ph-spinner v-if="testingRedis" class="h-4 w-4 animate-spin" />
                <ph-check-circle v-else-if="redisTestResult === 'success'" class="h-4 w-4" weight="fill" />
                <ph-x-circle v-else-if="redisTestResult === 'error'" class="h-4 w-4" weight="fill" />
                <ph-check-circle v-else class="h-4 w-4" />
                Test Connection
              </button>
            </div>
            
            <!-- Redis Test Result Message -->
            <div v-if="redisTestMessage" class="text-right">
              <p 
                :class="[
                  'text-sm',
                  redisTestResult === 'success' 
                    ? 'text-green-600 dark:text-green-400' 
                    : 'text-red-600 dark:text-red-400'
                ]"
              >
                {{ redisTestMessage }}
              </p>
            </div>
          </div>
          
          <div class="px-6 py-5 space-y-5">
            <!-- REDIS_URL -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Redis URL
              </label>
              <input
                v-model="config.REDIS_URL"
                type="text"
                placeholder="redis://localhost:6379/1"
                class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
              />
            </div>
          </div>
        </section>

        <!-- System Operations -->
        <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm overflow-hidden">
          <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">System Operations</h2>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Service management and restart commands</p>
          </div>
          <div class="px-6 py-5 space-y-5">
            <!-- SERVICE_RESTART_COMMANDS -->
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Service Restart Commands
              </label>
              <textarea
                v-model="config.SERVICE_RESTART_COMMANDS"
                rows="3"
                class="block w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm font-mono"
              ></textarea>
            </div>
          </div>
        </section>

        <!-- Submit Button -->
        <div class="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="submit"
            :disabled="saving"
            class="inline-flex items-center px-6 py-3 border border-transparent rounded-lg shadow-sm text-base font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ph-spinner v-if="saving" class="h-5 w-5 mr-2 animate-spin" />
            <ph-floppy-disk v-else class="h-5 w-5 mr-2" />
            {{ saving ? 'Saving...' : 'Save Configuration' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Audit History Modal -->
    <div
      v-if="showAuditModal"
      class="fixed inset-0 z-50 overflow-y-auto"
      @click.self="showAuditModal = false"
    >
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-4xl w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Configuration Audit History</h3>
            <button
              @click="showAuditModal = false"
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <ph-x class="h-6 w-6" />
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Action</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Section</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Timestamp</th>
                  <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                <tr v-for="audit in auditHistory" :key="audit.id">
                  <td class="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{{ audit.user }}</td>
                  <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ audit.action }}</td>
                  <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ audit.section }}</td>
                  <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ formatDate(audit.timestamp) }}</td>
                  <td class="px-4 py-3 text-sm">
                    <span
                      :class="audit.success ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'"
                      class="inline-flex rounded-full px-2 py-1 text-xs font-semibold"
                    >
                      {{ audit.success ? 'Success' : 'Failed' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import {
  PhDownload,
  PhUpload,
  PhClockCounterClockwise,
  PhCheckCircle,
  PhXCircle,
  PhSpinner,
  PhFloppyDisk,
  PhDatabase,
  PhX,
} from '@phosphor-icons/vue';

const config = ref({
  SECRET_KEY: '',
  DEBUG: false,
  ZABBIX_API_URL: '',
  ZABBIX_API_USER: '',
  ZABBIX_API_PASSWORD: '',
  ZABBIX_API_KEY: '',
  GOOGLE_MAPS_API_KEY: '',
  ALLOWED_HOSTS: '',
  ENABLE_DIAGNOSTIC_ENDPOINTS: false,
  DB_HOST: '',
  DB_PORT: '',
  DB_NAME: '',
  DB_USER: '',
  DB_PASSWORD: '',
  REDIS_URL: '',
  SERVICE_RESTART_COMMANDS: '',
});

const saving = ref(false);
const testingZabbix = ref(false);
const testingDatabase = ref(false);
const testingRedis = ref(false);
const zabbixTestResult = ref(null); // 'success' | 'error' | null
const databaseTestResult = ref(null); // 'success' | 'error' | null
const redisTestResult = ref(null); // 'success' | 'error' | null
const zabbixTestMessage = ref('');
const databaseTestMessage = ref('');
const redisTestMessage = ref('');
const successMessage = ref('');
const errorMessage = ref('');
const showAuditModal = ref(false);
const auditHistory = ref([]);

const getCsrfToken = () => {
  const name = 'csrftoken';
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
};

const loadConfiguration = async () => {
  try {
    const response = await fetch('/setup_app/api/config/', {
      headers: {
        'X-CSRFToken': getCsrfToken(),
      },
    });
    const data = await response.json();
    if (data.success) {
      config.value = { ...config.value, ...data.configuration };
    }
  } catch (error) {
    console.error('Failed to load configuration:', error);
  }
};

const saveConfiguration = async () => {
  saving.value = true;
  successMessage.value = '';
  errorMessage.value = '';

  try {
    const response = await fetch('/setup_app/api/config/update/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(config.value),
    });

    const data = await response.json();

    if (data.success) {
      successMessage.value = data.message;
      setTimeout(() => {
        successMessage.value = '';
      }, 5000);
    } else {
      errorMessage.value = data.message;
    }
  } catch (error) {
    errorMessage.value = `Failed to save configuration: ${error.message}`;
  } finally {
    saving.value = false;
  }
};

const testZabbixConnection = async () => {
  testingZabbix.value = true;
  zabbixTestResult.value = null;
  zabbixTestMessage.value = '';
  successMessage.value = '';
  errorMessage.value = '';

  try {
    const response = await fetch('/setup_app/api/test-zabbix/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        zabbix_api_url: config.value.ZABBIX_API_URL,
        zabbix_api_user: config.value.ZABBIX_API_USER,
        zabbix_api_password: config.value.ZABBIX_API_PASSWORD,
        zabbix_api_key: config.value.ZABBIX_API_KEY,
        auth_type: config.value.ZABBIX_API_KEY ? 'token' : 'login',
      }),
    });

    const data = await response.json();

    if (data.success) {
      zabbixTestResult.value = 'success';
      zabbixTestMessage.value = data.message;
      setTimeout(() => {
        zabbixTestMessage.value = '';
        zabbixTestResult.value = null;
      }, 10000);
    } else {
      zabbixTestResult.value = 'error';
      zabbixTestMessage.value = data.message;
    }
  } catch (error) {
    zabbixTestResult.value = 'error';
    zabbixTestMessage.value = `Test failed: ${error.message}`;
  } finally {
    testingZabbix.value = false;
  }
};

const testDatabaseConnection = async () => {
  testingDatabase.value = true;
  databaseTestResult.value = null;
  databaseTestMessage.value = '';
  successMessage.value = '';
  errorMessage.value = '';

  try {
    const response = await fetch('/setup_app/api/test-database/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        db_host: config.value.DB_HOST,
        db_port: config.value.DB_PORT,
        db_name: config.value.DB_NAME,
        db_user: config.value.DB_USER,
        db_password: config.value.DB_PASSWORD,
      }),
    });

    const data = await response.json();

    if (data.success) {
      databaseTestResult.value = 'success';
      databaseTestMessage.value = data.message;
      setTimeout(() => {
        databaseTestMessage.value = '';
        databaseTestResult.value = null;
      }, 10000);
    } else {
      databaseTestResult.value = 'error';
      databaseTestMessage.value = data.message;
    }
  } catch (error) {
    databaseTestResult.value = 'error';
    databaseTestMessage.value = `Test failed: ${error.message}`;
  } finally {
    testingDatabase.value = false;
  }
};

const testRedisConnection = async () => {
  testingRedis.value = true;
  redisTestResult.value = null;
  redisTestMessage.value = '';
  successMessage.value = '';
  errorMessage.value = '';

  try {
    const response = await fetch('/setup_app/api/test-redis/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        redis_url: config.value.REDIS_URL,
      }),
    });

    const data = await response.json();

    if (data.success) {
      redisTestResult.value = 'success';
      redisTestMessage.value = data.message;
      setTimeout(() => {
        redisTestMessage.value = '';
        redisTestResult.value = null;
      }, 10000);
    } else {
      redisTestResult.value = 'error';
      redisTestMessage.value = data.message;
    }
  } catch (error) {
    redisTestResult.value = 'error';
    redisTestMessage.value = `Test failed: ${error.message}`;
  } finally {
    testingRedis.value = false;
  }
};

const exportConfig = async () => {
  try {
    const response = await fetch('/setup_app/api/export/', {
      headers: {
        'X-CSRFToken': getCsrfToken(),
      },
    });
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `config_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    successMessage.value = 'Configuration exported successfully';
  } catch (error) {
    errorMessage.value = `Export failed: ${error.message}`;
  }
};

const importConfig = () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/setup_app/api/import/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        successMessage.value = data.message;
        await loadConfiguration();
      } else {
        errorMessage.value = data.message;
      }
    } catch (error) {
      errorMessage.value = `Import failed: ${error.message}`;
    }
  };
  input.click();
};

const showAuditHistory = async () => {
  try {
    const response = await fetch('/setup_app/api/audit-history/?limit=50', {
      headers: {
        'X-CSRFToken': getCsrfToken(),
      },
    });
    const data = await response.json();
    if (data.success) {
      auditHistory.value = data.audits;
      showAuditModal.value = true;
    }
  } catch (error) {
    errorMessage.value = `Failed to load audit history: ${error.message}`;
  }
};

const formatDate = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleString();
};

onMounted(() => {
  loadConfiguration();
});
</script>
