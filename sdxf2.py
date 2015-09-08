# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import struct

def utfOut(val):
	if val < 0:
		raise ValueError('negative values not permitted here: %d', val)
	elif val <= 0x07f:
		return bytearray([val])
	elif val <= 0x07ff:
		return bytearray([((val>>6)&0x1f)|0x0c0, val&0x3f])
	elif val <= 0x0ffff:
		return bytearray([((val>>12)&0x0f)|0x0e0, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x1fffff:
		return bytearray([((val>>18)&0x7)|0x0f0, (val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x3ffffff:
		return bytearray([((val>>24)&0x3)|0x0f8, (val>>18)&0x3f, (val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x7fffffff:
		return bytearray([((val>>30)&0x1)|0x0fc, (val>>24)&0x3f, (val>>18)&0x3f, (val>>12)&0x3f,
			(val>>6)&0x3f, val&0x3f])
	elif val <= 0x0fffffffffL:
		return bytearray([0x0fe, (val>>30)&0x3f, (val>>24)&0x3f, (val>>18)&0x3f, (val>>12)&0x3f,
			(val>>6)&0x3f, val&0x3f])
	elif val <= 0x03ffffffffffL:
		return bytearray([0x0ff, (val>>36)&0x3f, (val>>30)&0x3f, (val>>24)&0x3f, (val>>18)&0x3f,
			(val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	else:
		raise ValueError('value too high to encode: %d', val)

def utfIn(strm, idx = 0):
	lead = strm[idx]
	if (lead & 0x080) == 0:
		return (int(lead), 1)
	elif (lead & 0x0e0) == 0x0c0:
		return (int(lead&0x1f)<<6 | strm[idx+1]&0x3f, 2)
	elif (lead & 0x0f0) == 0x0e0:
		return (int(lead&0x0f)<<12 | int(strm[idx+1]&0x3f)<<6 | strm[idx+2]&0x3f, 3)
	elif (lead & 0x0f8) == 0x0f0:
		return (int(lead&0x7)<<18 | int(strm[idx+1]&0x3f)<<12 | int(strm[idx+2]&0x3f)<<6 | strm[idx+3]&0x3f, 4)
	elif (lead & 0x0fc) == 0x0f8:
		return (int(lead&0x3)<<24 | int(strm[idx+1]&0x3f)<<18 | int(strm[idx+2]&0x3f)<<12 |
			int(strm[idx+3]&0x3f)<<6 | strm[idx+4]&0x3f, 5)
	elif (lead & 0x0fe) == 0x0fc:
		return (int(lead&0x1)<<30 | int(strm[idx+1]&0x3f)<<24 | int(strm[idx+2]&0x3f)<<18 |
			int(strm[idx+3]&0x3f)<<12 | int(strm[idx+4]&0x3f)<<6 | strm[idx+5]&0x3f, 6)
	elif lead == 0x0fe:
		return (long(strm[idx+1]&0x3f)<<30 | int(strm[idx+2]&0x3f)<<24 | int(strm[idx+3]&0x3f)<<18 |
			int(strm[idx+4]&0x3f)<<12 | int(strm[idx+5]&0x3f)<<6 | strm[idx+6]&0x3f, 7)
	elif lead == 0x0ff:
		return (long(strm[idx+1]&0x3f)<<36 | long(strm[idx+2]&0x3f)<<30 | int(strm[idx+3]&0x3f)<<24 |
			int(strm[idx+4]&0x3f)<<18 | int(strm[idx+5]&0x3f)<<12 | int(strm[idx+6]&0x3f)<<6 |
			strm[idx+7]&0x3f, 8)
	else:
		raise ValueError('unexpected lead byte %d' % lead)

def utfLen(lead):
	if (lead & 0x080) == 0:
		return 1
	elif (lead & 0x0e0) == 0x0c0:
		return 2
	elif (lead & 0x0f0) == 0x0e0:
		return 3
	elif (lead & 0x0f8) == 0x0f0:
		return 4
	elif (lead & 0x0fc) == 0x0f8:
		return 5
	elif (lead & 0x0fe) == 0x0fc:
		return 6
	elif lead == 0x0fe:
		return 7
	elif lead == 0x0ff:
		return 8
	else:
		raise ValueError('unexpected lead byte %d' % lead)

class Sdxf2Generator(object):
	class Chunk(object):
		def __init__(self, id):
			self.id = id
			self.prev = None
			self.content = bytearray()
	
	def __init__(self):
		self.current = self.Chunk(-1)
		self.content = self.current.content
	
	def create(self, id, val):
		if isinstance(val, unicode):
			self.createImpl(id, 6, val.encode('utf8'))
		elif isinstance(val, (int, long)):
			self.createImpl(id, 3, self.int2binary(val))
		elif isinstance(val, float):
			self.createImpl(id, 5, bytearray(struct.pack('d', val)))
		elif isinstance(val, bytearray):
			self.createImpl(id, 2, val)
		elif isinstance(val, (tuple, list)):
			if len(val) == 0:
				self.createImpl(id, 2, utfOut(0), 2)
			else:
				typ = type(val[0])
				for elem in val:
					if type(elem) != typ:
						raise ValueError('Arrays must be of the same type (%s != %s)' % (typ, type(elem)))
				enc = bytearray([utfOut(len(val))])
				code = 0
				if isinstance(val[0], (int, long)):
					code = 3
					elemlen = 0
					for elem in val:
						mylen = len(self.int2binary(elem))
						if mylen > elemlen:
							elemlen = mylen
					for elem in val:
						enc.extend(self.int2binary(elem, elemlen))
				elif isinstance(val[0], float):
					code = 5
					for elem in val:
						enc.extend(bytearray(struct.pack('d', elem)))
				elif isinstance(val[0], bytearray):
					elemlen = len(val[0])
					for elem in val:
						if len(elem) != elemlen:
							raise ValueError('Array elements cannot differ in length')
						enc.extend(elem)
				else:
					raise NotImplementedError('This type is not supported for arrays')
				self.createImpl(id, code, enc, 2)
			
		else:
			raise ValueError('unexpected type %s' % type(val))
	
	def int2binary(self, val, minLen = 1):
		remain = val
		enc = bytearray()
		while len(enc)<minLen or ((remain != 0 and remain != -1) or ((enc[-1]&0x080!=0) != (remain < 0))):
			enc.append(remain & 0x0ff)
			remain >>= 8
		enc.reverse()
		return enc
	
	def enterChunk(self, id):
		if id < 0:
			raise ValueError('negative values not permitted here: %d', id)
		newChunk = self.Chunk(id)
		newChunk.prev = self.current
		self.current = newChunk
		pass
	
	def leaveChunk(self):
		if not(self.current.prev):
			raise Exception('Cannot leave outermost chunk')
		child = self.current
		self.current = child.prev
		self.createImpl(child.id, 1, child.content)
	
	def createImpl(self, id, typ, val, flags = 0):
		self.send(utfOut(id))
		if len(val) == 1:
			self.send([(typ << 5) | flags | 4])
			self.send(val)
		else:
			self.send([(typ << 5) | flags])
			self.send(utfOut(len(val)))
			self.send(val)
	
	def send(self, data):
		self.current.content.extend(data)
	
	def from_dict(self, src, id = -1):
		if id != -1:
			self.enterChunk(id)
		for key in src:
			val = src[key]
			key = long(key)
			if isinstance(val, dict):
				self.from_dict(val, key)
			elif not(val is None):
				self.create(key, val)
		if id != -1:
			self.leaveChunk()

class Sdxf2Parser(object):
	class Chunk(object):
		def __init__(self):
			self.id = 0
			self.prev = None
			self.type = 0
			self.flags = 0
			self.size = 0
			self.startoff = 0
			self.val = None
	
	def __init__(self, content):
		self.current = self.Chunk()
		self.nextChunk = None
		self.content = content
		self.current.size = len(content)
		self.idx = 0
	
	def next(self):
		if self.nextChunk:
			self.idx = self.nextChunk.startoff + self.nextChunk.size
		if self.idx >= self.current.startoff + self.current.size or self.idx >= len(self.content):
			return None
		next = self.nextChunk = self.getChunk()
		next.prev = self.current
		
		if next.type == 1:
			pass # handle children elsewhere
		elif next.flags & 2:
			numElem = self.recvNum()
			next.val = []
			if numElem:
				result = next.val
				elemSize = (next.size - self.idx + next.startoff) / numElem
				for idx in range(0, numElem-1):
					if next.type == 2:
						result.append(self.recv(elemSize))
					elif next.type == 3:
						result.push(self.binary2int(self.recv(elemSize)))
					elif next.type == 5:
						raw = self.recv(elemSize)
						if next.size == 8:
							result.push(struct.unpack('d', raw)[0])
						if next.size == 4:
							result.push(struct.unpack('f', raw)[0])
						else:
							raise NotImplementedError('Unsupported floating point size %d' % next.size)
					else:
						raise NotImplementedError('This type is not supported for arrays')
		elif next.type == 2:
			next.val = self.recv(next.size)
		elif next.type == 3:
			next.val = self.binary2int(self.recv(next.size))
		elif next.type == 4:
			next.val = self.recv(next.size).decode('latin1')
		elif next.type == 5:
			raw = self.recv(next.size)
			if next.size == 8:
				next.val = struct.unpack('d', raw)[0]
			elif next.size == 4:
				next.val = struct.unpack('f', raw)[0]
			else:
				raise NotImplementedError('Unsupported floating point size %d' % next.size)
		elif next.type == 6:
			next.val = self.recv(next.size).decode('utf-8')
		else:
			raise ValueError('unexpected type %d' % next.type)
		return next
	
	def binary2int(self, src):
		lead = src[0]
		result = -1 if (lead & 0x80) else 0
		for idx in range(0, len(src)):
			if idx == 4:
				result = long(result)
			result = ((result << 8) & ~0x0ff) | src[idx]
		return result
	
	def enterChunk(self):
		if not self.nextChunk:
			raise ValueError('no current node available to enter')
		if self.nextChunk.type != 1:
			raise ValueError('current node is not a subchunk and cannot be entered')
		self.current = self.nextChunk
		self.idx = self.current.startoff
		self.nextChunk = None
	
	def leaveChunk(self):
		if not(self.current.prev):
			raise Exception('Cannot leave outermost chunk')
		child = self.current
		self.current = child.prev
		self.idx = child.startoff + child.size
	
	def getChunk(self):
		c = self.Chunk()
		c.id = self.recvNum()
		flagtype = self.recv(1)[0]
		c.type = flagtype >> 5
		c.flags = flagtype & 0x1f
		if c.flags & 4:
			c.size = 1
		else:
			c.size = self.recvNum()
		c.startoff = self.idx
		return c
	
	def recvNum(self):
		result = self.recv(1)
		numlen = utfLen(result[0])
		if numlen > 1:
			result.extend(self.recv(numlen-1))
		return utfIn(result)[0]
	
	def recv(self, num):
		if num == 1:
			result = [self.content[self.idx]]
		else:
			result = self.content[self.idx:self.idx+num]
		self.idx += len(result)
		return result
	
	def to_dict(self):
		result = {}
		here = self.next()
		while here:
			if here.type == 1:
				self.enterChunk()
				result[here.id] = self.to_dict()
				self.leaveChunk()
			else:
				result[here.id] = here.val
			here = self.next()
		return result

class Sdxf2TextGenerator(object):
	def __init__(self):
		self.generator = Sdxf2Generator()
		self.content = self.generator.content
	
	def from_dict(self, *args):
		keys = {}
		count = { 'val': 1 }
		for src in args:
			self.gather_keys(src, keys, count)
		self.dump_keys(keys)
		for src in args:
			self.dump_dict(src, keys)
	
	def gather_keys(self, src, keys, count, name = None):
		for key in src:
			val = src[key]
			if isinstance(val, dict):
				if not(key in keys):
					keys[key] = count['val'];
					count['val'] += 1;
				self.gather_keys(val, keys, count, key)
			else:
				fullKey = name + '/' + key if name else key
				if not(fullKey in keys):
					keys[fullKey] = count['val'];
					count['val'] += 1;
	
	def dump_keys(self, keys):
		node = None
		generator = self.generator
		generator.enterChunk(0)
		for key in sorted(keys):
			val = keys[key]
			if isinstance(key,basestring) and '/' in key:
				(thisNode, subkey) = key.split('/', 2)
				if thisNode != node and node:
					generator.leaveChunk()
			else:
				subkey = key
				thisNode = None
				if node:
					generator.leaveChunk()
			if thisNode != node and thisNode:
				generator.enterChunk(keys[thisNode])
			generator.create(val, subkey)
			node = thisNode
		if node:
			generator.leaveChunk()
		generator.leaveChunk()
	
	def dump_dict(self, src, keys, name = None):
		for key in src:
			val = src[key]
			self.dump_val(key, val, keys, name)
	
	def dump_val(self, key, val, keys, name = None):
		generator = self.generator
		if isinstance(val, dict):
			generator.enterChunk(keys[key])
			self.dump_dict(val, keys, key)
			generator.leaveChunk()
		elif isinstance(val, (tuple, list)):
			fullKey = key + '/' + name if name else key
			keyId = keys[fullKey]
			try:
				generator.create(keyId, val)
			except ValueError:
				if len(val) < 2:
					generator.create(keyId, [])
				for elemVal in val:
					self.dump_val(key, elemVal, keys, name)
		elif not(val is None):
			fullKey = name + '/' + key if name else key
			generator.create(keys[fullKey], val)

class Sdxf2TextParser(object):
	def __init__(self, content):
		self.parser = Sdxf2Parser(content)
	
	def to_dict(self, keys = None):
		if not keys:
			keys = {}
		result = {}
		parser = self.parser
		here = parser.next()
		while here:
			key = keys.get(here.id, here.id)
			val = None
			if here.type == 1:
				parser.enterChunk()
				if here.id == 0:
					keys = self.fetch_keys()
				else:
					val = self.to_dict(keys)
				parser.leaveChunk()
			else:
				val = here.val
			if not(val is None):
				if key in result:
					if not isinstance(result[key], list):
						result[key] = [result[key]]
					result[key].append(val)
				else:
					result[key] = val
			here = parser.next()
		return result
	
	def fetch_keys(self):
		result = {}
		parser = self.parser
		here = parser.next()
		while here:
			if here.type == 1:
				parser.enterChunk()
				# we're not dealing with elements and attributes differently here
				child = parser.next()
				while child:
					result[child.id] = child.val
					child = parser.next()
				parser.leaveChunk()
			else:
				result[here.id] = here.val
			here = parser.next()
		return result

def encode(*src):
	gen = Sdxf2TextGenerator()
	gen.from_dict(*src)
	return gen.content

def decode(src):
	parser = Sdxf2TextParser(src)
	return parser.to_dict()

if __name__ == '__main__':
	from pprint import pprint
	#test = utfOut(0xfff)
	#pprint(len(test))
	#pprint(list(test))
	#pprint(utfIn(test))
	test_in = {
		5: 'one',
		'two': ('hi', 'you', -5563701247),
		'three': { 'my': 14.2, 'you': 'hi there' },
		'four': None
	}
	gen = Sdxf2TextGenerator()
	gen.from_dict(test_in)
	enc = gen.content
	parser = Sdxf2TextParser(enc)
	pprint('------------')
	test_out = parser.to_dict()
	pprint((len(enc),enc))
	pprint(test_out)
