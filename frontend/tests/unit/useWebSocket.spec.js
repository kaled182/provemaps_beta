import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useWebSocket } from '@/composables/useWebSocket';

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    
    // Simulate async connection
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 10);
  }
  
  send(data) {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  }
  
  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }
}

describe('useWebSocket', () => {
  let originalWebSocket;
  
  beforeEach(() => {
    originalWebSocket = global.WebSocket;
    global.WebSocket = MockWebSocket;
    vi.useFakeTimers();
  });
  
  afterEach(() => {
    global.WebSocket = originalWebSocket;
    vi.clearAllTimers();
    vi.useRealTimers();
  });
  
  it('connects automatically when autoConnect is true', async () => {
    const { connected, connecting } = useWebSocket('ws://localhost:8000/ws/test/', {
      autoConnect: true,
    });
    
    expect(connecting.value).toBe(true);
    
    // Fast-forward timers to simulate connection
    await vi.advanceTimersByTimeAsync(20);
    
    expect(connected.value).toBe(true);
    expect(connecting.value).toBe(false);
  });
  
  it('does not connect when autoConnect is false', () => {
    const { connected, connecting } = useWebSocket('ws://localhost:8000/ws/test/', {
      autoConnect: false,
    });
    
    expect(connected.value).toBe(false);
    expect(connecting.value).toBe(false);
  });
  
  it('parses JSON messages correctly', async () => {
    let capturedSocket;
    
    // Capture the socket instance when created
    const OriginalMockWebSocket = global.WebSocket;
    global.WebSocket = class extends OriginalMockWebSocket {
      constructor(url) {
        super(url);
        capturedSocket = this;
      }
    };
    
    const { lastMessage } = useWebSocket('ws://localhost:8000/ws/test/');
    
    await vi.advanceTimersByTimeAsync(20);
    
    // Simulate incoming message via captured socket
    const testData = { type: 'test', value: 123 };
    if (capturedSocket && capturedSocket.onmessage) {
      capturedSocket.onmessage({ data: JSON.stringify(testData) });
    }
    
    expect(lastMessage.value).toEqual(testData);
  });
  
  it('provides disconnect method', async () => {
    const { connected, disconnect } = useWebSocket('ws://localhost:8000/ws/test/');
    
    await vi.advanceTimersByTimeAsync(20);
    expect(connected.value).toBe(true);
    
    disconnect();
    expect(connected.value).toBe(false);
  });
});
