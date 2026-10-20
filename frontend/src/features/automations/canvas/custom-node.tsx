'use client';

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Zap,
  Sparkles,
  Layers,
  GitFork,
  Bot,
  Mail,
  MessageSquare,
  ShieldAlert,
  Clock,
  ArrowRight,
  Database,
  Globe,
  Code,
} from 'lucide-react';
import type { AutomationNode } from '../types';

const getCategoryStyles = (type: string, toolId?: string) => {
  if (type === 'trigger') {
    return {
      border: 'border-amber-500/40 hover:border-amber-500',
      badgeBg: 'bg-amber-500/10 text-amber-500 border-amber-500/30',
      glow: 'shadow-amber-500/10',
      icon: Zap,
    };
  }
  if (type === 'condition' || type === 'switch') {
    return {
      border: 'border-emerald-500/40 hover:border-emerald-500',
      badgeBg: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30',
      glow: 'shadow-emerald-500/10',
      icon: GitFork,
    };
  }
  if (type === 'ai_agent' || (toolId && toolId.includes('ai'))) {
    return {
      border: 'border-purple-500/40 hover:border-purple-500',
      badgeBg: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      glow: 'shadow-purple-500/10',
      icon: Sparkles,
    };
  }
  if (toolId && (toolId.includes('slack') || toolId.includes('email') || toolId.includes('message'))) {
    return {
      border: 'border-sky-500/40 hover:border-sky-500',
      badgeBg: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
      glow: 'shadow-sky-500/10',
      icon: MessageSquare,
    };
  }
  if (toolId && toolId.includes('http')) {
    return {
      border: 'border-indigo-500/40 hover:border-indigo-500',
      badgeBg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
      glow: 'shadow-indigo-500/10',
      icon: Globe,
    };
  }
  return {
    border: 'border-border hover:border-primary/60',
    badgeBg: 'bg-primary/10 text-primary border-primary/30',
    glow: 'shadow-primary/5',
    icon: Layers,
  };
};

function CustomWorkflowNodeComponent({ data, selected }: NodeProps) {
  const node = data as unknown as AutomationNode;
  const style = getCategoryStyles(node.type, node.tool_id);
  const IconComponent = style.icon;

  const isCondition = node.type === 'condition';
  const isTrigger = node.type === 'trigger';

  return (
    <div
      className={`min-w-[240px] max-w-[280px] rounded-xl border bg-card/95 backdrop-blur-md shadow-lg transition-all duration-150 ${style.border} ${
        selected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background shadow-xl' : ''
      }`}
    >
      {/* Target input handle (not on triggers) */}
      {!isTrigger && (
        <Handle
          type="target"
          position={Position.Left}
          id="input"
          className="!w-3 !h-3 !-left-1.5 !bg-muted-foreground !border-2 !border-background hover:!bg-primary transition-colors"
        />
      )}

      {/* Header */}
      <div className="p-3 border-b flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 truncate">
          <div className={`p-1.5 rounded-lg border ${style.badgeBg} shrink-0`}>
            <IconComponent className="h-4 w-4" />
          </div>
          <div className="truncate">
            <h4 className="text-xs font-semibold tracking-tight text-foreground truncate">{node.name}</h4>
            <p className="text-[10px] text-muted-foreground font-mono truncate">{node.tool_id || node.type}</p>
          </div>
        </div>
      </div>

      {/* Body / Config summary */}
      <div className="p-3 text-[11px] space-y-1.5">
        {node.description ? (
          <p className="text-muted-foreground line-clamp-2 leading-relaxed">{node.description}</p>
        ) : (
          <p className="text-muted-foreground italic">No description</p>
        )}

        {/* Badges */}
        <div className="flex flex-wrap gap-1 pt-1">
          {node.requires_approval && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-500 border border-amber-500/30">
              <ShieldAlert className="h-3 w-3" /> HITL Gate
            </span>
          )}
          {node.timeout_seconds && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground border">
              <Clock className="h-2.5 w-2.5" /> {node.timeout_seconds}s
            </span>
          )}
          {Object.keys(node.config || {}).length > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-muted/60 text-muted-foreground font-mono border">
              {Object.keys(node.config).length} params
            </span>
          )}
        </div>
      </div>

      {/* Source output handles */}
      {isCondition ? (
        <>
          {/* True branch handle */}
          <div className="relative">
            <Handle
              type="source"
              position={Position.Right}
              id="true"
              className="!w-3 !h-3 !-right-1.5 !top-[-10px] !bg-emerald-500 !border-2 !border-background hover:!scale-125 transition-transform"
            />
            <span className="absolute -right-7 -top-4 text-[9px] font-bold text-emerald-500">TRUE</span>
          </div>

          {/* False branch handle */}
          <div className="relative">
            <Handle
              type="source"
              position={Position.Right}
              id="false"
              className="!w-3 !h-3 !-right-1.5 !bottom-[-10px] !bg-rose-500 !border-2 !border-background hover:!scale-125 transition-transform"
            />
            <span className="absolute -right-8 -bottom-1 text-[9px] font-bold text-rose-500">FALSE</span>
          </div>
        </>
      ) : (
        <Handle
          type="source"
          position={Position.Right}
          id="output"
          className="!w-3 !h-3 !-right-1.5 !bg-primary !border-2 !border-background hover:!scale-125 transition-transform"
        />
      )}
    </div>
  );
}

export const CustomWorkflowNode = memo(CustomWorkflowNodeComponent);
