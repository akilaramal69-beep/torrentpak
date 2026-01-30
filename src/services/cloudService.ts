export const pikpak = {
    async request(endpoint: string, options: Omit<RequestInit, 'body'> & { body?: any } = {}) {
        const url = `/api${endpoint}`;
        const config: RequestInit = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        const response = await fetch(url, config);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Request failed');
        }
        return response.json();
    },

    async getUser() {
        return this.request('/user');
    },

    async addDownload(url: string, name?: string) {
        return this.request('/download', {
            method: 'POST',
            body: { url, name }
        });
    },

    async getTasks() {
        return this.request('/tasks');
    },

    async getFiles(parentId?: string) {
        const endpoint = parentId ? `/files?parent_id=${parentId}` : '/files';
        return this.request(endpoint);
    }
};
