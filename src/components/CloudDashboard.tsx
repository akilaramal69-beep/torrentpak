import React, { useState, useEffect } from 'react';
import { pikpak } from '../services/cloudService';
import { CloseIcon } from './Icons';

interface CloudFile {
    id: string;
    kind: string;
    name: string;
    size: string;
    created_time: string;
    [key: string]: any;
}

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
    const [activeTab, setActiveTab] = useState<'tasks' | 'files'>('tasks');
    const [tasks, setTasks] = useState<CloudTask[]>([]);
    const [files, setFiles] = useState<CloudFile[]>([]);
    const [currentFolder, setCurrentFolder] = useState<string | null>(null);
    const [folderStack, setFolderStack] = useState<{ id: string; name: string }[]>([]);
    const [user, setUser] = useState<any>(null);

    useEffect(() => {
        if (isOpen) {
            checkAuth();
        }
    }, [isOpen]);

    useEffect(() => {
        let interval: any;
        if (isOpen && activeTab === 'tasks') {
            loadTasks();
            interval = setInterval(loadTasks, 5000);
        }
        return () => clearInterval(interval);
    }, [isOpen, activeTab]);

    useEffect(() => {
        if (isOpen && activeTab === 'files') {
            loadFiles(currentFolder);
        }
    }, [isOpen, activeTab, currentFolder]);

    const checkAuth = async () => {
        try {
            const data = await pikpak.getUser();
            setUser(data);
        } catch (e) {
            console.error(e);
        }
    };

    const loadTasks = async () => {
        try {
            const data = await pikpak.getTasks();
            setTasks(data.tasks || []);
        } catch (e) {
            console.error(e);
        }
    };

    const loadFiles = async (parentId?: string | null) => {
        try {
            const data = await pikpak.getFiles(parentId || undefined);
            setFiles(data.files || []);
        } catch (e) {
            console.error(e);
        }
    };

    const navigateToFolder = (folderId: string | null, folderName: string) => {
        if (folderId === null) {
            setCurrentFolder(null);
            setFolderStack([]);
        } else {
            setCurrentFolder(folderId);
            setFolderStack(prev => [...prev, { id: folderId, name: folderName }]);
        }
    };

    const navigateUp = () => {
        if (folderStack.length <= 1) {
            setCurrentFolder(null);
            setFolderStack([]);
        } else {
            const newStack = folderStack.slice(0, -1);
            setFolderStack(newStack);
            setCurrentFolder(newStack[newStack.length - 1].id);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden">
                <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-800/50">
                    <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-cyan-300">
                        Cloud Drive
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <CloseIcon />
                    </button>
                </div>

                <div className="flex-1 overflow-auto p-4">
                    <div className="h-full flex flex-col">
                        <div className="flex gap-2 mb-4">
                            <button
                                onClick={() => setActiveTab('tasks')}
                                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'tasks' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                            >
                                Active Transfers
                            </button>
                            <button
                                onClick={() => setActiveTab('files')}
                                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'files' ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'}`}
                            >
                                All Files
                            </button>
                            <div className="flex-1"></div>
                            {user && <span className="text-sm text-slate-500 self-center">Welcome, {user.username}</span>}
                        </div>

                        {activeTab === 'tasks' && (
                            <div className="space-y-3">
                                {tasks.length === 0 ? (
                                    <p className="text-center text-slate-500 py-8">No active transfers</p>
                                ) : (
                                    tasks.map(task => (
                                        <div key={task.id} className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                                            <div className="flex justify-between mb-2">
                                                <span className="font-medium text-slate-200 truncate pr-4" title={task.name}>{task.name}</span>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${task.phase === 'PHASE_TYPE_COMPLETE' ? 'bg-green-900/50 text-green-400' :
                                                        task.phase === 'PHASE_TYPE_ERROR' ? 'bg-red-900/50 text-red-400' : 'bg-sky-900/50 text-sky-400'
                                                    }`}>
                                                    {task.phase?.replace('PHASE_TYPE_', '')}
                                                </span>
                                            </div>
                                            <div className="w-full bg-slate-700 h-1.5 rounded-full overflow-hidden">
                                                <div className="bg-sky-500 h-full transition-all duration-300" style={{ width: `${task.progress}%` }}></div>
                                            </div>
                                            <div className="flex justify-between mt-1 text-xs text-slate-500">
                                                <span>{task.file_size ? formatSize(task.file_size) : ''}</span>
                                                <span>{task.progress}%</span>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}

                        {activeTab === 'files' && (
                            <div className="flex-1 flex flex-col min-h-0">
                                <div className="flex items-center gap-2 mb-3 text-sm overflow-x-auto pb-1">
                                    <button onClick={() => navigateToFolder(null, '')} className="text-slate-400 hover:text-white">Home</button>
                                    {folderStack.map((f) => (
                                        <React.Fragment key={f.id}>
                                            <span className="text-slate-600">/</span>
                                            <span className="text-slate-200 whitespace-nowrap">{f.name}</span>
                                        </React.Fragment>
                                    ))}
                                </div>
                                <div className="flex-1 overflow-y-auto space-y-2 pr-2">
                                    {folderStack.length > 0 && (
                                        <button onClick={navigateUp} className="w-full text-left p-3 rounded-lg bg-slate-800/30 hover:bg-slate-800/50 border border-slate-800 flex items-center gap-3">
                                            <span className="text-xl">📁</span> <span className="text-slate-300">..</span>
                                        </button>
                                    )}
                                    {files.map(file => {
                                        const isFolder = file.kind === 'drive#folder';
                                        return (
                                            <div key={file.id} onClick={() => isFolder ? navigateToFolder(file.id, file.name) : null} className={`w-full text-left p-3 rounded-lg bg-slate-800/30 border border-slate-700 flex items-center justify-between gap-3 group ${isFolder ? 'cursor-pointer hover:bg-slate-800/50' : ''}`}>
                                                <div className="flex items-center gap-3 min-w-0">
                                                    <span className="text-xl flex-shrink-0">{isFolder ? '📁' : '📄'}</span>
                                                    <div className="min-w-0">
                                                        <p className="text-slate-200 truncate pr-2" title={file.name}>{file.name}</p>
                                                        <p className="text-xs text-slate-500">{formatSize(file.size)} • {new Date(file.created_time).toLocaleDateString()}</p>
                                                    </div>
                                                </div>
                                                {!isFolder && (
                                                    <a href={`/api/proxy/download/${file.id}`} target="_blank" download className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity">Download</a>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
