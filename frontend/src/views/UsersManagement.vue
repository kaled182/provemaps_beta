<template>
  <div class="users-management h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <PhGear :size="32" weight="bold" class="text-gray-900 dark:text-white" />
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
          </div>
          <button
            v-if="currentTab === 'members'"
            @click="showInviteModal = true"
            class="px-4 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium"
          >
            Invite people
          </button>
        </div>
      </div>

      <!-- Tabs Navigation -->
      <div class="border-b border-gray-200 dark:border-gray-700 mb-8">
        <nav class="flex gap-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="currentTab = tab.id"
            class="flex items-center gap-2 px-1 py-4 border-b-2 font-medium text-sm transition-colors"
            :class="currentTab === tab.id 
              ? 'border-green-500 text-green-600 dark:text-green-400' 
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
          >
            <component :is="tab.icon" :size="18" weight="bold" />
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- Members Tab -->
        <div v-if="currentTab === 'members'" class="space-y-6">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Members</h2>
            <p class="text-gray-600 dark:text-gray-400">Invite new members by email address.</p>
          </div>

          <!-- Search -->
          <div class="relative max-w-md">
            <PhMagnifyingGlass :size="18" class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search members"
              class="w-full pl-10 pr-3 py-2 border-2 border-green-500 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <!-- Members List -->
          <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="user in filteredUsers"
              :key="user.id"
              class="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div class="flex items-center gap-4">
                <!-- Avatar -->
                <div class="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                  {{ getInitials(user.full_name || user.username) }}
                </div>

                <!-- User Info -->
                <div>
                  <div class="font-semibold text-gray-900 dark:text-white">
                    {{ user.full_name || user.username }}
                  </div>
                  <div class="text-sm text-gray-500 dark:text-gray-400">
                    {{ user.username }}
                  </div>
                </div>
              </div>

              <!-- Role & Actions -->
              <div class="flex items-center gap-3">
                <!-- Role Dropdown -->
                <select
                  :value="getUserRole(user)"
                  @change="changeUserRole(user, $event.target.value)"
                  class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  :disabled="user.is_superuser"
                >
                  <option value="Owner" :disabled="!currentUser.is_superuser">Owner</option>
                  <option value="Admin">Admin</option>
                  <option value="Member">Member</option>
                  <option value="Viewer">Viewer</option>
                </select>

                <!-- Menu Button -->
                <div class="relative">
                  <button
                    @click="toggleUserMenu(user.id)"
                    class="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                  >
                    <PhDotsThree :size="24" weight="bold" class="text-gray-600 dark:text-gray-300" />
                  </button>

                  <!-- Dropdown Menu -->
                  <div
                    v-if="activeUserMenu === user.id"
                    v-click-outside="() => activeUserMenu = null"
                    class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10"
                  >
                    <button
                      @click="editUser(user)"
                      class="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      <PhPencil :size="16" />
                      Edit Profile
                    </button>
                    <button
                      v-if="user.id !== currentUser.id"
                      @click="toggleUserStatus(user)"
                      class="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      <PhProhibit v-if="user.is_active" :size="16" />
                      <PhCheck v-else :size="16" />
                      {{ user.is_active ? 'Deactivate' : 'Activate' }}
                    </button>
                    <button
                      v-if="user.id !== currentUser.id && !user.is_superuser"
                      @click="confirmDeleteUser(user)"
                      class="w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2 rounded-b-lg"
                    >
                      <PhTrash :size="16" />
                      Delete User
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-if="filteredUsers.length === 0" class="p-12 text-center">
              <PhUsers :size="64" weight="thin" class="mx-auto text-gray-300 dark:text-gray-600 mb-4" />
              <p class="text-gray-500 dark:text-gray-400">No users found</p>
            </div>
          </div>
        </div>

        <!-- Profile Tab -->
        <div v-if="currentTab === 'profile'" class="space-y-6">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Profile</h2>
            <p class="text-gray-600 dark:text-gray-400">These informations will be displayed publicly.</p>
          </div>

          <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 max-w-2xl">
            <form @submit.prevent="saveProfile" class="space-y-6">
              <!-- Name -->
              <div>
                <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Name <span class="text-red-500">*</span>
                </label>
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Will appear on receipts, invoices, and other communication.
                </p>
                <input
                  v-model="profileForm.full_name"
                  type="text"
                  required
                  class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="John Doe"
                />
              </div>

              <!-- Email -->
              <div>
                <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Email <span class="text-red-500">*</span>
                </label>
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Used to sign in, for email receipts and product updates.
                </p>
                <input
                  v-model="profileForm.email"
                  type="email"
                  required
                  class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="john@example.com"
                />
              </div>

              <!-- Username -->
              <div>
                <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Username <span class="text-red-500">*</span>
                </label>
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Your unique username for logging in and your profile URL.
                </p>
                <input
                  v-model="profileForm.username"
                  type="text"
                  required
                  disabled
                  class="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-500 dark:text-gray-400 cursor-not-allowed"
                />
              </div>

              <!-- Phone -->
              <div>
                <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Phone
                </label>
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  Contact phone number for support and notifications.
                </p>
                <input
                  v-model="profileForm.phone"
                  type="tel"
                  class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="+1 (555) 123-4567"
                />
              </div>

              <!-- Avatar -->
              <div>
                <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Avatar
                </label>
                <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                  JPG, GIF or PNG. 1MB Max.
                </p>
                <div class="flex items-center gap-4">
                  <div class="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-2xl">
                    {{ getInitials(profileForm.full_name || profileForm.username) }}
                  </div>
                  <button
                    type="button"
                    class="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  >
                    Choose
                  </button>
                </div>
              </div>

              <!-- Save Button -->
              <div class="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  type="submit"
                  :disabled="savingProfile"
                  class="px-6 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors font-medium disabled:opacity-50"
                >
                  {{ savingProfile ? 'Saving...' : 'Save changes' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Security Tab -->
        <div v-if="currentTab === 'security'" class="space-y-6 max-w-2xl">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Security</h2>
            <p class="text-gray-600 dark:text-gray-400">Manage your password and account security.</p>
          </div>

          <!-- Change Password -->
          <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Password</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Confirm your current password before setting a new one.
            </p>

            <form @submit.prevent="changePassword" class="space-y-4">
              <input
                v-model="passwordForm.current"
                type="password"
                placeholder="Current password"
                class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <input
                v-model="passwordForm.new"
                type="password"
                placeholder="New password"
                class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <button
                type="submit"
                class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors font-medium"
              >
                Update
              </button>
            </form>
          </div>

          <!-- Delete Account -->
          <div class="bg-white dark:bg-gray-800 rounded-lg border border-red-200 dark:border-red-900/50 p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Account</h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
              No longer want to use our service? You can delete your account here. This action is not reversible. 
              All information related to this account will be deleted permanently.
            </p>
            <button
              type="button"
              class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium"
            >
              Delete account
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Invite Modal -->
    <div
      v-if="showInviteModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showInviteModal = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <h3 class="text-xl font-bold text-gray-900 dark:text-white mb-4">Invite New Member</h3>
        
        <form @submit.prevent="inviteUser" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Username <span class="text-red-500">*</span>
            </label>
            <input
              v-model="inviteForm.username"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="johndoe"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Email <span class="text-red-500">*</span>
            </label>
            <input
              v-model="inviteForm.email"
              type="email"
              required
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="john@example.com"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Full Name <span class="text-red-500">*</span>
            </label>
            <input
              v-model="inviteForm.full_name"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="John Doe"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Phone
            </label>
            <input
              v-model="inviteForm.phone"
              type="tel"
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="+1 (555) 123-4567"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Password <span class="text-red-500">*</span>
            </label>
            <input
              v-model="inviteForm.password"
              type="password"
              required
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
              Role <span class="text-red-500">*</span>
            </label>
            <select
              v-model="inviteForm.role"
              required
              class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="Member">Member</option>
              <option value="Admin">Admin</option>
              <option value="Viewer">Viewer</option>
            </select>
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <button
              type="button"
              @click="showInviteModal = false"
              class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="inviting"
              class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors font-medium disabled:opacity-50"
            >
              {{ inviting ? 'Inviting...' : 'Send Invite' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
  PhGear,
  PhUser,
  PhUsers,
  PhBell,
  PhShield,
  PhMagnifyingGlass,
  PhDotsThree,
  PhPencil,
  PhTrash,
  PhProhibit,
  PhCheck,
} from '@phosphor-icons/vue';

const currentTab = ref('members');
const searchQuery = ref('');
const users = ref([]);
const groups = ref([]);
const loading = ref(false);
const showInviteModal = ref(false);
const activeUserMenu = ref(null);
const savingProfile = ref(false);
const inviting = ref(false);

// Current user from Django
const currentUser = ref({
  id: window.USER_ID || null,
  username: window.USERNAME || '',
  is_superuser: window.IS_SUPERUSER || false,
});

const tabs = [
  { id: 'profile', label: 'General', icon: PhUser },
  { id: 'members', label: 'Members', icon: PhUsers },
  { id: 'notifications', label: 'Notifications', icon: PhBell },
  { id: 'security', label: 'Security', icon: PhShield },
];

const profileForm = ref({
  username: '',
  email: '',
  full_name: '',
  phone: '',
});

const passwordForm = ref({
  current: '',
  new: '',
});

const inviteForm = ref({
  username: '',
  email: '',
  full_name: '',
  phone: '',
  password: '',
  role: 'Member',
});

const filteredUsers = computed(() => {
  if (!searchQuery.value.trim()) {
    return users.value;
  }

  const query = searchQuery.value.toLowerCase();
  return users.value.filter(user =>
    user.username.toLowerCase().includes(query) ||
    user.email.toLowerCase().includes(query) ||
    (user.full_name && user.full_name.toLowerCase().includes(query))
  );
});

function getInitials(name) {
  if (!name) return '?';
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

function getUserRole(user) {
  if (user.is_superuser) return 'Owner';
  if (user.is_staff) return 'Admin';
  
  const memberGroup = user.groups.find(g => g.name === 'Member');
  if (memberGroup) return 'Member';
  
  return 'Viewer';
}

async function loadUsers() {
  loading.value = true;
  try {
    const response = await fetch('/api/users/');
    const data = await response.json();
    if (data.success) {
      users.value = data.users;
    }
  } catch (error) {
    console.error('Error loading users:', error);
  } finally {
    loading.value = false;
  }
}

async function loadGroups() {
  try {
    const response = await fetch('/api/groups/');
    const data = await response.json();
    if (data.success) {
      groups.value = data.groups;
    }
  } catch (error) {
    console.error('Error loading groups:', error);
  }
}

async function inviteUser() {
  inviting.value = true;
  try {
    const [firstName, ...lastNameParts] = inviteForm.value.full_name.split(' ');
    const lastName = lastNameParts.join(' ');

    const response = await fetch('/api/users/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || '',
      },
      body: JSON.stringify({
        username: inviteForm.value.username,
        email: inviteForm.value.email,
        password: inviteForm.value.password,
        first_name: firstName,
        last_name: lastName,
        is_staff: inviteForm.value.role === 'Admin',
      }),
    });

    const data = await response.json();
    if (data.success) {
      alert('User invited successfully!');
      showInviteModal.value = false;
      inviteForm.value = {
        username: '',
        email: '',
        full_name: '',
        phone: '',
        password: '',
        role: 'Member',
      };
      await loadUsers();
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error('Error inviting user:', error);
    alert('Failed to invite user');
  } finally {
    inviting.value = false;
  }
}

function toggleUserMenu(userId) {
  activeUserMenu.value = activeUserMenu.value === userId ? null : userId;
}

function editUser(user) {
  // TODO: Implement edit modal
  console.log('Edit user:', user);
  activeUserMenu.value = null;
}

async function toggleUserStatus(user) {
  try {
    const response = await fetch(`/api/users/${user.id}/update/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || '',
      },
      body: JSON.stringify({
        is_active: !user.is_active,
      }),
    });

    const data = await response.json();
    if (data.success) {
      await loadUsers();
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error('Error toggling user status:', error);
    alert('Failed to update user status');
  }
  activeUserMenu.value = null;
}

async function confirmDeleteUser(user) {
  if (confirm(`Are you sure you want to delete ${user.username}? This action cannot be undone.`)) {
    try {
      const response = await fetch(`/api/users/${user.id}/delete/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': window.CSRF_TOKEN || '',
        },
      });

      const data = await response.json();
      if (data.success) {
        alert('User deleted successfully');
        await loadUsers();
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Failed to delete user');
    }
  }
  activeUserMenu.value = null;
}

async function changeUserRole(user, newRole) {
  try {
    const response = await fetch(`/api/users/${user.id}/update/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || '',
      },
      body: JSON.stringify({
        is_staff: newRole === 'Admin' || newRole === 'Owner',
      }),
    });

    const data = await response.json();
    if (data.success) {
      await loadUsers();
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error('Error changing user role:', error);
    alert('Failed to change user role');
  }
}

async function saveProfile() {
  savingProfile.value = true;
  try {
    const [firstName, ...lastNameParts] = profileForm.value.full_name.split(' ');
    const lastName = lastNameParts.join(' ');

    const response = await fetch(`/api/users/${currentUser.value.id}/update/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.CSRF_TOKEN || '',
      },
      body: JSON.stringify({
        email: profileForm.value.email,
        first_name: firstName,
        last_name: lastName,
      }),
    });

    const data = await response.json();
    if (data.success) {
      alert('Profile updated successfully!');
    } else {
      alert(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error('Error saving profile:', error);
    alert('Failed to save profile');
  } finally {
    savingProfile.value = false;
  }
}

async function changePassword() {
  // TODO: Implement password change
  console.log('Change password');
}

// Click outside directive
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = function(event) {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value();
      }
    };
    document.body.addEventListener('click', el.clickOutsideEvent);
  },
  unmounted(el) {
    document.body.removeEventListener('click', el.clickOutsideEvent);
  },
};

onMounted(async () => {
  await Promise.all([loadUsers(), loadGroups()]);
  
  // Load current user profile
  if (currentUser.value.id) {
    try {
      const response = await fetch(`/api/users/${currentUser.value.id}/`);
      const data = await response.json();
      if (data.success) {
        profileForm.value = {
          username: data.user.username,
          email: data.user.email,
          full_name: data.user.full_name,
          phone: '', // TODO: Add phone field to User model
        };
      }
    } catch (error) {
      console.error('Error loading current user:', error);
    }
  }
});
</script>

<style scoped>
/* Additional styles if needed */
</style>
