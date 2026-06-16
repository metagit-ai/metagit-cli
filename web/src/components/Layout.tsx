import { NavLink, Outlet } from 'react-router-dom'
import logoPng from '../assets/metagit_logo_header.png'
import logoWebp from '../assets/metagit_logo_header.webp'
import { useThemeStore } from '../theme/useThemeStore'
import styles from './Layout.module.css'

const GITHUB_REPO_URL = 'https://github.com/metagit-ai/metagit-cli'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink

export default function Layout() {
  const resolved = useThemeStore((state) => state.resolved)
  const toggleResolved = useThemeStore((state) => state.toggleResolved)

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <a
            href={GITHUB_REPO_URL}
            className={styles.logoLink}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Metagit on GitHub"
          >
            <picture>
              <source srcSet={logoWebp} type="image/webp" />
              <img
                src={logoPng}
                alt=""
                className={styles.logo}
                width={128}
                height={128}
              />
            </picture>
          </a>
          <h1 className={styles.title}>Metagit Web</h1>
        </div>
        <nav className={styles.nav} aria-label="Main">
          <NavLink to="/workspace" className={navLinkClass}>
            Workspace
          </NavLink>
          <NavLink to="/agents" className={navLinkClass}>
            Agents
          </NavLink>
          <NavLink to="/config/metagit" className={navLinkClass}>
            Metagit config
          </NavLink>
          <NavLink to="/config/appconfig" className={navLinkClass}>
            App config
          </NavLink>
        </nav>
        <button
          type="button"
          className={styles.themeToggle}
          onClick={toggleResolved}
          aria-label={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} theme`}
        >
          {resolved === 'dark' ? (
            <span className={styles.themeIcon} aria-hidden>
              ☀
            </span>
          ) : (
            <span className={styles.themeIcon} aria-hidden>
              ☾
            </span>
          )}
        </button>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
