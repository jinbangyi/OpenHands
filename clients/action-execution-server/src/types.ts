/**
 * Type definitions for OpenHands Action Execution Server API
 */

// Base Action Types
export interface BaseAction {
  action: string;
  thought?: string;
  [key: string]: any;
}

export interface CmdRunAction extends BaseAction {
  action: 'run';
  command: string;
  background?: boolean;
  timeout?: number;
  keep_prompt?: boolean;
  cwd?: string;
}

export interface FileReadAction extends BaseAction {
  action: 'read';
  path: string;
  start?: number;
  end?: number;
  view_range?: [number, number];
  impl_source?: 'OH_ACI' | 'default';
}

export interface FileWriteAction extends BaseAction {
  action: 'write';
  path: string;
  content: string;
  start?: number;
  end?: number;
}

export interface FileEditAction extends BaseAction {
  action: 'edit';
  path: string;
  file_text?: string;
  old_str?: string;
  new_str?: string;
  insert_line?: number;
  command?: string;
  impl_source?: 'OH_ACI';
}

export interface IPythonRunCellAction extends BaseAction {
  action: 'run_ipython';
  code: string;
  kernel_init_code?: string;
  include_extra?: boolean;
}

export interface BrowseURLAction extends BaseAction {
  action: 'browse';
  url: string;
  return_axtree?: boolean;
}

export interface BrowseInteractiveAction extends BaseAction {
  action: 'browse_interactive';
  browser_actions: string;
  return_axtree?: boolean;
}

export type Action =
  | CmdRunAction
  | FileReadAction
  | FileWriteAction
  | FileEditAction
  | IPythonRunCellAction
  | BrowseURLAction
  | BrowseInteractiveAction;

// Observation Types
export interface BaseObservation {
  observation: string;
  content: string;
  timestamp?: string;
  [key: string]: any;
}

export interface CmdOutputObservation extends BaseObservation {
  observation: 'run';
  exit_code: number;
  command_id?: number;
}

export interface FileReadObservation extends BaseObservation {
  observation: 'read';
  path: string;
  impl_source?: string;
}

export interface FileWriteObservation extends BaseObservation {
  observation: 'write';
  path: string;
}

export interface FileEditObservation extends BaseObservation {
  observation: 'edit';
  path: string;
  old_content?: string;
  new_content?: string;
  diff?: string;
  impl_source?: string;
}

export interface IPythonRunCellObservation extends BaseObservation {
  observation: 'run_ipython';
  code?: string;
}

export interface BrowseObservation extends BaseObservation {
  observation: 'browse';
  url?: string;
  screenshot?: string;
  open_pages_urls?: string[];
  focused_page_url?: string;
  last_browser_action?: string;
  last_browser_action_error?: string;
  axtree?: string;
}

export interface ErrorObservation extends BaseObservation {
  observation: 'error';
  error_code?: string;
}

export type Observation =
  | CmdOutputObservation
  | FileReadObservation
  | FileWriteObservation
  | FileEditObservation
  | IPythonRunCellObservation
  | BrowseObservation
  | ErrorObservation;

// API Request/Response Types
export interface ActionRequest {
  action: Action;
}

export interface ServerInfo {
  uptime: number;
  idle_time: number;
  resources: {
    cpu_percent: number;
    memory_percent: number;
    disk_usage: number;
    [key: string]: any;
  };
}

export interface MCPTool {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  timeout?: number;
}

export interface UploadFileResponse {
  filename: string;
  destination: string;
  recursive: boolean;
}

export interface ListFilesRequest {
  path?: string;
}

export interface VSCodeConnectionToken {
  token: string | null;
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  detail?: string;
}

// Client Configuration
export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

// Error Types
export class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class TimeoutError extends Error {
  constructor(message: string = 'Request timed out') {
    super(message);
    this.name = 'TimeoutError';
  }
}

export class NetworkError extends Error {
  constructor(message: string = 'Network error occurred') {
    super(message);
    this.name = 'NetworkError';
  }
}
