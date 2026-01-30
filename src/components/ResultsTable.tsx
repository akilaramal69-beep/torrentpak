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
  <tr className="border-b border-slate-800 animate-pulse">
    <td className="px-4 py-4"><div className="h-4 bg-slate-700 rounded w-24"></div></td>
    <td className="px-4 py-4">
      <div className="h-4 bg-slate-700 rounded w-3/4"></div>
      <div className="h-3 bg-slate-700 rounded w-1/4 mt-2"></div>
    </td>
    <td className="px-4 py-4"><div className="h-4 bg-slate-700 rounded w-16"></div></td>
    <td className="px-4 py-4"><div className="h-4 bg-slate-700 rounded w-12"></div></td>
    <td className="px-4 py-4"><div className="h-4 bg-slate-700 rounded w-12"></div></td>
    <td className="px-4 py-4"><div className="h-4 bg-slate-700 rounded w-20"></div></td>
    <td className="px-4 py-4">
      <div className="flex gap-2">
        <div className="h-8 w-8 bg-slate-700 rounded-full"></div>
        <div className="h-8 w-8 bg-slate-700 rounded-full"></div>
      </div>
    </td>
  </tr>
)

const SkeletonCard: React.FC = () => (
  <div className="bg-slate-800 border border-slate-700 rounded-lg shadow-lg p-4 animate-pulse">
    <div className="h-5 bg-slate-700 rounded w-3/4 mb-2"></div>
    <div className="h-3 bg-slate-700 rounded w-1/3 mb-3"></div>
    <div className="flex justify-between border-y border-slate-700 py-3 mb-3">
      <div className="h-4 bg-slate-700 rounded w-1/4"></div>
      <div className="h-4 bg-slate-700 rounded w-1/4"></div>
    </div>
    <div className="flex justify-around mb-4">
      <div className="h-4 bg-slate-700 rounded w-1/5"></div>
      <div className="h-4 bg-slate-700 rounded w-1/5"></div>
      <div className="h-4 bg-slate-700 rounded w-1/5"></div>
    </div>
    <div className="flex gap-2">
      <div className="h-10 bg-slate-700 rounded-md w-full"></div>
      <div className="h-10 bg-slate-700 rounded-md w-12"></div>
    </div>
  </div>
);


