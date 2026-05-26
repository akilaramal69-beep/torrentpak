import React, { useState } from 'react';
import type { Category } from '../types';
import { ChevronDownIcon, ChevronUpIcon } from './Icons';

interface CategoryFilterProps {
  categories: Category[];
  selectedCategory: string;
  onCategoryChange: (categoryId: string) => void;
  disabled: boolean;
}

const CategoryFilter: React.FC<CategoryFilterProps> = ({ categories, selectedCategory, onCategoryChange, disabled }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const VISIBLE_COUNT = 6;

  const visibleCategories = isExpanded ? categories : categories.slice(0, VISIBLE_COUNT);
  const hasMore = categories.length > VISIBLE_COUNT;

  return (
    <div className="w-full">
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent">
        <button
          onClick={() => onCategoryChange('')}
          disabled={disabled}
          className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
            selectedCategory === ''
              ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/30'
              : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          All
        </button>
        {visibleCategories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => onCategoryChange(cat.id)}
            disabled={disabled}
            className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
              selectedCategory === cat.id
                ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/30'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {cat.name}
          </button>
        ))}
        {hasMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            disabled={disabled}
            className="flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap bg-slate-700 text-slate-300 hover:bg-slate-600 border border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                Show Less
                <ChevronUpIcon />
              </>
            ) : (
              <>
                Show More
                <ChevronDownIcon />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default CategoryFilter;
