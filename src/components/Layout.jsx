import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Menu, Zap } from 'lucide-react';
import Sidebar from './Sidebar';

export default function Layout() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const location = useLocation();

    React.useEffect(() => {
        setIsSidebarOpen(false);
    }, [location]);

    // Omit header on DDx page which handles its own full-screen layout
    const isDDx = location.pathname === '/ddx';

    return (
        <div className="app-container">
            {isSidebarOpen && (
                <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />
            )}
            
            <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

            <div className="main-wrapper">
                {!isDDx && (
                    <header className="glass-header fade-in-down">
                        <div className="header-left">
                            <button className="mobile-menu-btn" onClick={() => setIsSidebarOpen(true)}>
                                <Menu size={24} />
                            </button>
                            <h2 className="header-title">Workspace Overview</h2>
                        </div>
                        <div className="header-right">
                            <button className="btn-animated-pulse">
                                <Zap size={16} />
                                <span>New Query</span>
                            </button>
                        </div>
                    </header>
                )}
                
                <main className={`main-content ${isDDx ? 'no-padding' : ''}`}>
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
