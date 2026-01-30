import React from 'react';
import type { Category } from '../types';
import { ChevronDownIcon } from './Icons';

interface CategoryFilterProps {
  categories: Category[];
  selectedCategory: string;
  onCategoryChange: (categoryId: string) => void;
  disabled: boolean;
}

const CategoryFilter: React.FC<CategoryFilterProps> = ({ categories, selectedCategory, onCategoryChange, disabled }) => {
  return (
    <div className="relative w-full">
      <select
        value={selectedCategory}
        onChange={(e) => onCategoryChange(e.target.value)}
        disabled={disabled || categories.length === 0}
        className="w-full h-full px-5 py-4 bg-slate-800 border border-slate-700 rounded-full text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all duration-300 appearance-none pr-12 disabled:bg-slate-800/50 disabled:cursor-not-allowed"
        aria-label="Select Category"
      >
        <option value="">All Categories</option>
        {categories.map((cat) => (
          <option key={cat.id} value={cat.id}>
            {cat.name}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-slate-400">
        <ChevronDownIcon />
      </div>
    </div>
  );
};

export default CategoryFilter;
