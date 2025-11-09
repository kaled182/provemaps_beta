document.addEventListener('DOMContentLoaded', () => {
  const userMenuButton = document.getElementById('userMenuButton');
  const userMenuDropdown = document.getElementById('userMenuDropdown');
  const userMenuArrow = document.getElementById('userMenuArrow');

  if (userMenuButton && userMenuDropdown) {
    userMenuButton.addEventListener('click', (event) => {
      event.stopPropagation();
      const isHidden = userMenuDropdown.classList.contains('hidden');
      userMenuDropdown.classList.toggle('hidden', !isHidden);
      if (userMenuArrow) userMenuArrow.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    });

    document.addEventListener('click', (event) => {
      if (!userMenuButton.contains(event.target) && !userMenuDropdown.contains(event.target)) {
        userMenuDropdown.classList.add('hidden');
        if (userMenuArrow) userMenuArrow.style.transform = 'rotate(0deg)';
      }
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        userMenuDropdown.classList.add('hidden');
        if (userMenuArrow) userMenuArrow.style.transform = 'rotate(0deg)';
      }
    });
  }

  const themeToggle = document.getElementById('themeToggle');
  const iconSun = document.getElementById('iconSun');
  const iconMoon = document.getElementById('iconMoon');

  if (themeToggle && iconSun && iconMoon) {
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.classList.toggle('dark', currentTheme === 'dark');

    if (currentTheme === 'dark') {
      iconSun.classList.remove('hidden');
      iconMoon.classList.add('hidden');
    } else {
      iconSun.classList.add('hidden');
      iconMoon.classList.remove('hidden');
    }

    themeToggle.addEventListener('click', () => {
      const isDark = document.documentElement.classList.contains('dark');
      if (isDark) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
        iconSun.classList.add('hidden');
        iconMoon.classList.remove('hidden');
      } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
        iconSun.classList.remove('hidden');
        iconMoon.classList.add('hidden');
      }
    });
  }

  const mobileToggle = document.querySelector('[data-mobile-toggle]');
  const mobileNav = document.getElementById('mobileNav');

  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const isExpanded = mobileToggle.getAttribute('aria-expanded') === 'true';
      mobileToggle.setAttribute('aria-expanded', (!isExpanded).toString());
      mobileNav.classList.toggle('hidden');
    });
  }
});
