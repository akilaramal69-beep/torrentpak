import React, { useState, useEffect } from 'react';
import { pikpak } from '../services/cloudService';
import { CloseIcon } from './Icons';

interface CloudTask {
    id: string;
    name: string;
    phase: string;
    progress: number;
    file_size?: string;
    [key: string]: any;
}

interface CloudDashboardProps {
    isOpen: boolean;
    onClose: () => void;
}

const formatSize = (sizeStr: string) => {
    const bytes = parseInt(sizeStr);
    if (isNaN(bytes)) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const CloudDashboard: React.FC<CloudDashboardProps> = ({ isOpen, onClose }) => {
    const [tasks, setTasks] = useState<CloudTask[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        let interval: any;
        if (isOpen) {
            loadTasks();
            interval = setInterval(loadTasks, 5000);
        }
        return () => clearInterval(interval);
    }, [isOpen]);

    const loadTasks = async () => {
        try {
            const data = await pikpak.getTasks();
            setTasks(data.tasks || []);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-xl max-h-[80vh] flex flex-col overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-800/50">
                    <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-cyan-300">
                        My Downloads
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <CloseIcon />
                    </button>
                </div>

                <div className="flex-1 overflow-auto p-6">
                    <div className="h-full flex flex-col">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Active & Recent Transfers</h3>
                            <button
                                onClick={() => { setIsLoading(true); loadTasks(); }}
                                className="text-xs text-sky-400 hover:text-sky-300 font-medium transition-colors"
                            >
                                {isLoading ? 'Refreshing...' : 'Refresh List'}
                            </button>
                        </div>

                        <div className="space-y-4">
                            {tasks.length === 0 ? (
                                <div className="text-center py-12 px-4 bg-slate-800/30 border border-dashed border-slate-700 rounded-lg">
                                    <p className="text-slate-400">No active downloads.</p>
                                    <p className="text-xs text-slate-500 mt-1">Start a search to add torrents to your cloud.</p>
                                </div>
                            ) : (
                                tasks.map(task => (
                                    <div key={task.id} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700 shadow-sm">
                                        <div className="flex justify-between items-start gap-3 mb-3">
                                            <span className="font-medium text-slate-200 text-sm break-all leading-tight" title={task.name}>
                                                {task.name}
                                            </span>
                                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${task.phase === 'PHASE_TYPE_COMPLETE' ? 'bg-green-900/40 text-green-400 border border-green-800/50' :
                                                    task.phase === 'PHASE_TYPE_ERROR' ? 'bg-red-900/40 text-red-400 border border-red-800/50' :
                                                        'bg-sky-900/40 text-sky-400 border border-sky-800/50'
                                                }`}>
                                                {task.phase?.replace('PHASE_TYPE_', '')}
                                            </span>
                                        </div>

                                        <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden shadow-inner mb-2">
                                            <div
                                                className={`h-full transition-all duration-500 ease-out ${task.phase === 'PHASE_TYPE_COMPLETE' ? 'bg-green-500' : 'bg-sky-500'
                                                    }`}
                                                style={{ width: `${task.progress}%` }}
                                            ></div>
                                        </div>

                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-slate-400 font-mono italic">
                                                {task.file_size ? formatSize(task.file_size) : ''}
                                            </span>
                                            <span className="text-sky-400 font-bold">
                                                {task.progress}%
                                            </span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-slate-800/30 border-t border-slate-800 text-center">
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest">
                        PikPak Cloud Integration Active
                    </p>
                </div>
            </div>
        </div>
    );
};
