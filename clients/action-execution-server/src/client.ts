import {
  Action,
  ActionRequest,
  APIError,
  ClientConfig,
  ListFilesRequest,
  MCPTool,
  NetworkError,
  Observation,
  ServerInfo,
  TimeoutError,
  UploadFileResponse,
  VSCodeConnectionToken,
} from './types';

/**
 * TypeScript client for OpenHands Action Execution Server
 */
export class OpenHandsClient {
  private config: Required<ClientConfig>;
  private controller?: AbortController;

  constructor(config: ClientConfig) {
    this.config = {
      baseUrl: config.baseUrl.replace(/\/$/, ''), // Remove trailing slash
      apiKey: config.apiKey || '',
      timeout: config.timeout || 30000, // 30 seconds default
      retries: config.retries || 3,
      retryDelay: config.retryDelay || 1000, // 1 second default
    };
  }

  /**
   * Create request headers with authentication
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (this.config.apiKey) {
      headers['X-Session-API-Key'] = this.config.apiKey;
    }

    return headers;
  }

  /**
   * Make HTTP request with retry logic and timeout
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < this.config.retries; attempt++) {
      try {
        // Create new AbortController for each request
        this.controller = new AbortController();

        // Set up timeout
        const timeoutId = setTimeout(() => {
          this.controller?.abort();
        }, this.config.timeout);

        const response = await fetch(url, {
          ...options,
          headers: {
            ...this.getHeaders(),
            ...options.headers,
          },
          signal: this.controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new APIError(
            errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
            response.status,
            errorData
          );
        }

        return await response.json();
      } catch (error) {
        lastError = error as Error;

        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            throw new TimeoutError(`Request timed out after ${this.config.timeout}ms`);
          }

          if (error instanceof TypeError && error.message.includes('fetch')) {
            throw new NetworkError('Failed to connect to server');
          }
        }

        // Don't retry on client errors (4xx) except 429 (rate limit)
        if (error instanceof APIError && error.status && error.status >= 400 && error.status < 500 && error.status !== 429) {
          throw error;
        }

        // Wait before retry (except on last attempt)
        if (attempt < this.config.retries - 1) {
          await new Promise(resolve => setTimeout(resolve, this.config.retryDelay * (attempt + 1)));
        }
      }
    }

    throw lastError || new Error('Max retries exceeded');
  }

  /**
   * Cancel any ongoing requests
   */
  public cancelRequests(): void {
    if (this.controller) {
      this.controller.abort();
    }
  }

  /**
   * Check if the server is alive and initialized
   */
  public async checkAlive(): Promise<{ status: string }> {
    return this.makeRequest<{ status: string }>('/alive');
  }

  /**
   * Get server information including uptime and resource usage
   */
  public async getServerInfo(): Promise<ServerInfo> {
    return this.makeRequest<ServerInfo>('/server_info');
  }

