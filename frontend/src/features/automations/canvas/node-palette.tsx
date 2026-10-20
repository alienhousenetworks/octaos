'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Zap,
  GitFork,
  Sparkles,
  Layers,
  ShieldCheck,
  Plus,
  MessageSquare,
  Globe,
  Database,
  Clock,
  Briefcase,
  Target,
  AlertTriangle,
  Bot,
  FileText,
  FileCode,
  Play,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useWorkflowEditorStore } from '../state/workflow-editor-store';
import { STATIC_ENTERPRISE_CATALOG } from '../catalog/node-catalog';
import type { NodeDefinition, NodeCategory, AutomationNode } from '../types';

const ICON_MAP: Record<string, any> = {
  Globe,
  Play,
  Clock,
  Target,
  AlertTriangle,
  Zap,
  Briefcase,
  GitFork,
  Layers,
  Sparkles,
  Bot,
  FileText,
  FileCode,
  Database,
  ShieldCheck,
  MessageSquare,
};

export function WorkflowNodePalette({ API_URL }: { API_URL?: string }) {
  const [search, setSearch] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    triggers: true,
    document_intelligence: true,
    ai_agents: true,
    control_flow: false,
    connectivity: false,
    native_modules: false,
  });

  const activeMode = useWorkflowEditorStore((s) => s.activeMode);
  const addNode = useWorkflowEditorStore((s) => s.addNode);

  // Filter Catalog by Mode and Search Query
  const filteredCatalog = useMemo(() => {
    return STATIC_ENTERPRISE_CATALOG.map((cat) => {
      const filteredFamilies = cat.families
        .map((fam) => {
          const matchingNodes = fam.nodes.filter((node) => {
            // Mode filter
            if (activeMode === 'document' && node.mode !== 'all' && node.mode !== 'document') {
              return false;
            }
            if (activeMode === 'ai_agent' && node.mode !== 'all' && node.mode !== 'ai_agent') {
              return false;
            }

            // Search filter
            if (!search.trim()) return true;
            const q = search.toLowerCase();
            return (
              node.name.toLowerCase().includes(q) ||
              node.description.toLowerCase().includes(q) ||
              node.node_id.toLowerCase().includes(q) ||
              fam.name.toLowerCase().includes(q)
            );
          });

          return {
            ...fam,
            nodes: matchingNodes,
          };
        })
        .filter((fam) => fam.nodes.length > 0);

      return {
        ...cat,
        families: filteredFamilies,
      };
    }).filter((cat) => cat.families.length > 0);
  }, [activeMode, search]);

  const toggleCategory = (catId: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  const handleAddNode = (nodeDef: NodeDefinition) => {
    let nodeType = 'action';
    if (nodeDef.category === 'triggers') nodeType = 'trigger';
    else if (nodeDef.category === 'control_flow' && nodeDef.node_id.includes('if_else')) nodeType = 'condition';
    else if (nodeDef.category === 'ai_agents') nodeType = 'ai_agent';

    const newNode: Partial<AutomationNode> = {
      name: nodeDef.name,
      type: nodeType,
      tool_id: nodeDef.node_id,
      description: nodeDef.description,
      config: { ...(nodeDef.default_config || {}) },
      requires_approval: nodeDef.requires_approval,
      display_icon: nodeDef.icon || 'Layers',
    };
    addNode(newNode);
  };

  const totalAvailableNodes = useMemo(() => {
    return filteredCatalog.reduce(
      (acc, cat) => acc + cat.families.reduce((famAcc, fam) => famAcc + fam.nodes.length, 0),
      0
    );
  }, [filteredCatalog]);

  return (
    <div className="w-80 border-r bg-card/70 backdrop-blur-md flex flex-col h-full select-none z-10">
      {/* Header & Search */}
      <div className="p-3 border-b space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Enterprise Library
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">
            {totalAvailableNodes} nodes
          </span>
        </div>

        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search 3-level catalog..."
            className="pl-8 h-8 text-xs bg-background/80"
          />
        </div>

        {/* Current Active Mode Indicator */}
        <div className="flex items-center justify-between text-[11px] px-2 py-1 bg-muted/50 rounded border">
          <span className="text-muted-foreground">Active Canvas Mode:</span>
          <span className="font-semibold capitalize text-primary font-mono">
            {activeMode === 'ai_agent' ? 'AI Agents' : activeMode}
          </span>
        </div>
      </div>

      {/* 3-Level Accordion Catalog */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2 text-xs">
        {filteredCatalog.map((cat) => {
          const isCatExpanded = expandedCategories[cat.id] ?? true;

          return (
            <div key={cat.id} className="border rounded-lg bg-card/60 overflow-hidden">
              {/* Category Header */}
              <button
                onClick={() => toggleCategory(cat.id)}
                className="w-full px-2.5 py-2 flex items-center justify-between bg-muted/30 hover:bg-muted/60 transition-colors text-left"
              >
                <div className="flex items-center gap-1.5 font-semibold text-xs text-foreground">
                  {isCatExpanded ? (
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  <span>{cat.name}</span>
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {cat.families.reduce((sum, f) => sum + f.nodes.length, 0)}
                </span>
              </button>

              {/* Families in Category */}
              {isCatExpanded && (
                <div className="p-2 space-y-3 border-t">
                  {cat.families.map((family) => (
                    <div key={family.id} className="space-y-1.5">
                      <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground px-1 flex items-center justify-between">
                        <span>{family.name}</span>
                      </div>

                      {/* Nodes in Family */}
                      <div className="space-y-1">
                        {family.nodes.map((node) => {
                          const IconComponent = ICON_MAP[node.icon] || Layers;

                          return (
                            <div
                              key={node.node_id}
                              onClick={() => handleAddNode(node)}
                              className="group p-2 rounded-md border bg-background/80 hover:border-primary/50 hover:bg-muted/50 transition-all cursor-pointer space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 truncate">
                                  <div className="p-1 rounded bg-muted text-muted-foreground group-hover:text-primary transition-colors">
                                    <IconComponent className="h-3.5 w-3.5" />
                                  </div>
                                  <span className="font-medium text-xs text-foreground truncate">
                                    {node.name}
                                  </span>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Plus className="h-3 w-3" />
                                </Button>
                              </div>

                              <p className="text-[10px] text-muted-foreground line-clamp-1 leading-snug">
                                {node.description}
                              </p>

                              {/* Badges */}
                              <div className="flex items-center gap-1.5 pt-0.5">
                                {node.requires_approval && (
                                  <span className="inline-flex items-center gap-0.5 text-[9px] px-1 py-0.2 rounded bg-amber-500/10 text-amber-600 font-medium">
                                    <ShieldAlert className="h-2.5 w-2.5" /> HITL
                                  </span>
                                )}
                                {node.risk_level === 'high' && (
                                  <span className="text-[9px] px-1 py-0.2 rounded bg-red-500/10 text-red-600 font-mono">
                                    high risk
                                  </span>
                                )}
                                <span className="text-[9px] text-muted-foreground font-mono truncate max-w-[120px]">
                                  {node.node_id}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
