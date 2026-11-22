import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  FolderGit2,
  Wrench,
  CheckCircle,
  BarChart3,
  History,
  Settings,
  Terminal,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  active: boolean;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: <LayoutDashboard size={18} />, active: true },
  { name: 'Projects', path: '/projects', icon: <FolderGit2 size={18} />, active: true },
  { name: 'New Analysis', path: '/analysis', icon: <PlusCircle size={18} />, active: true },
  { name: 'Code Repairs', path: '/repairs', icon: <Wrench size={18} />, active: false },
  { name: 'Test Results', path: '/test-results', icon: <CheckCircle size={18} />, active: true },
  { name: 'Analytics', path: '/analytics', icon: <BarChart3 size={18} />, active: false },
  { name: 'History', path: '/history', icon: <History size={18} />, active: false },
  { name: 'Settings', path: '/settings', icon: <Settings size={18} />, active: false },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">
          <Terminal size={16} />
          <span>FIXMATE</span>
        </div>
        <div>
          <div className="brand-title">FIXMATE AI</div>
          <div className="brand-subtitle">Autonomous Repair</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) =>
              `nav-link ${isActive && item.active ? 'active' : ''}`
            }
          >
            <div className="nav-link-content">
              {item.icon}
              <span>{item.name}</span>
            </div>
            {!item.active && <span className="badge-coming-soon">Soon</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', fontWeight: 600 }}>
            PHASE 1 FOUNDATION
          </div>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
            v0.1.0 • Dev Mode
          </div>
        </div>
      </div>
    </aside>
  );
};
