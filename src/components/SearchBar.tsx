
import React from 'react';
import { SearchIcon, SpinnerIcon } from './Icons';

interface SearchBarProps {
  query: string;
  setQuery: (query: string) => void;
  onSearch: () => void;
  isLoading: boolean;
  disabled: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({ query, setQuery, onSearch, isLoading, disabled }) => {
  
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "Please configure settings first" : "Search for movies, series, games..."}
        className="w-full pl-5 pr-32 py-4 bg-slate-800 border border-slate-700 rounded-full text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all duration-300 disabled:bg-slate-800/50 disabled:cursor-not-allowed"
        disabled={isLoading || disabled}
      />
      <button
        onClick={onSearch}
        disabled={isLoading || disabled}
        className="absolute right-2 top-1/2 -translate-y-1/2 h-12 px-6 flex items-center justify-center bg-sky-600 text-white rounded-full font-semibold hover:bg-sky-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800 focus:ring-sky-500 disabled:bg-slate-600 disabled:cursor-not-allowed transition-all duration-300"
      >
        {isLoading ? (
          <>
            <SpinnerIcon />
            Searching...
          </>
        ) : (
          <>
           <SearchIcon />
           Search
          </>
        )}
      </button>
    </div>
  );
};

export default SearchBar;