  /**
   * Execute an action and get the observation
   */
  public async executeAction(action: Action): Promise<Observation> {
    const request: ActionRequest = { action };
    return this.makeRequest<Observation>('/execute_action', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Execute a command and get the output
   */
  public async runCommand(
    command: string,
    options: {
      background?: boolean;
      timeout?: number;
      cwd?: string;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'run',
      args: {
        command,
      }
    };

    if (options.background !== undefined) action.args.background = options.background;
    if (options.timeout !== undefined) action.args.timeout = options.timeout;
    if (options.cwd !== undefined) action.args.cwd = options.cwd;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Read a file
   */
  public async readFile(
    path: string,
    options: {
      start?: number;
      end?: number;
      viewRange?: [number, number];
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'read',
      args: {
        path,
      },
    };

    if (options.start !== undefined) action.args.start = options.start;
    if (options.end !== undefined) action.args.end = options.end;
    if (options.viewRange !== undefined) action.args.view_range = options.viewRange;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Write content to a file
   */
  public async writeFile(
    path: string,
    content: string,
    options: {
      start?: number;
      end?: number;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'write',
      args: {
        path,
        content,
      },
    };

    if (options.start !== undefined) action.args.start = options.start;
    if (options.end !== undefined) action.args.end = options.end;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Edit a file using the OH_ACI editor
   */
  public async editFile(
    path: string,
    options: {
      oldStr?: string;
      newStr?: string;
      insertLine?: number;
      command?: string;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'edit',
      args: {
        path,
        //     LLM_BASED_EDIT = 'llm_based_edit'
        // OH_ACI = 'oh_aci'  # openhands-aci
        impl_source: 'oh_aci',
      },
    };

    if (options.oldStr !== undefined) action.args.old_str = options.oldStr;
    if (options.newStr !== undefined) action.args.new_str = options.newStr;
    if (options.insertLine !== undefined) action.args.insert_line = options.insertLine;
    if (options.command !== undefined) action.args.command = options.command;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Run IPython/Jupyter code
   */
  public async runIPython(
    code: string,
    options: {
      kernelInitCode?: string;
      includeExtra?: boolean;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'run_ipython',
      args: {
        code,
      },
    };

    if (options.kernelInitCode !== undefined) action.args.kernel_init_code = options.kernelInitCode;
    if (options.includeExtra !== undefined) action.args.include_extra = options.includeExtra;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Browse to a URL
   */
  public async browseUrl(
    url: string,
    options: {
      returnAxtree?: boolean;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'browse',
      args: {
        url,
      },
    };

    if (options.returnAxtree !== undefined) action.args.return_axtree = options.returnAxtree;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Perform interactive browser actions
   */
  public async browseInteractive(
    browserActions: string,
    options: {
      returnAxtree?: boolean;
      thought?: string;
    } = {}
  ): Promise<Observation> {
    const action: any = {
      action: 'browse_interactive',
      args: {
        browser_actions: browserActions,
      },
    };

    if (options.returnAxtree !== undefined) action.args.return_axtree = options.returnAxtree;
    if (options.thought !== undefined) action.args.thought = options.thought;

    return this.executeAction(action);
  }

  /**
   * Update MCP server configuration
   */
  public async updateMCPServer(tools: MCPTool[]): Promise<{
    detail: string;
    router_error_log: string;
  }> {
    return this.makeRequest('/update_mcp_server', {
      method: 'POST',
      body: JSON.stringify(tools),
    });
  }

  /**
   * Upload a file to the server
   */
  public async uploadFile(
    file: File | Blob,
    destination: string = '/',
    options: {
      recursive?: boolean;
      filename?: string;
    } = {}
  ): Promise<UploadFileResponse> {
    const formData = new FormData();

    // Determine filename
    const filename = options.filename ||
      (file instanceof File ? file.name : 'uploaded_file');

    formData.append('file', file, filename);
    formData.append('destination', destination);
    formData.append('recursive', String(options.recursive || false));

    const headers = this.getHeaders();
    delete headers['Content-Type']; // Let browser set it for FormData

    return this.makeRequest<UploadFileResponse>('/upload_file', {
      method: 'POST',
      body: formData,
      headers,
    });
  }

  /**
   * Download files from the server
   */
  public async downloadFiles(path: string): Promise<Blob> {
    const url = `${this.config.baseUrl}/download_files?path=${encodeURIComponent(path)}`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.blob();
  }

  /**
   * List files in a directory
   */
  public async listFiles(path?: string): Promise<string[]> {
    const request: ListFilesRequest = path ? { path } : {};
    return this.makeRequest<string[]>('/list_files', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  /**
   * Get VSCode connection token
   */
  public async getVSCodeToken(): Promise<VSCodeConnectionToken> {
    return this.makeRequest<VSCodeConnectionToken>('/vscode/connection_token');
  }

  /**
   * Set API key for authentication
   */
  public setApiKey(apiKey: string): void {
    this.config.apiKey = apiKey;
  }

  /**
   * Get current configuration
   */
  public getConfig(): Readonly<Required<ClientConfig>> {
    return { ...this.config };
  }

  /**
   * Update client configuration
   */
  public updateConfig(config: Partial<ClientConfig>): void {
    this.config = {
      ...this.config,
      ...config,
      baseUrl: config.baseUrl ? config.baseUrl.replace(/\/$/, '') : this.config.baseUrl,
    };
  }
}

// Export convenience functions
export const createClient = (config: ClientConfig): OpenHandsClient => {
  return new OpenHandsClient(config);
};

export default OpenHandsClient;
