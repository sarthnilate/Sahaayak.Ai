import React, { useState } from 'react';
import {
  CheckSquare, ShieldCheck, ArrowRight, UserCheck, Clock,
  RefreshCw, CheckCircle2, Play, CheckCircle, AlertTriangle
} from 'lucide-react';
import { Task } from '../../types';
import { approveTask, updateTask } from '../../services/api';
import { PriorityBadge } from '../common/PriorityBadge';

interface Props {
  tasks: Task[];
  onRefresh: () => void;
  isLoading: boolean;
}

export const TasksView: React.FC<Props> = ({ tasks, onRefresh, isLoading }) => {
  const [statusFilter, setStatusFilter] = useState('all');
  const [assigneeMap, setAssigneeMap] = useState<{ [key: string]: string }>({});
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);

  const squadOptions = [
    'Ward F-South Dewatering Squad',
    'Matunga Traffic Police Division',
    'Garden Cell Chainsaw Squad #02',
    'Municipal Rapid Action Team',
    'Emergency Medical Response Unit'
  ];

  const handleApprove = async (task: Task) => {
    setUpdatingTaskId(task.id);
    const assigned = assigneeMap[task.id] || squadOptions[0];
    try {
      await approveTask(task.id, assigned);
      onRefresh();
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setUpdatingTaskId(null);
    }
  };

  const handleStatusTransition = async (taskId: string, newStatus: string) => {
    setUpdatingTaskId(taskId);
    try {
      await updateTask(taskId, { status: newStatus });
      onRefresh();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setUpdatingTaskId(null);
    }
  };

  const filteredTasks = tasks.filter((t) => {
    if (statusFilter !== 'all' && t.status !== statusFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      
      {/* Header and Safety Notice */}
      <div className="bg-[#151515] border border-[#282828] rounded-xl p-5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-[#D4FF3F]" />
            <h2 className="text-base font-bold text-white font-mono uppercase tracking-wide">
              Coordinator Task Dispatch & Approval Center
            </h2>
          </div>
          <span className="text-xs font-mono text-[#D4FF3F]">
            Human-in-the-Loop Protocol Enforced
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[#0B0B0B] border border-[#282828] text-xs font-mono text-[#A7A7A7] flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-[#F5B942] shrink-0 mt-0.5" />
          <span>
            Tasks recommended by AI require explicit human coordinator approval before dispatch.
            No automated sirens or emergency service dispatches occur autonomously.
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {['all', 'suggested', 'pending', 'in_progress', 'completed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold uppercase transition-all ${
                statusFilter === st
                  ? 'bg-[#FF2DA8] text-white shadow-[0_0_10px_rgba(255,45,168,0.3)]'
                  : 'bg-[#151515] text-[#A7A7A7] hover:text-white border border-[#282828]'
              }`}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        <button
          onClick={onRefresh}
          className="p-2 rounded-lg bg-[#151515] border border-[#282828] text-[#A7A7A7] hover:text-white"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Tasks Grid */}
      <div className="space-y-3">
        {filteredTasks.length === 0 ? (
          <div className="bg-[#151515] border border-[#282828] rounded-xl p-8 text-center text-xs font-mono text-[#A7A7A7]">
            No tasks found matching active filter.
          </div>
        ) : (
          filteredTasks.map((task) => {
            const isProcessing = updatingTaskId === task.id;
            return (
              <div
                key={task.id}
                className="bg-[#151515] border border-[#282828] hover:border-[#383838] rounded-xl p-4 sm:p-5 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <PriorityBadge priority={task.priority} />
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                      task.status === 'completed'
                        ? 'bg-[#10291F] text-[#48C78E] border border-[#48C78E]/30'
                        : task.status === 'in_progress'
                        ? 'bg-[#351024] text-[#FF2DA8] border border-[#FF2DA8]/30'
                        : task.status === 'pending'
                        ? 'bg-[#252B12] text-[#D4FF3F] border border-[#D4FF3F]/30'
                        : 'bg-[#30240D] text-[#F5B942] border border-[#F5B942]/30'
                    }`}>
                      {task.status.replace('_', ' ')}
                    </span>
                    {task.assigned_to && (
                      <span className="text-xs font-mono text-[#A7A7A7] flex items-center gap-1">
                        <UserCheck className="w-3.5 h-3.5 text-[#D4FF3F]" />
                        {task.assigned_to}
                      </span>
                    )}
                  </div>

                  <span className="text-[11px] font-mono text-[#A7A7A7]">
                    Created: {new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                <h3 className="font-bold text-sm text-white mb-1.5">{task.title}</h3>
                <p className="text-xs text-[#A7A7A7] leading-relaxed mb-4">{task.description}</p>

                {/* Task State Actions */}
                <div className="pt-3 border-t border-[#242424] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="text-xs font-mono text-[#888]">
                    {task.approved_by ? (
                      <span>Approved by: <strong className="text-white">{task.approved_by}</strong></span>
                    ) : (
                      <span className="text-[#F5B942]">Awaiting coordinator approval</span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {task.status === 'suggested' && (
                      <>
                        <select
                          value={assigneeMap[task.id] || squadOptions[0]}
                          onChange={(e) => setAssigneeMap({ ...assigneeMap, [task.id]: e.target.value })}
                          className="bg-[#0B0B0B] border border-[#282828] rounded px-2.5 py-1 text-xs font-mono text-white outline-none"
                        >
                          {squadOptions.map((sq, i) => (
                            <option key={i} value={sq}>{sq}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleApprove(task)}
                          disabled={isProcessing}
                          className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#FF2DA8] hover:bg-[#E91E93] text-white shadow-[0_0_10px_rgba(255,45,168,0.3)] flex items-center gap-1.5 transition-all"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>{isProcessing ? 'APPROVING...' : 'APPROVE TASK'}</span>
                        </button>
                      </>
                    )}

                    {task.status === 'pending' && (
                      <button
                        onClick={() => handleStatusTransition(task.id, 'in_progress')}
                        disabled={isProcessing}
                        className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#1D1D1D] hover:bg-[#282828] text-[#FF2DA8] border border-[#FF2DA8]/40 flex items-center gap-1.5"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>START EXECUTION</span>
                      </button>
                    )}

                    {task.status === 'in_progress' && (
                      <button
                        onClick={() => handleStatusTransition(task.id, 'completed')}
                        disabled={isProcessing}
                        className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-[#10291F] hover:bg-[#1a4031] text-[#48C78E] border border-[#48C78E]/40 flex items-center gap-1.5"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>MARK COMPLETED</span>
                      </button>
                    )}

                    {task.status === 'completed' && (
                      <span className="text-xs font-mono text-[#48C78E] font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" />
                        TASK RESOLVED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
