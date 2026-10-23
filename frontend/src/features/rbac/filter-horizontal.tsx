'use client';

import React, { useState, useMemo } from 'react';
import { Search, ChevronRight, ChevronsRight, ChevronLeft, ChevronsLeft } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export interface FilterItem {
  id: string;
  name: string;
  subtitle?: string; // e.g. module/content_type: 'sales', 'hr'
}

interface FilterHorizontalProps {
  title: string; // e.g. "permissions" or "groups"
  availableItems: FilterItem[];
  chosenItemIds: string[];
  onChange: (newChosenIds: string[]) => void;
  helpText?: string;
}

export default function FilterHorizontal({
  title,
  availableItems,
  chosenItemIds,
  onChange,
  helpText,
}: FilterHorizontalProps) {
  const [availableSearch, setAvailableSearch] = useState('');
  const [chosenSearch, setChosenSearch] = useState('');

  const [selectedAvailableIds, setSelectedAvailableIds] = useState<Set<string>>(new Set());
  const [selectedChosenIds, setSelectedChosenIds] = useState<Set<string>>(new Set());

  const chosenSet = useMemo(() => new Set(chosenItemIds), [chosenItemIds]);

  // Items currently available (not in chosen)
  const availablePool = useMemo(() => {
    return availableItems.filter((item) => !chosenSet.has(item.id));
  }, [availableItems, chosenSet]);

  // Items currently chosen
  const chosenPool = useMemo(() => {
    const itemMap = new Map(availableItems.map((item) => [item.id, item]));
    return chosenItemIds
      .map((id) => itemMap.get(id))
      .filter((item): item is FilterItem => item !== undefined);
  }, [availableItems, chosenItemIds]);

  // Filtered lists
  const filteredAvailable = useMemo(() => {
    if (!availableSearch.trim()) return availablePool;
    const q = availableSearch.toLowerCase();
    return availablePool.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q))
    );
  }, [availablePool, availableSearch]);

  const filteredChosen = useMemo(() => {
    if (!chosenSearch.trim()) return chosenPool;
    const q = chosenSearch.toLowerCase();
    return chosenPool.filter(
      (item) =>
        item.name.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q))
    );
  }, [chosenPool, chosenSearch]);

  // Toggle selection in Available box
  const toggleSelectAvailable = (id: string) => {
    setSelectedAvailableIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Toggle selection in Chosen box
  const toggleSelectChosen = (id: string) => {
    setSelectedChosenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Action: Add selected to Chosen
  const handleAddSelected = () => {
    if (selectedAvailableIds.size === 0) return;
    const newChosen = [...chosenItemIds, ...Array.from(selectedAvailableIds)];
    onChange(newChosen);
    setSelectedAvailableIds(new Set());
  };

  // Action: Choose All (filtered)
  const handleChooseAll = () => {
    const idsToAdd = filteredAvailable.map((i) => i.id);
    if (idsToAdd.length === 0) return;
    const newChosen = Array.from(new Set([...chosenItemIds, ...idsToAdd]));
    onChange(newChosen);
    setSelectedAvailableIds(new Set());
  };

  // Action: Remove selected from Chosen
  const handleRemoveSelected = () => {
    if (selectedChosenIds.size === 0) return;
    const newChosen = chosenItemIds.filter((id) => !selectedChosenIds.has(id));
    onChange(newChosen);
    setSelectedChosenIds(new Set());
  };

  // Action: Remove All (filtered)
  const handleRemoveAll = () => {
    const idsToRemove = new Set(filteredChosen.map((i) => i.id));
    const newChosen = chosenItemIds.filter((id) => !idsToRemove.has(id));
    onChange(newChosen);
    setSelectedChosenIds(new Set());
  };

  // Double click transfer
  const handleDoubleClickAvailable = (id: string) => {
    onChange([...chosenItemIds, id]);
    setSelectedAvailableIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleDoubleClickChosen = (id: string) => {
    onChange(chosenItemIds.filter((itemId) => itemId !== id));
    setSelectedChosenIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  return (
    <div className="space-y-1.5">
      <div className="filter-horizontal-widget">
        {/* Left: Available Box */}
        <div className="filter-horizontal-col">
          <div className="filter-horizontal-header">
            <span>Available {title}</span>
            <span className="text-[10px] font-mono text-zinc-400">
              ({filteredAvailable.length} of {availablePool.length})
            </span>
          </div>

          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <Input
              type="text"
              placeholder={`Filter available ${title}...`}
              value={availableSearch}
              onChange={(e) => setAvailableSearch(e.target.value)}
              className="h-8 pl-8 text-xs bg-[#0b0e14] border-zinc-700/80 text-zinc-200"
            />
          </div>

          <div className="filter-horizontal-box">
            {filteredAvailable.length === 0 ? (
              <div className="p-4 text-center text-xs text-zinc-500 italic">
                {availablePool.length === 0 ? `All ${title} chosen` : 'No matching items'}
              </div>
            ) : (
              filteredAvailable.map((item) => {
                const isSelected = selectedAvailableIds.has(item.id);
                return (
                  <div
                    key={item.id}
                    onClick={() => toggleSelectAvailable(item.id)}
                    onDoubleClick={() => handleDoubleClickAvailable(item.id)}
                    className={`filter-horizontal-item ${isSelected ? 'selected' : ''}`}
                  >
                    <span className="font-medium truncate">
                      {item.subtitle ? (
                        <span className="text-zinc-400 font-mono text-[11px] mr-1.5">
                          {item.subtitle} |
                        </span>
                      ) : null}
                      {item.name}
                    </span>
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-2 flex justify-between">
            <button
              type="button"
              onClick={handleChooseAll}
              disabled={filteredAvailable.length === 0}
              className="text-[11px] text-[#79aec8] hover:text-[#a8d5e5] hover:underline disabled:opacity-40 disabled:hover:no-underline font-medium"
            >
              Choose all
            </button>
          </div>
        </div>

        {/* Center: Transfer Buttons */}
        <div className="filter-horizontal-buttons">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleChooseAll}
            disabled={filteredAvailable.length === 0}
            title="Choose all"
            className="h-8 w-8 p-0 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-zinc-200"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddSelected}
            disabled={selectedAvailableIds.size === 0}
            title="Add selected"
            className="h-8 w-8 p-0 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-zinc-200"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRemoveSelected}
            disabled={selectedChosenIds.size === 0}
            title="Remove selected"
            className="h-8 w-8 p-0 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-zinc-200"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRemoveAll}
            disabled={filteredChosen.length === 0}
            title="Remove all"
            className="h-8 w-8 p-0 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-zinc-200"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
        </div>

        {/* Right: Chosen Box */}
        <div className="filter-horizontal-col">
          <div className="filter-horizontal-header">
            <span>Chosen {title}</span>
            <span className="text-[10px] font-mono text-zinc-400">
              ({filteredChosen.length} of {chosenPool.length})
            </span>
          </div>

          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <Input
              type="text"
              placeholder={`Filter chosen ${title}...`}
              value={chosenSearch}
              onChange={(e) => setChosenSearch(e.target.value)}
              className="h-8 pl-8 text-xs bg-[#0b0e14] border-zinc-700/80 text-zinc-200"
            />
          </div>

          <div className="filter-horizontal-box">
            {filteredChosen.length === 0 ? (
              <div className="p-4 text-center text-xs text-zinc-500 italic">
                {chosenPool.length === 0 ? `No ${title} selected` : 'No matching items'}
              </div>
            ) : (
              filteredChosen.map((item) => {
                const isSelected = selectedChosenIds.has(item.id);
                return (
                  <div
                    key={item.id}
                    onClick={() => toggleSelectChosen(item.id)}
                    onDoubleClick={() => handleDoubleClickChosen(item.id)}
                    className={`filter-horizontal-item ${isSelected ? 'selected' : ''}`}
                  >
                    <span className="font-medium truncate">
                      {item.subtitle ? (
                        <span className="text-zinc-400 font-mono text-[11px] mr-1.5">
                          {item.subtitle} |
                        </span>
                      ) : null}
                      {item.name}
                    </span>
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-2 flex justify-between">
            <button
              type="button"
              onClick={handleRemoveAll}
              disabled={filteredChosen.length === 0}
              className="text-[11px] text-[#d9828b] hover:text-[#f87171] hover:underline disabled:opacity-40 disabled:hover:no-underline font-medium"
            >
              Remove all
            </button>
          </div>
        </div>
      </div>

      {helpText && <p className="django-help-text italic">{helpText}</p>}
    </div>
  );
}
