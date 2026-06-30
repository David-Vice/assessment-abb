import { describe, expect, it } from 'vitest';

import { parseSSEBlock, splitSSEBuffer } from './sse';

describe('parseSSEBlock', () => {
  it('parses a CRLF token event (the format sse-starlette emits)', () => {
    const block = 'event: token\r\ndata: {"token": "Hi"}';
    expect(parseSSEBlock(block)).toEqual({ event: 'token', data: '{"token": "Hi"}' });
  });

  it('parses an LF-only event', () => {
    const block = 'event: done\ndata: {"answer": "x"}';
    expect(parseSSEBlock(block)).toEqual({ event: 'done', data: '{"answer": "x"}' });
  });

  it('returns null for a ping comment block', () => {
    expect(parseSSEBlock(': ping - 2026-06-30')).toBeNull();
  });

  it('returns null for an empty block', () => {
    expect(parseSSEBlock('')).toBeNull();
  });

  it('joins multi-line data fields', () => {
    const block = 'event: token\r\ndata: line1\r\ndata: line2';
    expect(parseSSEBlock(block)).toEqual({ event: 'token', data: 'line1\nline2' });
  });

  it('defaults to the "message" event when none is given', () => {
    expect(parseSSEBlock('data: {"x":1}')).toEqual({ event: 'message', data: '{"x":1}' });
  });
});

describe('splitSSEBuffer', () => {
  it('splits complete CRLF events and retains the incomplete tail', () => {
    const buffer =
      'event: token\r\ndata: {"token": "a"}\r\n\r\nevent: token\r\ndata: {"token": "b"}\r\n\r\nevent: token\r\ndata: {"to';
    const { blocks, rest } = splitSSEBuffer(buffer);

    expect(blocks).toEqual([
      'event: token\r\ndata: {"token": "a"}',
      'event: token\r\ndata: {"token": "b"}',
    ]);
    expect(rest).toBe('event: token\r\ndata: {"to');
  });

  it('reassembles an event split across two reads', () => {
    // First read ends mid-event.
    let buffer = 'event: token\r\ndata: {"tok';
    let result = splitSSEBuffer(buffer);
    expect(result.blocks).toEqual([]);
    expect(result.rest).toBe(buffer);

    // Second read completes it.
    buffer = result.rest + 'en": "x"}\r\n\r\n';
    result = splitSSEBuffer(buffer);
    expect(result.blocks).toEqual(['event: token\r\ndata: {"token": "x"}']);
    expect(result.rest).toBe('');
  });

  it('handles a full ping + token + done stream end to end', () => {
    const stream =
      ': ping - t\r\n\r\nevent: token\r\ndata: {"token": "The"}\r\n\r\nevent: done\r\ndata: {"answer": "The"}\r\n\r\n';
    const { blocks, rest } = splitSSEBuffer(stream);

    const events = blocks.map(parseSSEBlock);
    expect(events[0]).toBeNull(); // ping
    expect(events[1]).toEqual({ event: 'token', data: '{"token": "The"}' });
    expect(events[2]).toEqual({ event: 'done', data: '{"answer": "The"}' });
    expect(rest).toBe('');
  });
});
