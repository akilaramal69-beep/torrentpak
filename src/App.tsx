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

    const fetchCategories = async () => {
        try {
            const response = await fetch('/api/search?q=test'); // Just to get a response or handle categories differently
            // In a real app, Jackett has a capabilities endpoint. For now, we'll use a static list or fetch from API if available.
            setCategories([
                { id: '2000', name: 'Movies' },
                { id: '2040', name: 'Movies (HD)' },
                { id: '5000', name: 'TV Shows' },
                { id: '5070', name: 'TV (HD)' },
                { id: '3000', name: 'Music' },
                { id: '4000', name: 'PC Games' },
                { id: '6000', name: 'Software' },
                { id: '7000', name: 'Books' }
            ]);
        } catch (e) {
            console.error("Failed to fetch categories");
        }
    };

    const handleSearch = async (forcedQuery?: string) => {
        const searchTerms = forcedQuery || query;
        if (!searchTerms.trim()) return;

        setIsLoading(true);
        setError('');
        setCurrentPage(1);

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

            <div className="min-h-screen bg-slate-900 text-slate-200 font-sans">
                <div className="container mx-auto px-4 py-8">
                    <header className="flex flex-col items-center justify-center text-center mb-8">
                        <div className="absolute top-4 right-4">
                            {/* Cloud Drive button removed */}
                        </div>

                        <div className="relative w-full max-w-3xl flex items-center justify-center">
                            <div className="flex items-center gap-4">
                                <LogoIcon />
                                <h1 className="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-cyan-300">
                                    TorrentWave
                                </h1>
                            </div>
                        </div>
                        <p className="text-slate-400 mt-2">The fastest way to find your favorite torrents.</p>
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

                        <ResultsTable
                            results={results}
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