const ResultsTable: React.FC<ResultsTableProps> = ({
  results, isLoading, hasSearched, needsConfiguration,
  sortConfig, requestSort, currentPage, totalPages, onPageChange, totalResults,
  onAddToCloud
}) => {
  const [activeCopyMagnetId, setActiveCopyMagnetId] = useState<number | null>(null);

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
  };

  const SortableHeaderCell: React.FC<{
    sortKey: keyof TorrentResult;
    className?: string;
    children: React.ReactNode;
  }> = ({ sortKey, children, className }) => (
    <th scope="col" className={`px-4 py-3 whitespace-nowrap ${className || ''}`}>
      <button
        type="button"
        onClick={() => requestSort(sortKey)}
        className="flex items-center gap-1.5 group text-slate-400 uppercase"
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
        <div className="hidden md:block bg-slate-800/50 border border-slate-700 rounded-lg overflow-x-auto">
          <table className="w-full text-left">
            <thead className="text-xs text-slate-400 uppercase bg-slate-800">
              <tr>
                <th scope="col" className="px-4 py-3">Category</th>
                <th scope="col" className="px-4 py-3">Title</th>
                <th scope="col" className="px-4 py-3">Size</th>
                <th scope="col" className="px-4 py-3">Seeders</th>
                <th scope="col" className="px-4 py-3">Peers</th>
                <th scope="col" className="px-4 py-3">Date</th>
                <th scope="col" className="px-4 py-3">Links</th>
              </tr>
            </thead>
            <tbody>
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
        <div className="text-center py-16 px-6 bg-slate-800/50 border border-dashed border-slate-700 rounded-lg">
          <h3 className="text-xl font-semibold text-slate-300">Configuration Required</h3>
          <p className="text-slate-500 mt-2">The Jackett server URL and API Key must be configured for the app to function.</p>
          <p className="text-slate-500 mt-1">Please provide them via environment variables.</p>
        </div>
      );
    }
    return (
      <div className="text-center py-16 px-6 bg-slate-800/50 border border-dashed border-slate-700 rounded-lg">
        <h3 className="text-xl font-semibold text-slate-300">Ready to search?</h3>
        <p className="text-slate-500 mt-2">Enter a query above to find torrents.</p>
      </div>
    )
  }

  if (results.length === 0 && totalResults === 0) {
    return (
      <div className="text-center py-16 px-6 bg-slate-800/50 border border-dashed border-slate-700 rounded-lg">
        <h3 className="text-xl font-semibold text-slate-300">No Results Found</h3>
        <p className="text-slate-500 mt-2">Your search did not match any torrents. Try a different query.</p>
      </div>
    );
  }

  return (
    <>
      {/* Mobile Sort Controls */}
      {totalResults > 0 && (
        <div className="md:hidden flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm text-slate-400">Sort by:</label>
            <div className="relative">
              <select
                id="sort-select"
                value={sortConfig.key}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => requestSort(e.target.value as keyof TorrentResult)}
                className="pl-3 pr-8 py-2 text-sm bg-slate-700 border border-slate-600 rounded-md text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500 appearance-none"
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
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-slate-700 text-slate-200 rounded-md hover:bg-slate-600"
            aria-label={`Current sort direction is ${sortConfig.direction}. Click to toggle.`}
          >
            {sortConfig.direction === 'ascending' ? <SortAscIcon /> : <SortDescIcon />}
          </button>
        </div>
      )}

      {/* Desktop Table View */}
      <div className="hidden md:block bg-slate-800/50 border border-slate-700 rounded-lg overflow-x-auto shadow-lg">
        <table className="w-full text-left text-sm">
          <thead className="text-xs bg-slate-800">
            <tr>
              <SortableHeaderCell sortKey="CategoryDesc">Category</SortableHeaderCell>
              <SortableHeaderCell sortKey="Title">Title</SortableHeaderCell>
              <SortableHeaderCell sortKey="Size"><div className="flex items-center gap-1"><SizeIcon /> Size</div></SortableHeaderCell>
              <SortableHeaderCell sortKey="Seeders">Seeders</SortableHeaderCell>
              <SortableHeaderCell sortKey="Peers">Peers</SortableHeaderCell>
              <SortableHeaderCell sortKey="PublishDate">Date</SortableHeaderCell>
              <th scope="col" className="px-4 py-3 uppercase text-slate-400">Links</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.Id} className="border-b border-slate-800 hover:bg-slate-800/60 transition-colors duration-200">
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2 text-slate-400">
                    <CategoryIcon />
                    {result.CategoryDesc}
                  </div>
                </td>
                <td className="px-4 py-4 max-w-sm xl:max-w-md">
                  <p className="font-semibold text-slate-200 break-words" title={result.Title}>{result.Title}</p>
                  <p className="text-xs text-slate-500">{result.Tracker}</p>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-slate-300 font-mono">{formatBytes(result.Size)}</td>
                <td className="px-4 py-4 whitespace-nowrap"><SeederPeers value={result.Seeders} type="seeders" /></td>
                <td className="px-4 py-4 whitespace-nowrap"><SeederPeers value={result.Peers} type="peers" /></td>
                <td className="px-4 py-4 whitespace-nowrap text-slate-400 font-mono">
                  {new Date(result.PublishDate).toLocaleDateString()}
                </td>
                <td className="px-4 py-4">
                  {activeCopyMagnetId === result.Id ? (
                    <div className="flex items-center gap-1 w-full">
                      <input
                        type="text"
                        readOnly
                        value={result.MagnetUri || ''}
                        className="w-full min-w-0 flex-1 text-xs bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-slate-300 font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
                        ref={(input: HTMLInputElement | null) => input?.select()}
                        onBlur={() => setActiveCopyMagnetId(null)}
                        aria-label="Magnet link"
                      />
                      <button
                        onClick={() => setActiveCopyMagnetId(null)}
                        title="Close"
                        className="p-2 text-slate-400 rounded-full hover:text-sky-400 hover:bg-slate-700"
                        aria-label="Close copy input"
                      >
                        <CloseIcon />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopyMagnet(result.MagnetUri, result.Id)}
                        title={result.MagnetUri ? "Copy Magnet Link" : "Magnet link not available"}
                        disabled={!result.MagnetUri}
                        className="p-2 text-slate-400 rounded-full transition-all duration-200 enabled:hover:text-sky-400 enabled:hover:bg-slate-700 disabled:text-slate-600 disabled:cursor-not-allowed"
                        aria-label="Copy magnet link"
                      >
                        <ClipboardCopyIcon />
                      </button>
                      <a href={result.Details} target="_blank" rel="noopener noreferrer" title="View on Tracker" className="p-2 text-slate-400 hover:text-sky-400 hover:bg-slate-700 rounded-full transition-all duration-200" aria-label="View on Tracker">
                        <ExternalLinkIcon />
                      </a>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Card View */}
      <div className="block md:hidden space-y-4">
        {results.map((result) => (
          <div key={result.Id} className="bg-slate-800 border border-slate-700 rounded-lg shadow-lg p-4 flex flex-col gap-3">
            <div>
              <p className="font-semibold text-slate-200 break-words">{result.Title}</p>
              <p className="text-xs text-slate-500 mt-1">{result.Tracker}</p>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 border-y border-slate-700 py-3">
              <div className="flex items-center gap-2 truncate shrink">
                <CategoryIcon />
                <span className="truncate">{result.CategoryDesc}</span>
              </div>
              <span className="font-mono whitespace-nowrap pl-2">{new Date(result.PublishDate).toLocaleDateString()}</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="flex flex-col items-center justify-center gap-1 text-slate-300">
                <div className="flex items-center gap-1.5"><SizeIcon /> <span className="text-xs text-slate-400">Size</span></div>
                <div className="font-mono text-sm">{formatBytes(result.Size)}</div>
              </div>
              <div className="flex flex-col items-center justify-center gap-1">
                <span className="text-xs text-slate-400">Seeders</span>
                <SeederPeers value={result.Seeders} type="seeders" />
              </div>
              <div className="flex flex-col items-center justify-center gap-1">
                <span className="text-xs text-slate-400">Peers</span>
                <SeederPeers value={result.Peers} type="peers" />
              </div>
            </div>

            <div className="mt-1">
              {activeCopyMagnetId === result.Id ? (
                <div className="flex items-center gap-1 w-full">
                  <input
                    type="text"
                    readOnly
                    value={result.MagnetUri || ''}
                    className="w-full min-w-0 flex-1 text-xs bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-slate-300 font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
                    ref={(input: HTMLInputElement | null) => input?.select()}
                    onBlur={() => setActiveCopyMagnetId(null)}
                    aria-label="Magnet link"
                  />
                  <button onClick={() => setActiveCopyMagnetId(null)} title="Close" className="p-2 text-slate-400 rounded-full hover:text-sky-400 hover:bg-slate-700" aria-label="Close copy input" >
                    <CloseIcon />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button onClick={() => handleCopyMagnet(result.MagnetUri, result.Id)} title={result.MagnetUri ? "Copy Magnet Link" : "Magnet link not available"} disabled={!result.MagnetUri} className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm bg-sky-600 text-white rounded-md font-semibold hover:bg-sky-500 disabled:bg-slate-600 disabled:cursor-not-allowed transition-colors" aria-label="Copy magnet link" >
                    <ClipboardCopyIcon />
                    <span>Copy</span>
                  </button>
                  {/* Cloud button removed */}
                  <a href={result.Details} target="_blank" rel="noopener noreferrer" title="View on Tracker" className="p-2.5 text-slate-400 bg-slate-700 hover:text-sky-400 hover:bg-slate-600 rounded-md transition-all duration-200" aria-label="View on Tracker" >
                    <ExternalLinkIcon />
                  </a>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <nav className="flex flex-col md:flex-row items-center justify-between gap-4 mt-6 text-sm text-slate-400" aria-label="Pagination">
          <div className="text-center md:text-left">
            Showing <span className="font-semibold text-slate-200">{(currentPage - 1) * 50 + 1}</span> to <span className="font-semibold text-slate-200">{Math.min(currentPage * 50, totalResults)}</span> of <span className="font-semibold text-slate-200">{totalResults}</span> results
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-4 py-2 bg-slate-700 rounded-md hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="px-2">
              Page <span className="font-semibold text-slate-200">{currentPage}</span> of <span className="font-semibold text-slate-200">{totalPages}</span>
            </span>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-4 py-2 bg-slate-700 rounded-md hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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