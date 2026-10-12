'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { allNavItems, canSeeItem, type NavItem } from '@/lib/navigation';

export default function CommandPalette({
  open,
  onOpenChange,
  profile,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profile: any;
}) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return allNavItems().filter((item) => {
      if (!canSeeItem(item, profile)) return false;
      if (!needle) return true;
      return `${item.name} ${item.keywords || ''} ${item.href}`.toLowerCase().includes(needle);
    });
  }, [profile, query]);

  useEffect(() => {
    setActive(0);
  }, [query, open]);

  const go = (item: NavItem) => {
    onOpenChange(false);
    setQuery('');
    router.push(item.href);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg gap-3 p-3">
        <DialogHeader>
          <DialogTitle className="text-sm font-medium text-muted-foreground">Jump to</DialogTitle>
        </DialogHeader>
        <Input
          autoFocus
          placeholder="Search screens"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setActive((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
            } else if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActive((current) => Math.max(current - 1, 0));
            } else if (event.key === 'Enter' && items[active]) {
              event.preventDefault();
              go(items[active]);
            }
          }}
        />
        <div className="max-h-72 overflow-auto">
          {items.length === 0 && (
            <p className="px-2 py-6 text-center text-sm text-muted-foreground">No matching screens</p>
          )}
          {items.map((item, index) => {
            const Icon = item.icon;
            return (
              <button
                key={item.href}
                type="button"
                onClick={() => go(item)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm ${index === active ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'}`}
              >
                <Icon className="size-4 text-muted-foreground" />
                <span>{item.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">{item.href.replace('/app/', '')}</span>
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
