import { create } from 'zustand';

type Theme = 'dark' | 'light';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

const getInitialTheme = (): Theme => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('theme-preference') as Theme;
    if (saved) return saved;
  }
  return 'dark'; // Default to dark as preferred by user
};

export const useThemeStore = create<ThemeState>((set) => {
  const initial = getInitialTheme();
  
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', initial);
    document.documentElement.classList.toggle('dark', initial === 'dark');
  }

  return {
    theme: initial,
    toggleTheme: () =>
      set((state) => {
        const newTheme = state.theme === 'dark' ? 'light' : 'dark';
        if (typeof window !== 'undefined') {
          localStorage.setItem('theme-preference', newTheme);
          document.documentElement.setAttribute('data-theme', newTheme);
          document.documentElement.classList.toggle('dark', newTheme === 'dark');
        }
        return { theme: newTheme };
      }),
  };
});
