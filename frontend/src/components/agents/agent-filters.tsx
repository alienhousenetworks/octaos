'use client';

import React from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface AgentFiltersProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedDept: string;
  onSelectDept: (dept: string) => void;
  deptCounts?: Record<string, number>;
}

const DEPARTMENTS = [
  { id: 'all', label: 'All' },
  { id: 'sales', label: 'Sales' },
  { id: 'marketing', label: 'Marketing' },
  { id: 'support', label: 'Support' },
  { id: 'hr', label: 'HR' },
  { id: 'finance', label: 'Finance' },
  { id: 'executive', label: 'Executive' },
  { id: 'custom', label: 'Custom' },
];

export default function AgentFilters({
  searchQuery,
  onSearchChange,
  selectedDept,
  onSelectDept,
  deptCounts = {},
}: AgentFiltersProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      {/* Search Input */}
      <div className="relative flex-1 sm:max-w-md">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search agents by name, role, capability, or tool..."
          className="h-10 rounded-xl border-gray-800 bg-gray-900/60 pl-9 pr-9 text-xs text-white placeholder:text-gray-500 focus-visible:border-gray-700 focus-visible:ring-0"
        />
        {searchQuery && (
          <button
            type="button"
            onClick={() => onSearchChange('')}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
          >
            <X className="size-3.5" />
          </button>
        )}
      </div>

      {/* Department Pills */}
      <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto rounded-xl border border-gray-800/80 bg-gray-950/40 p-1">
        {DEPARTMENTS.map((dept) => {
          const isSelected = selectedDept === dept.id;
          const count = deptCounts[dept.id];
          return (
            <button
              key={dept.id}
              type="button"
              onClick={() => onSelectDept(dept.id)}
              className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                isSelected
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-gray-900 hover:text-foreground'
              }`}
            >
              <span>{dept.label}</span>
              {typeof count === 'number' && (
                <span
                  className={`text-[10px] font-mono px-1 rounded-full ${
                    isSelected ? 'bg-black/20 text-white' : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
