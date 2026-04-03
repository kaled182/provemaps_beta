<template>
  <div class="docs-container h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <PhBook :size="32" weight="bold" class="text-blue-600 dark:text-blue-400" />
          MapsProveFiber Documentation
        </h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">
          Comprehensive guides for developers, operators, and contributors
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- Sidebar Navigation -->
        <aside class="lg:col-span-1">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sticky top-4">
            <h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
              <PhList :size="18" weight="bold" />
              Navigation
            </h2>
            
            <!-- Search Box -->
            <div class="mb-4">
              <div class="relative">
                <PhMagnifyingGlass :size="18" class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search docs..."
                  class="w-full pl-10 pr-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <!-- Navigation Tree -->
            <nav class="space-y-1">
              <div v-for="section in filteredSections" :key="section.title" class="mb-3">
                <button
                  @click="toggleSection(section.title)"
                  class="w-full flex items-center justify-between text-left px-2 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                >
                  <span class="flex items-center gap-2">
                    <component :is="section.icon" :size="16" weight="bold" />
                    {{ section.title }}
                  </span>
                  <PhCaretDown
                    v-if="expandedSections.has(section.title)"
                    :size="14"
                    weight="bold"
                    class="text-gray-400"
                  />
                  <PhCaretRight
                    v-else
                    :size="14"
                    weight="bold"
                    class="text-gray-400"
                  />
                </button>

                <div
                  v-if="expandedSections.has(section.title)"
                  class="ml-4 mt-1 space-y-0.5"
                >
                  <button
                    v-for="doc in section.docs"
                    :key="doc.path"
                    @click="loadDocument(doc.path)"
                    class="w-full text-left px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
                    :class="{ 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 font-medium': currentDoc === doc.path }"
                  >
                    {{ doc.title }}
                  </button>
                </div>
              </div>
            </nav>
          </div>
        </aside>

        <!-- Main Content -->
        <main class="lg:col-span-3">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 lg:p-8">
            <!-- Loading State -->
            <div v-if="loading" class="flex items-center justify-center py-12">
              <PhSpinner :size="32" class="animate-spin text-blue-600 dark:text-blue-400" />
            </div>

            <!-- Error State -->
            <div v-else-if="error" class="text-center py-12">
              <PhWarning :size="48" weight="fill" class="mx-auto text-red-500 mb-4" />
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Error Loading Document</h3>
              <p class="text-gray-600 dark:text-gray-400">{{ error }}</p>
              <button
                @click="loadDocument(currentDoc)"
                class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>

            <!-- Markdown Content -->
            <div
              v-else-if="htmlContent"
              class="prose prose-slate dark:prose-invert max-w-none"
              v-html="htmlContent"
            ></div>

            <!-- Empty State -->
            <div v-else class="text-center py-12">
              <PhBookOpen :size="64" weight="thin" class="mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Welcome to Documentation</h3>
              <p class="text-gray-600 dark:text-gray-400">Select a document from the sidebar to get started</p>
            </div>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  PhBook,
  PhList,
  PhMagnifyingGlass,
  PhCaretDown,
  PhCaretRight,
  PhSpinner,
  PhWarning,
  PhBookOpen,
  PhRocketLaunch,
  PhBooks,
  PhStack,
  PhPlugs,
  PhUsers,
  PhCode,
  PhShield,
  PhMapPin,
  PhChartBar,
} from '@phosphor-icons/vue';
import { marked } from 'marked';

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const error = ref(null);
const htmlContent = ref('');
const currentDoc = ref('');
const searchQuery = ref('');
const expandedSections = ref(new Set(['Getting Started']));

// Documentation structure
const sections = [
  {
    title: 'Getting Started',
    icon: PhRocketLaunch,
    docs: [
      { title: 'Overview', path: 'README.md' },
      { title: 'Quick Start', path: 'getting-started/QUICKSTART.md' },
      { title: 'Troubleshooting', path: 'getting-started/TROUBLESHOOTING.md' },
    ],
  },
  {
    title: 'Guides',
    icon: PhBooks,
    docs: [
      { title: 'Development', path: 'guides/DEVELOPMENT.md' },
      { title: 'Docker', path: 'guides/DOCKER.md' },
      { title: 'Testing', path: 'guides/TESTING.md' },
      { title: 'Observability', path: 'guides/OBSERVABILITY.md' },
    ],
  },
  {
    title: 'Architecture',
    icon: PhStack,
    docs: [
      { title: 'Overview', path: 'architecture/OVERVIEW.md' },
      { title: 'Modules', path: 'architecture/MODULES.md' },
      { title: 'Data Flow', path: 'architecture/DATA_FLOW.md' },
    ],
  },
  {
    title: 'API',
    icon: PhPlugs,
    docs: [
      { title: 'Endpoints', path: 'api/ENDPOINTS.md' },
      { title: 'Authentication', path: 'api/AUTHENTICATION.md' },
    ],
  },
  {
    title: 'Contributing',
    icon: PhUsers,
    docs: [
      { title: 'Contributing Guide', path: 'contributing/CONTRIBUTING.md' },
      { title: 'Code Standards', path: 'contributing/CODE_STANDARDS.md' },
    ],
  },
  {
    title: 'Developer',
    icon: PhCode,
    docs: [
      { title: 'IDE Setup', path: 'developer/IDE_SETUP.md' },
      { title: 'Debugging', path: 'developer/DEBUGGING.md' },
    ],
  },
  {
    title: 'Security',
    icon: PhShield,
    docs: [
      { title: 'Security Policy', path: 'security/SECURITY.md' },
    ],
  },
  {
    title: 'Roadmap',
    icon: PhMapPin,
    docs: [
      { title: 'Roadmap', path: 'roadmap/ROADMAP.md' },
    ],
  },
];

