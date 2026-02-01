import React, { useState, useEffect, lazy, Suspense } from 'react';
import SearchBar from './components/SearchBar';
import CategoryFilter from './components/CategoryFilter';
import ResultsTable from './components/ResultsTable';
import ProgressBar from './components/ProgressBar';
import { LogoIcon } from './components/Icons';

const CloudDashboard = lazy(() => import('./components/CloudDashboard').then(m => ({ default: m.CloudDashboard })));

import type { Category } from './types';

function App() {
    const [query, setQuery] = useState('');
    const [categories, setCategories] = useState<Category[]>([]);
    const [selectedCategory, setSelectedCategory] = useState('');
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [hasSearched, setHasSearched] = useState(false);
    const [error, setError] = useState('');
    const [sortConfig, setSortConfig] = useState<{ key: any, direction: 'ascending' | 'descending' | null }>({ key: null, direction: 'ascending' });
    const [currentPage, setCurrentPage] = useState(1);
    const [isCloudOpen, setIsCloudOpen] = useState(false);

    useEffect(() => {
        fetchCategories();
    }, []);

    // Quirky loading messages for fun
    const loadingMessages = [
        "🏴‍☠️ Hoisting the sails...",
        "🔭 Scanning the horizon...",
        "🌊 Riding the waves...",
        "🦜 Asking the parrot...",
        "🗺️ Checking the treasure map...",
        "⚓ Dropping anchor on results...",
        "🏝️ Searching distant islands...",
        "🧭 Calibrating the compass...",
        "🦑 Waking up the kraken...",
        "🚢 Full speed ahead...",
    ];
    const [loadingMessage, setLoadingMessage] = useState(loadingMessages[0]);

    const fetchCategories = async () => {
        // Fast static categories - no slow API calls
        setCategories([
            { id: '2000', name: '🎬 Movies' },
            { id: '2040', name: '🎬 Movies HD' },
            { id: '2045', name: '🎥 Movies 4K' },
            { id: '5000', name: '📺 TV Shows' },
            { id: '5040', name: '📺 TV HD' },
            { id: '5045', name: '📺 TV 4K' },
            { id: '5070', name: '🎌 Anime' },
            { id: '3000', name: '🎵 Music' },
            { id: '3030', name: '🎧 Audiobooks' },
            { id: '4000', name: '🎮 PC Games' },
            { id: '1000', name: '🕹️ Console' },
            { id: '6000', name: '💻 Software' },
            { id: '7000', name: '📚 Books' },
            { id: '7030', name: '📖 Comics' },
            { id: '8000', name: '📦 Other' },
        ]);
    };

    const handleSearch = async (forcedQuery?: string) => {
        const searchTerms = forcedQuery || query;
        if (!searchTerms.trim()) return;

        setIsLoading(true);
        setError('');
        setCurrentPage(1);

        // Start rotating through fun messages
        setLoadingMessage(loadingMessages[Math.floor(Math.random() * loadingMessages.length)]);
        const messageInterval = setInterval(() => {
            setLoadingMessage(loadingMessages[Math.floor(Math.random() * loadingMessages.length)]);
        }, 1500);

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerms)}&category=${selectedCategory}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Search failed (Status ${response.status})`);
            }
            const data = await response.json();
            const rawResults = data.Results || [];

            // Sort by seeders (highest first) by default
            const sortedResults = [...rawResults].sort((a: any, b: any) => (b.Seeders || 0) - (a.Seeders || 0));

            setResults(sortedResults as any);
            setHasSearched(true);
        } catch (err: any) {
            setError(err.message || 'Something went wrong');
            console.error('Search error:', err);
        } finally {
            clearInterval(messageInterval);
            setIsLoading(false);
        }
    };

    const requestSort = (key: any) => {
        let direction: 'ascending' | 'descending' = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });

        const sorted = [...results].sort((a: any, b: any) => {
            if (a[key] < b[key]) return direction === 'ascending' ? -1 : 1;
            if (a[key] > b[key]) return direction === 'ascending' ? 1 : -1;
            return 0;
        });
        setResults(sorted as any);
    };

    const handleAddToCloud = async (magnet: string, title: string) => {
        // Cloud functionality disabled for now
        console.log('Cloud download requested for:', title);
    };

    return (
        <>
            <ProgressBar isLoading={isLoading} />

            <Suspense fallback={null}>
                {isCloudOpen && <CloudDashboard isOpen={isCloudOpen} onClose={() => setIsCloudOpen(false)} />}
            </Suspense>

            <div className="min-h-screen bg-slate-900 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-800 via-slate-900 to-black text-slate-200 font-sans selection:bg-sky-500/30">
                <div className="container mx-auto px-4 py-8 md:py-12">
                    <header className="flex flex-col items-center justify-center text-center mb-12 relative z-10">
                        <div className="absolute top-4 right-4">
                            {/* Cloud Drive button removed */}
                        </div>

                        <div className="relative w-full max-w-4xl flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-800/30 backdrop-blur-md border border-slate-700/50 shadow-xl">
                            <div className="flex items-center gap-4 mb-2">
                                <LogoIcon />
                                <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-cyan-300 to-teal-200 drop-shadow-lg">
                                    TorrentWave
                                </h1>
                            </div>
                            <p className="text-slate-400 text-lg font-light tracking-wide">Sailing high seas to find torrents.</p>
                        </div>
                    </header>

                    <main>
                        <div className="max-w-3xl mx-auto mb-8">
                            <div className="flex flex-col md:flex-row gap-4 items-center">
                                <div className="w-full md:flex-grow">
                                    <SearchBar
                                        query={query}
                                        setQuery={setQuery}
                                        onSearch={handleSearch}
                                        isLoading={isLoading}
                                        disabled={isLoading}
                                    />
                                </div>
                                <div className="w-full md:w-64">
                                    <CategoryFilter
                                        categories={categories}
                                        selectedCategory={selectedCategory}
                                        onCategoryChange={setSelectedCategory}
                                        disabled={isLoading}
                                    />
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="max-w-3xl mx-auto text-center p-4 bg-red-900/50 border border-red-700 rounded-lg mb-8">
                                <p className="text-red-400">{error}</p>
                            </div>
                        )}

                        {isLoading && (
                            <div className="max-w-3xl mx-auto text-center p-6 mb-8">
                                <p className="text-xl text-cyan-400 font-medium animate-pulse">{loadingMessage}</p>
                            </div>
                        )}

                        <ResultsTable
                            results={results.slice((currentPage - 1) * 50, currentPage * 50)}
                            isLoading={isLoading}
                            hasSearched={hasSearched}
                            needsConfiguration={false}
                            sortConfig={sortConfig as any}
                            requestSort={requestSort}
                            currentPage={currentPage}
                            totalPages={Math.ceil(results.length / 50)}
                            onPageChange={setCurrentPage}
                            totalResults={results.length}
                            onAddToCloud={handleAddToCloud}
                        />
                    </main>
                </div>
            </div>
        </>
    );
}

export default App;
