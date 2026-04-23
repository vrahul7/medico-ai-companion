import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, BookOpen, X, LogOut } from 'lucide-react';
import { supabase } from '../services/supabase';

const Sidebar = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const handleLogout = async () => {
    await supabase.auth.signOut();
    navigate('/auth');
  };

  const navItems = [
    { icon: LayoutDashboard, label: 'Clinical Feeds', to: '/' },
    { icon: MessageSquare, label: 'MediChat AI', to: '/chat' },
    { icon: BookOpen, label: 'Quizzes', to: '/quizzes' },
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
          <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', marginLeft: 'auto' }} title="Log Out">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