const filteredSections = computed(() => {
  if (!searchQuery.value.trim()) {
    return sections;
  }

  const query = searchQuery.value.toLowerCase();
  return sections
    .map(section => ({
      ...section,
      docs: section.docs.filter(doc =>
        doc.title.toLowerCase().includes(query) ||
        doc.path.toLowerCase().includes(query)
      ),
    }))
    .filter(section => section.docs.length > 0);
});

function toggleSection(sectionTitle) {
  if (expandedSections.value.has(sectionTitle)) {
    expandedSections.value.delete(sectionTitle);
  } else {
    expandedSections.value.add(sectionTitle);
  }
  expandedSections.value = new Set(expandedSections.value);
}

async function loadDocument(docPath) {
  currentDoc.value = docPath;
  loading.value = true;
  error.value = null;
  htmlContent.value = '';

  try {
    const response = await fetch(`/api/docs/${docPath}`);
    if (!response.ok) {
      throw new Error(`Failed to load document: ${response.statusText}`);
    }

    const markdown = await response.text();
    htmlContent.value = marked.parse(markdown);

    // Update URL without reloading
    router.push({ path: '/docs', query: { doc: docPath } });
  } catch (err) {
    console.error('Error loading document:', err);
    error.value = err.message || 'Failed to load document';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  // Load document from query parameter or default
  const docPath = route.query.doc || 'README.md';
  loadDocument(docPath);

  // Expand section containing current doc
  sections.forEach(section => {
    if (section.docs.some(doc => doc.path === docPath)) {
      expandedSections.value.add(section.title);
    }
  });
});
</script>

<style scoped>
/* Markdown prose styles */
.prose {
  @apply text-gray-700 dark:text-gray-300;
}

.prose :deep(h1) {
  @apply text-3xl font-bold text-gray-900 dark:text-white mb-6 pb-3 border-b border-gray-200 dark:border-gray-700;
}

.prose :deep(h2) {
  @apply text-2xl font-semibold text-gray-900 dark:text-white mt-8 mb-4;
}

.prose :deep(h3) {
  @apply text-xl font-semibold text-gray-800 dark:text-gray-200 mt-6 mb-3;
}

.prose :deep(h4) {
  @apply text-lg font-semibold text-gray-800 dark:text-gray-200 mt-4 mb-2;
}

.prose :deep(p) {
  @apply mb-4 leading-relaxed;
}

.prose :deep(a) {
  @apply text-blue-600 dark:text-blue-400 hover:underline;
}

.prose :deep(code) {
  @apply px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-pink-600 dark:text-pink-400 rounded text-sm font-mono;
}

.prose :deep(pre) {
  @apply bg-gray-900 dark:bg-black text-gray-100 p-4 rounded-lg overflow-x-auto mb-4;
}

.prose :deep(pre code) {
  @apply bg-transparent text-gray-100 p-0;
}

.prose :deep(ul) {
  @apply list-disc list-inside mb-4 space-y-2;
}

.prose :deep(ol) {
  @apply list-decimal list-inside mb-4 space-y-2;
}

.prose :deep(li) {
  @apply ml-4;
}

.prose :deep(blockquote) {
  @apply border-l-4 border-blue-500 pl-4 italic text-gray-600 dark:text-gray-400 my-4;
}

.prose :deep(table) {
  @apply w-full border-collapse mb-4;
}

.prose :deep(th) {
  @apply bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 px-4 py-2 text-left font-semibold;
}

.prose :deep(td) {
  @apply border border-gray-300 dark:border-gray-600 px-4 py-2;
}

.prose :deep(img) {
  @apply rounded-lg shadow-md my-6;
}

.prose :deep(hr) {
  @apply border-gray-300 dark:border-gray-600 my-8;
}
</style>
