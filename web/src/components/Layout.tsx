import { NavLink, Outlet } from 'react-router-dom'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link active' : 'nav-link'

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">Metagit Web</h1>
        <nav className="app-nav" aria-label="Main">
          <NavLink to="/workspace" className={navLinkClass}>
            Workspace
          </NavLink>
          <NavLink to="/config/metagit" className={navLinkClass}>
            Metagit config
          </NavLink>
          <NavLink to="/config/appconfig" className={navLinkClass}>
            App config
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
