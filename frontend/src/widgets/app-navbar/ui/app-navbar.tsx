import { Link } from "@tanstack/react-router";

const navItems = [
  {
    to: "/sessions",
    label: "Sessions",
    description: "Session graph, focus state, and agent execution"
  },
  {
    to: "/channels",
    label: "Channels",
    description: "Delivery surfaces, status, and channel inventory"
  },
  {
    to: "/settings",
    label: "Settings",
    description: "Skills import, models, and configuration policy"
  }
] as const;

export function AppNavbar() {
  return (
    <header className="app-navbar">
      <div className="app-navbar__brand">
        <span className="eyebrow">NightOwl Control Tower</span>
        <strong>Frontend Console</strong>
      </div>

      <nav aria-label="Primary" className="app-navbar__links">
        {navItems.map((item) => (
          <Link
            activeProps={{ className: "app-navbar__link app-navbar__link--active" }}
            className="app-navbar__link"
            key={item.to}
            to={item.to}
          >
            <span>{item.label}</span>
            <small>{item.description}</small>
          </Link>
        ))}
      </nav>
    </header>
  );
}
