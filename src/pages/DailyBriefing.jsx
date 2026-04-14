import React, { useState } from 'react';
import { Newspaper, ChevronRight, Bookmark, Share2 } from 'lucide-react';
import PremiumLock from '../components/PremiumLock';

// Mock user state
const IS_PREMIUM = false;

const NEWS_ARTICLES = [
    {
        id: 1,
        title: "New Guidelines for Hypertension Management in Elderly Patients",
        source: "JAMA Cardiology",
        date: "2 hours ago",
        summary: "The latest guidelines suggest a target systolic blood pressure of <130 mm Hg for non-frail elderly patients, marking a shift from previous recommendations.",
        category: "Cardiology",
        imageUrl: "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&q=80&w=2070",
        premium: true
    },
    {
        id: 2,
        title: "Breakthrough in Alzheimer's Monoclonal Antibody Therapy",
        source: "NEJM",
        date: "5 hours ago",
        summary: "Phase 3 clinical trials demonstrate a 27% slowing of cognitive decline with the new antibody treatment.",
        category: "Neurology",
        imageUrl: "https://images.unsplash.com/photo-1559757175-5700dde675bc?auto=format&fit=crop&q=80&w=2070",
        premium: true
    },
    {
        id: 3,
        title: "Dengue Outbreak: CDC Issues New Clinical Protocols",
        source: "CDC Health Alert",
        date: "1 day ago",
        summary: "Updated fluid management protocols for severe dengue cases to prevent fluid overload while maintaining perfusion.",
        category: "Infectious Disease",
        imageUrl: "https://images.unsplash.com/photo-1584036561566-b93a94925034?auto=format&fit=crop&q=80&w=2070",
        premium: false
    }
];

export default function DailyBriefing() {
    const [activeTab, setActiveTab] = useState('All');

    return (
        <div className="flex flex-col gap-lg h-full">
            <div className="flex justify-between items-end mb-2">
                <div>
                    <h2 className="text-h2">Daily Medical Briefing</h2>
                    <p className="text-body text-gray-500">Curated summaries of the latest high-impact research.</p>
                </div>
                <div className="flex gap-2 text-sm font-medium">
                    {['All', 'Cardiology', 'Neurology', 'Infectious Disease'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-3 py-1 rounded-full transition-colors ${activeTab === tab ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {!IS_PREMIUM ? (
                <PremiumLock featureName="Daily Medical Briefing" />
            ) : (
                <div className="grid grid-cols-1 gap-md">
                    {NEWS_ARTICLES.filter(a => activeTab === 'All' || a.category === activeTab).map((article) => (
                        <div key={article.id} className="card flex flex-col md:flex-row gap-lg group cursor-pointer hover:shadow-md transition-shadow">
                            {/* Image Placeholder - simplified for code env */}
                            <div
                                className="w-full md:w-48 h-32 rounded-md bg-gray-200 flex-shrink-0 bg-cover bg-center"
                                style={{ backgroundImage: `url(${article.imageUrl})` }}
                            />

                            <div className="flex-1 flex flex-col justify-between py-1">
                                <div>
                                    <div className="flex justify-between items-start">
                                        <span className="text-xs font-bold text-blue-600 uppercase tracking-wide mb-1 block">{article.category}</span>
                                        {article.premium && <span className="badge badge-premium">Premium</span>}
                                    </div>
                                    <h3 className="text-h3 leading-tight group-hover:text-blue-700 transition-colors mb-2">{article.title}</h3>
                                    <p className="text-body text-gray-600 line-clamp-2">{article.summary}</p>
                                </div>

                                <div className="flex justify-between items-center mt-3">
                                    <div className="text-small flex items-center gap-2">
                                        <Newspaper size={14} /> {article.source} • {article.date}
                                    </div>
                                    <div className="flex gap-2">
                                        <button className="p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-blue-600 transition-colors">
                                            <Bookmark size={18} />
                                        </button>
                                        <button className="p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-blue-600 transition-colors">
                                            <Share2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
