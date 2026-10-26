# -*- coding: utf-8 -*-
"""Cooperative JSON work using the standard decoder for individual records."""
from __future__ import unicode_literals

import codecs
import hashlib
import json
import re

BLOCK = 16384
_SPACE = re.compile(r'[ \t\r\n]*')


def complete(steps):
    for unused in steps:
        pass


def values(mapping):
    return mapping.itervalues() if hasattr(mapping, 'itervalues') else iter(mapping.values())


def items(mapping):
    return mapping.iteritems() if hasattr(mapping, 'iteritems') else iter(mapping.items())


def depth_steps(value, limit=64):
    stack = [(iter((value,)), 0)]
    count = 0
    while stack:
        iterator, depth = stack[-1]
        try:
            current = next(iterator)
        except StopIteration:
            stack.pop()
            continue
        if isinstance(current, (dict, list)):
            if depth > limit:
                raise ValueError('JSON nesting exceeds the supported data shape')
            stack.append((values(current) if isinstance(current, dict) else iter(current), depth + 1))
        count += 1
        if count % 128 == 0:
            yield None


def digest_steps(value, output):
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
    digest, chunks, length = hashlib.sha256(), [], 0
    for chunk in encoder.iterencode(value):
        chunks.append(chunk)
        length += len(chunk)
        if length >= BLOCK:
            digest.update(''.join(chunks).encode('utf-8'))
            chunks, length = [], 0
            yield None
    digest.update(''.join(chunks).encode('utf-8'))
    output[0] = digest.hexdigest()


class _JSONReader(object):
    def __init__(self, handle, limit, too_large):
        self.handle, self.limit, self.too_large = handle, limit, too_large
        self.buffer, self.position, self.eof, self.size = '', 0, False, 0
        self.utf8 = codecs.getincrementaldecoder('utf-8')()
        self.decoder = json.JSONDecoder()
        self.digest = hashlib.sha256()

    def fill(self):
        raw = self.handle.read(min(BLOCK, self.limit + 1 - self.size))
        self.size += len(raw)
        if self.size > self.limit:
            raise self.too_large
        self.digest.update(raw)
        self.eof = not raw
        self.buffer = self.buffer[self.position:] + self.utf8.decode(raw, self.eof)
        self.position = 0
        yield None

    def space(self):
        while True:
            self.position = _SPACE.match(self.buffer, self.position).end()
            if self.position < len(self.buffer) or self.eof:
                return
            for step in self.fill():
                yield step

    def atom(self, output):
        while True:
            try:
                value, end = self.decoder.raw_decode(self.buffer, self.position)
            except ValueError:
                if self.eof:
                    raise
            else:
                # A number/literal can continue in the next file block.
                if ((end < len(self.buffer) and self.buffer[end] in ',]}: \t\r\n') or
                        (end == len(self.buffer) and self.eof)):
                    self.position = end
                    output[0] = value
                    yield None
                    return
                if self.eof:
                    raise ValueError('Invalid JSON token')
            for step in self.fill():
                yield step

    def value(self, depth, output):
        for step in self.space():
            yield step
        if self.position == len(self.buffer):
            raise ValueError('Missing JSON value')
        char = self.buffer[self.position]
        # Split the envelope, payload and battle/period collections. Individual
        # battle records still use the established standard-library decoder.
        if depth >= 3 or char not in '{[':
            for step in self.atom(output):
                yield step
            return
        mapping = char == '{'
        result = {} if mapping else []
        closing = '}' if mapping else ']'
        self.position += 1
        first = True
        while True:
            for step in self.space():
                yield step
            if self.position >= len(self.buffer):
                raise ValueError('Unclosed JSON container')
            if first and self.buffer[self.position] == closing:
                self.position += 1
                break
            box = [None]
            if mapping:
                if self.buffer[self.position] != '"':
                    raise ValueError('JSON object key must be a string')
                for step in self.atom(box):
                    yield step
                key = box[0]
                for step in self.space():
                    yield step
                if self.position >= len(self.buffer) or self.buffer[self.position] != ':':
                    raise ValueError('Missing JSON colon')
                self.position += 1
            for step in self.value(depth + 1, box):
                yield step
            if mapping:
                result[key] = box[0]
            else:
                result.append(box[0])
            for step in self.space():
                yield step
            if self.position >= len(self.buffer):
                raise ValueError('Unclosed JSON container')
            char = self.buffer[self.position]
            self.position += 1
            if char == closing:
                break
            if char != ',':
                raise ValueError('Missing JSON comma')
            first = False
        output[0] = result
        yield None


def read_json_steps(path, limit, too_large, output):
    with open(path, 'rb') as handle:
        first = handle.read(min(BLOCK + 1, limit + 1))
        if len(first) > limit:
            raise too_large
        if len(first) <= BLOCK:
            output[0] = (json.loads(first.decode('utf-8')), hashlib.sha256(first).hexdigest(), len(first))
            yield None
            return
        handle.seek(0)
        reader = _JSONReader(handle, limit, too_large)
        box = [None]
        for step in reader.value(0, box):
            yield step
        for step in reader.space():
            yield step
        if reader.position != len(reader.buffer):
            raise ValueError('Trailing JSON data')
        output[0] = (box[0], reader.digest.hexdigest(), reader.size)
