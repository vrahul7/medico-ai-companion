import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, BookOpen, Newspaper, X, Stethoscope } from 'lucide-react';

const Sidebar = ({ isOpen, onClose }) => {
  const navItems = [
    { icon: LayoutDashboard, label: 'Control Center', to: '/' },
    { icon: MessageSquare, label: 'MediChat AI', to: '/chat' },
    { icon: Stethoscope, label: 'DDx Assistant', to: '/ddx', premium: true },
    { icon: BookOpen, label: 'Quizzes', to: '/quizzes' },
    { icon: Newspaper, label: 'Daily Briefing', to: '/briefing', premium: true },
  ];

  return (
    <aside className={`glass-sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div className="brand-container">
          <div className="brand-icon pulse-glow">
            <span>M</span>
          </div>
          <span className="brand-text gold-heading-sm">Medico AI</span>
        </div>
        <button onClick={onClose} className="mobile-close-btn">
          <X size={20} />
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item, index) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-item stagger-slide-in ${isActive ? 'active' : ''}`}
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <item.icon size={20} className="nav-icon" />
            <span className="nav-label">{item.label}</span>
            {item.premium && (
              <span className="badge badge-premium shadow-glow">PRO</span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-profile-card">
          <div className="avatar">
            <span>DS</span>
          </div>
          <div className="user-info">
            <span className="user-name">Dr. Swetha</span>
            <span className="user-role">Residency PGY-2</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
