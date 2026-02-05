import React, { useState } from 'react';
import type { TorrentResult } from '../types';
import {
  CategoryIcon, SeedersIcon, PeersIcon, SizeIcon, ClipboardCopyIcon,
  ExternalLinkIcon, CloseIcon, SortAscIcon, SortDescIcon, SortIcon
} from './Icons';

interface ResultsTableProps {
  results: TorrentResult[];
  isLoading: boolean;
  hasSearched: boolean;
  needsConfiguration: boolean;
  sortConfig: { key: keyof TorrentResult; direction: 'ascending' | 'descending' };
  requestSort: (key: keyof TorrentResult) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  totalResults: number;
  onAddToCloud?: (magnet: string, title: string) => void;
}

const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const SeederPeers: React.FC<{ value: number, type: 'seeders' | 'peers' }> = ({ value, type }) => {
  const colorClass = type === 'seeders'
    ? value > 50 ? 'text-green-400' : value > 10 ? 'text-yellow-400' : 'text-red-400'
    : 'text-sky-400';
  const Icon = type === 'seeders' ? SeedersIcon : PeersIcon;

  return (
    <div className={`flex items-center justify-center text-center gap-1.5 font-mono ${colorClass}`}>
      <Icon />
      <span>{value}</span>
    </div>
  );
};

const SkeletonRow: React.FC = () => (
  <tr className="border-b border-slate-700/50 animate-pulse">
    <td className="px-6 py-4"><div className="h-4 bg-slate-700/50 rounded w-24"></div></td>
    <td className="px-6 py-4">
      <div className="h-4 bg-slate-700/50 rounded w-3/4"></div>
      <div className="h-3 bg-slate-700/50 rounded w-1/4 mt-2"></div>
    </td>
    <td className="px-6 py-4"><div className="h-4 bg-slate-700/50 rounded w-16"></div></td>
    <td className="px-6 py-4"><div className="h-4 bg-slate-700/50 rounded w-12"></div></td>
    <td className="px-6 py-4"><div className="h-4 bg-slate-700/50 rounded w-12"></div></td>
    <td className="px-6 py-4"><div className="h-4 bg-slate-700/50 rounded w-20"></div></td>
    <td className="px-6 py-4">
      <div className="flex gap-2 justify-end">
        <div className="h-8 w-8 bg-slate-700/50 rounded-lg"></div>
        <div className="h-8 w-8 bg-slate-700/50 rounded-lg"></div>
      </div>
    </td>
  </tr>
)

const SkeletonCard: React.FC = () => (
  <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl shadow-lg p-4 animate-pulse">
    <div className="h-5 bg-slate-700/50 rounded w-3/4 mb-2"></div>
    <div className="h-3 bg-slate-700/50 rounded w-1/3 mb-3"></div>
    <div className="flex justify-between border-y border-slate-700/50 py-3 mb-3">
      <div className="h-4 bg-slate-700/50 rounded w-1/4"></div>
      <div className="h-4 bg-slate-700/50 rounded w-1/4"></div>
    </div>
    <div className="flex justify-around mb-4">
      <div className="h-4 bg-slate-700/50 rounded w-1/5"></div>
      <div className="h-4 bg-slate-700/50 rounded w-1/5"></div>
      <div className="h-4 bg-slate-700/50 rounded w-1/5"></div>
    </div>
    <div className="flex gap-2">
      <div className="h-10 bg-slate-700/50 rounded-lg w-full"></div>
      <div className="h-10 bg-slate-700/50 rounded-lg w-12"></div>
    </div>
  </div>
);


