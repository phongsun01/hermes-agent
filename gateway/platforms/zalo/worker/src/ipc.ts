
export interface IPCRequest {
    id: string;
    method: string;
    params: any;
}

export interface IPCResponse {
    id: string;
    result?: any;
    error?: string;
}

export interface IPCEvent {
    type: 'event';
    data: {
        type: string;
        payload: any;
    };
}
