import { describe, it, expect, beforeEach, vi } from 'vitest';
import { OpenHandsClient, createClient, APIError, TimeoutError, NetworkError } from '../src';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('OpenHandsClient', () => {
  let client: OpenHandsClient;
  const baseUrl = 'http://localhost:8000';
  const apiKey = 'test-api-key';

  beforeEach(() => {
    client = createClient({ baseUrl, apiKey });
    mockFetch.mockClear();
  });

  describe('constructor', () => {
    it('should create client with correct config', () => {
      const config = client.getConfig();
      expect(config.baseUrl).toBe(baseUrl);
      expect(config.apiKey).toBe(apiKey);
      expect(config.timeout).toBe(30000);
      expect(config.retries).toBe(3);
    });

    it('should remove trailing slash from baseUrl', () => {
      const clientWithSlash = createClient({ baseUrl: 'http://localhost:8000/' });
      expect(clientWithSlash.getConfig().baseUrl).toBe('http://localhost:8000');
    });
  });

  describe('checkAlive', () => {
    it('should make GET request to /alive endpoint', async () => {
      const mockResponse = { status: 'ok' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await client.checkAlive();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/alive',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Session-API-Key': apiKey,
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('executeAction', () => {
    it('should execute command action', async () => {
      const mockObservation = {
        observation: 'run',
        content: 'Hello World',
        exit_code: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockObservation,
      });

      const result = await client.runCommand('echo "Hello World"', {
        thought: 'Testing command execution',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/execute_action',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            action: {
              action: 'run',
              command: 'echo "Hello World"',
              thought: 'Testing command execution',
            },
          }),
        })
      );
      expect(result).toEqual(mockObservation);
    });

    it('should read file', async () => {
      const mockObservation = {
        observation: 'read',
        content: 'file content',
        path: '/test/file.txt',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockObservation,
      });

      const result = await client.readFile('/test/file.txt', {
        start: 1,
        end: 10,
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/execute_action',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            action: {
              action: 'read',
              path: '/test/file.txt',
              start: 1,
              end: 10,
            },
          }),
        })
      );
      expect(result).toEqual(mockObservation);
    });
  });

  describe('error handling', () => {
    it('should throw APIError for HTTP errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'File not found' }),
      });

      await expect(client.checkAlive()).rejects.toThrow(APIError);
      await expect(client.checkAlive()).rejects.toThrow('File not found');
    });

    it('should throw TimeoutError for timeout', async () => {
      const shortTimeoutClient = createClient({
        baseUrl,
        apiKey,
        timeout: 100
      });

      mockFetch.mockImplementationOnce(() =>
        new Promise(resolve => setTimeout(resolve, 200))
      );

      await expect(shortTimeoutClient.checkAlive()).rejects.toThrow(TimeoutError);
    });

    it('should retry on network errors', async () => {
      const retryClient = createClient({
        baseUrl,
        apiKey,
        retries: 2,
        retryDelay: 10
      });

      // First call fails, second succeeds
      mockFetch
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ status: 'ok' }),
        });

      const result = await retryClient.checkAlive();
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(result).toEqual({ status: 'ok' });
    });
  });

  describe('file operations', () => {
    it('should upload file', async () => {
      const mockResponse = {
        filename: 'test.txt',
        destination: '/uploads',
        recursive: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const result = await client.uploadFile(file, '/uploads');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/upload_file',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should list files', async () => {
      const mockFiles = ['file1.txt', 'file2.txt', 'folder/'];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockFiles,
      });

      const result = await client.listFiles('/test');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/list_files',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ path: '/test' }),
        })
      );
      expect(result).toEqual(mockFiles);
    });
  });

  describe('browser operations', () => {
    it('should browse to URL', async () => {
      const mockObservation = {
        observation: 'browse',
        content: 'Page loaded',
        url: 'https://example.com',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockObservation,
      });

      const result = await client.browseUrl('https://example.com', {
        returnAxtree: true,
      });

      expect(result).toEqual(mockObservation);
    });

    it('should perform interactive browser actions', async () => {
      const mockObservation = {
        observation: 'browse',
        content: 'Action completed',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockObservation,
      });

      const result = await client.browseInteractive('click("button")', {
        returnAxtree: false,
      });

      expect(result).toEqual(mockObservation);
    });
  });

  describe('MCP operations', () => {
    it('should update MCP server', async () => {
      const mockResponse = {
        detail: 'MCP server updated successfully',
        router_error_log: '',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const tools = [
        { name: 'test-tool', command: 'test-command' },
      ];

      const result = await client.updateMCPServer(tools);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/update_mcp_server',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(tools),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('configuration', () => {
    it('should update configuration', () => {
      const newConfig = { timeout: 5000, retries: 5 };
      client.updateConfig(newConfig);

      const config = client.getConfig();
      expect(config.timeout).toBe(5000);
      expect(config.retries).toBe(5);
      expect(config.baseUrl).toBe(baseUrl); // Should remain unchanged
    });

    it('should set API key', () => {
      const newApiKey = 'new-api-key';
      client.setApiKey(newApiKey);

      expect(client.getConfig().apiKey).toBe(newApiKey);
    });
  });
});