const ResultsTable: React.FC<ResultsTableProps> = ({
  results, isLoading, hasSearched, needsConfiguration,
  sortConfig, requestSort, currentPage, totalPages, onPageChange, totalResults,
  onAddToCloud
}) => {
  const [activeCopyMagnetId, setActiveCopyMagnetId] = useState<number | null>(null);

  // Filter out any invalid results before rendering (safety check)
  const currentResults = results.filter(r => r && r.Id);

  const sortOptions: { key: keyof TorrentResult; label: string }[] = [
    { key: 'Seeders', label: 'Seeders' },
    { key: 'Peers', label: 'Peers' },
    { key: 'Size', label: 'Size' },
    { key: 'PublishDate', label: 'Date' },
    { key: 'Title', label: 'Title' },
    { key: 'CategoryDesc', label: 'Category' },
  ];

  const handleCopyMagnet = (magnetUri: string | null, id: number) => {
    if (!magnetUri) {
      console.error('Magnet link is not available.');
      return;
    }

    setActiveCopyMagnetId(id);

    const fallbackCopy = (text: string) => {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.top = "0";
      textArea.style.left = "0";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } catch (err) {
        console.error('Fallback copy exception:', err);
      }
      document.body.removeChild(textArea);
    };

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(magnetUri).catch(err => {
        console.error('Failed to copy magnet link with Clipboard API, falling back.', err);
        fallbackCopy(magnetUri);
      });
    } else {
      fallbackCopy(magnetUri);
    }

    // Auto-reset the "Copied!" state after 1.5 seconds
    setTimeout(() => setActiveCopyMagnetId(null), 1500);
  };

  const SortableHeaderCell: React.FC<{
    sortKey: keyof TorrentResult;
    className?: string;
    children: React.ReactNode;
  }> = ({ sortKey, children, className }) => (
    <th scope="col" className={`px-6 py-4 whitespace-nowrap tracking-wider ${className || ''}`}>
      <button
        type="button"
        onClick={() => requestSort(sortKey)}
        className="flex items-center gap-1.5 group text-slate-400 uppercase hover:text-sky-400 transition-colors"
      >
        {children}
        <span className={sortConfig?.key === sortKey ? 'text-sky-400' : 'opacity-0 group-hover:opacity-100 transition-opacity'}>
          {sortConfig?.key === sortKey
            ? (sortConfig.direction === 'ascending' ? <SortAscIcon /> : <SortDescIcon />)
            : <SortIcon />
          }
        </span>
      </button>
    </th>
  );

  if (isLoading) {
    return (
      <>
        {/* Desktop Skeleton */}
        <div className="hidden md:block bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-x-auto backdrop-blur-sm">
          <table className="w-full text-left">
            <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
              <tr>
                <th scope="col" className="px-6 py-4">Category</th>
                <th scope="col" className="px-6 py-4">Title</th>
                <th scope="col" className="px-6 py-4">Size</th>
                <th scope="col" className="px-6 py-4">Seeders</th>
                <th scope="col" className="px-6 py-4">Peers</th>
                <th scope="col" className="px-6 py-4">Date</th>
                <th scope="col" className="px-6 py-4">Links</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {[...Array(10)].map((_, i) => <SkeletonRow key={i} />)}
            </tbody>
          </table>
        </div>
        {/* Mobile Skeleton */}
        <div className="block md:hidden space-y-4">
          {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </>
    );
  }

  if (!hasSearched) {
    if (needsConfiguration) {
      return (
        <div className="text-center py-16 px-6 bg-slate-800/30 backdrop-blur-sm border border-dashed border-slate-700/50 rounded-xl">
          <h3 className="text-xl font-semibold text-slate-300">Configuration Required</h3>
          <p className="text-slate-500 mt-2">The Jackett server URL and API Key must be configured for the app to function.</p>
          <p className="text-slate-500 mt-1">Please provide them via environment variables.</p>
        </div>
      );
    }
    return (
      <div className="text-center py-16 px-6 bg-slate-800/30 backdrop-blur-sm border border-dashed border-slate-700/50 rounded-xl">
        <h3 className="text-xl font-semibold text-slate-300">Ready to search?</h3>
        <p className="text-slate-500 mt-2">Enter a query above to find torrents.</p>
      </div>
    )
  }

  if (results.length === 0 && totalResults === 0) {
    return (
      <div className="text-center py-16 px-6 bg-slate-800/30 backdrop-blur-sm border border-dashed border-slate-700/50 rounded-xl">
        <h3 className="text-xl font-semibold text-slate-300">No Results Found</h3>
        <p className="text-slate-500 mt-2">Your search did not match any torrents. Try a different query.</p>
      </div>
    );
  }

  return (
    <>
      {/* Mobile Sort Controls */}
      {totalResults > 0 && (
        <div className="md:hidden flex items-center justify-between mb-4 px-1">
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm text-slate-400 font-medium">Sort by:</label>
            <div className="relative">
              <select
                id="sort-select"
                value={sortConfig.key}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => requestSort(e.target.value as keyof TorrentResult)}
                className="pl-3 pr-8 py-2 text-sm bg-slate-800/80 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500 appearance-none shadow-sm"
                aria-label="Sort by property"
              >
                {sortOptions.map(opt => (
                  <option key={opt.key} value={opt.key}>{opt.label}</option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                <SortIcon className="w-4 h-4" />
              </div>
            </div>
          </div>
          <button
            onClick={() => requestSort(sortConfig.key)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-800/80 text-slate-200 rounded-lg border border-slate-700 hover:bg-slate-700 shadow-sm transition-colors"
            aria-label={`Current sort direction is ${sortConfig.direction}. Click to toggle.`}
          >
            {sortConfig.direction === 'ascending' ? <SortAscIcon /> : <SortDescIcon />}
          </button>
        </div>
      )}

      {/* Desktop/Tablet Table View */}
      <div className="hidden md:block overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/40 backdrop-blur-sm shadow-xl">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-900/50 text-xs uppercase text-slate-400 font-medium">
            <tr>
              <SortableHeaderCell sortKey="CategoryDesc">Category</SortableHeaderCell>
              <SortableHeaderCell sortKey="Title">Title</SortableHeaderCell>
              <SortableHeaderCell sortKey="Size"><div className="flex items-center gap-1"><SizeIcon /> Size</div></SortableHeaderCell>
              <SortableHeaderCell sortKey="Seeders">Seeders</SortableHeaderCell>
              <SortableHeaderCell sortKey="Peers">Peers</SortableHeaderCell>
              <SortableHeaderCell sortKey="PublishDate">Date</SortableHeaderCell>
              <th scope="col" className="px-6 py-4 tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {currentResults.map((result) => (
              <tr key={result.Id} className="hover:bg-slate-700/30 transition-colors duration-150 group">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2 text-slate-400 group-hover:text-slate-300 transition-colors">
                    <CategoryIcon />
                    {result.CategoryDesc}
                  </div>
                </td>
                <td className="px-6 py-4 max-w-md">
                  <div className="flex flex-col gap-1">
                    <span className="font-medium text-slate-200 leading-snug group-hover:text-sky-300 transition-colors" title={result.Title}>{result.Title}</span>
                    <span className="text-xs text-slate-500">{result.Indexer?.toLowerCase().includes('bitmagnet') ? 'TorrentWave' : result.Indexer}</span>
                  </div>
                </td>
                <td className="px-6 py-4 font-mono text-slate-400 whitespace-nowrap">{formatBytes(result.Size)}</td>
                <td className="px-6 py-4 text-center">
                  <SeederPeers value={result.Seeders} type="seeders" />
                </td>
                <td className="px-6 py-4 text-center">
                  <SeederPeers value={result.Peers} type="peers" />
                </td>
                <td className="px-6 py-4 text-center font-mono text-xs text-slate-500 whitespace-nowrap">
                  {new Date(result.PublishDate).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                    {/* Copy Magnet Button */}
                    <div className="relative">
                      <button
                        onClick={() => handleCopyMagnet(result.MagnetUri, result.Id)}
                        disabled={!result.MagnetUri}
                        title={activeCopyMagnetId === result.Id ? 'Copied!' : 'Copy Magnet Link'}
                        className={`p-2 rounded-lg transition-all disabled:opacity-30 disabled:hover:bg-transparent disabled:cursor-not-allowed ${activeCopyMagnetId === result.Id ? 'text-green-400 bg-green-400/10' : 'text-slate-400 hover:text-sky-400 hover:bg-sky-400/10'}`}
                      >
                        {activeCopyMagnetId === result.Id ? (
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                        ) : (
                          <ClipboardCopyIcon />
                        )}
                      </button>
                    </div>

                    {!result.Indexer?.toLowerCase().includes('bitmagnet') && (
                      <a
                        href={result.Details}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 text-slate-400 hover:text-sky-400 hover:bg-sky-400/10 rounded-lg transition-all"
                        title="View on Tracker"
                      >
                        <ExternalLinkIcon />
                      </a>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden flex flex-col gap-4">
        {currentResults.map((result) => (
          <div key={result.Id} className="bg-slate-800/40 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4 shadow-lg active:scale-[0.99] transition-transform">
            <div className="mb-3">
              <h3 className="font-semibold text-slate-100 leading-snug mb-1 break-words">{result.Title}</h3>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="bg-slate-900/50 px-2 py-0.5 rounded border border-slate-700/50">{result.Indexer?.toLowerCase().includes('bitmagnet') ? 'TorrentWave' : result.Indexer}</span>
                <span className="truncate max-w-[120px]">{result.CategoryDesc}</span>
                <span className="ml-auto font-mono">{new Date(result.PublishDate).toLocaleDateString()}</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4 bg-slate-900/30 rounded-lg p-2 border border-slate-700/30">
              <div className="flex flex-col items-center">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Size</span>
                <span className="font-mono text-sm text-slate-300">{formatBytes(result.Size)}</span>
              </div>
              <div className="flex flex-col items-center border-l border-r border-slate-700/30">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Seeds</span>
                <SeederPeers value={result.Seeders} type="seeders" />
              </div>
              <div className="flex flex-col items-center">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Peers</span>
                <SeederPeers value={result.Peers} type="peers" />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => handleCopyMagnet(result.MagnetUri, result.Id)}
                disabled={!result.MagnetUri}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold shadow-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${activeCopyMagnetId === result.Id ? 'bg-green-600 hover:bg-green-500 text-white shadow-green-900/20' : 'bg-sky-600 hover:bg-sky-500 active:bg-sky-700 text-white shadow-sky-900/20'}`}
              >
                {activeCopyMagnetId === result.Id ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                ) : (
                  <ClipboardCopyIcon />
                )}
                {activeCopyMagnetId === result.Id ? 'Copied!' : 'Copy Magnet'}
              </button>
              {!result.Indexer?.toLowerCase().includes('bitmagnet') && (
                <a
                  href={result.Details}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-slate-700 hover:bg-slate-600 text-slate-300 py-2.5 px-4 rounded-lg flex items-center justify-center transition-colors border border-slate-600"
                  aria-label="View on Tracker"
                >
                  <ExternalLinkIcon />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <nav className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-8 px-2" aria-label="Pagination">
          <div className="text-sm text-slate-400 text-center sm:text-left">
            Showing <span className="font-semibold text-slate-200">{(currentPage - 1) * 50 + 1}</span> to <span className="font-semibold text-slate-200">{Math.min(currentPage * 50, totalResults)}</span> of <span className="font-semibold text-slate-200">{totalResults}</span>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/40 p-1 rounded-lg border border-slate-700/50 backdrop-blur-sm">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-4 py-2 text-sm font-medium rounded-md text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
            >
              Previous
            </button>
            <span className="px-3 py-1 bg-slate-700/50 rounded text-sm text-sky-400 font-bold min-w-[3rem] text-center border border-slate-600/50">
              {currentPage}
            </span>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-4 py-2 text-sm font-medium rounded-md text-slate-300 hover:bg-slate-700 hover:text-white disabled:opacity-40 disabled:hover:bg-transparent transition-colors"
            >
              Next
            </button>
          </div>
        </nav>
      )}
    </>
  );
};

export default ResultsTable;