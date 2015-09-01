# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals

def utfOut(val):
	if val < 0:
		raise ValueError('negative values not permitted here: %d', val)
	elif val <= 0x7f:
		return bytearray([val])
	elif val <= 0x7ff:
		return bytearray([((val>>6)&0x1f)|0xc0, val&0x3f])
	elif val <= 0xffff:
		return bytearray([((val>>12)&0xf)|0xe0, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x1fffff:
		return bytearray([((val>>18)&0x7)|0xf0, (val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x3ffffff:
		return bytearray([((val>>24)&0x3)|0xf8, (val>>18)&0x3f, (val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	elif val <= 0x7fffffff:
		return bytearray([((val>>30)&0x1)|0xfc, (val>>24)&0x3f, (val>>18)&0x3f, (val>>12)&0x3f,
			(val>>6)&0x3f, val&0x3f])
	elif val <= 0xfffffffffL:
		return bytearray([0xfe, (val>>30)&0x3f, (val>>24)&0x3f, (val>>18)&0x3f, (val>>12)&0x3f,
			(val>>6)&0x3f, val&0x3f])
	elif val <= 0x3ffffffffffL:
		return bytearray([0xff, (val>>36)&0x3f, (val>>30)&0x3f, (val>>24)&0x3f, (val>>18)&0x3f,
			(val>>12)&0x3f, (val>>6)&0x3f, val&0x3f])
	else:
		raise ValueError('value too high to encode: %d', val)

def utfIn(strm, idx = 0):
	lead = strm[idx]
	if (lead & 0x80) == 0:
		return (int(lead), 1)
	elif (lead & 0xe0) == 0xc0:
		return (int(lead&0x1f)<<6 | strm[idx+1]&0x3f, 2)
	elif (lead & 0xf0) == 0xe0:
		return (int(lead&0xf)<<12 | int(strm[idx+1]&0x3f)<<6 | strm[idx+2]&0x3f, 3)
	elif (lead & 0xf8) == 0xf0:
		return (int(lead&0x7)<<18 | int(strm[idx+1]&0x3f)<<12 | int(strm[idx+2]&0x3f)<<6 | strm[idx+3]&0x3f, 4)
	elif (lead & 0xfc) == 0xf8:
		return (int(lead&0x3)<<24 | int(strm[idx+1]&0x3f)<<18 | int(strm[idx+2]&0x3f)<<12 |
			int(strm[idx+3]&0x3f)<<6 | strm[idx+4]&0x3f, 5)
	elif (lead & 0xfe) == 0xfc:
		return (int(lead&0x1)<<30 | int(strm[idx+1]&0x3f)<<24 | int(strm[idx+2]&0x3f)<<18 |
			int(strm[idx+3]&0x3f)<<12 | int(strm[idx+4]&0x3f)<<6 | strm[idx+5]&0x3f, 6)
	elif lead == 0xfe:
		return (long(strm[idx+1]&0x3f)<<30 | int(strm[idx+2]&0x3f)<<24 | int(strm[idx+3]&0x3f)<<18 |
			int(strm[idx+4]&0x3f)<<12 | int(strm[idx+5]&0x3f)<<6 | strm[idx+6]&0x3f, 7)
	elif lead == 0xff:
		return (long(strm[idx+1]&0x3f)<<36 | long(strm[idx+2]&0x3f)<<30 | int(strm[idx+3]&0x3f)<<24 |
			int(strm[idx+4]&0x3f)<<18 | int(strm[idx+5]&0x3f)<<12 | int(strm[idx+6]&0x3f)<<6 |
			strm[idx+7]&0x3f, 8)
	else:
		raise ValueError('unexpected lead byte %d' % lead)

class Sdxf2Generator:
	class Chunk:
		def __init__(self, id):
			self.id = id
			self.prev = Empty
			self.content = bytearray()
	
	def __init__(self, id):
		self.current = Chunk(-1)
	
	def create(self, id, val):
		typ = type(val)
		if isinstance(typ, (int, long)):
			self.createImpl(id, 3, self.int2binary(val))
		elif isinstance(typ, float):
			self.createImpl(id, 5, bytearray(pack('d', val)))
		elif isinstance(typ, unicode):
			self.createImpl(id, 6, val.encode('utf8'))
		elif isinstance(typ, bytearray):
			self.createImpl(id, 2, val)
		elif isinstance(typ, (tuple, list)):
			if len(val) == 0:
				self.createImpl(id, 2, utfOut(0), 2)
			else:
				typ = typ(val[0])
				for elem in val:
					if typ(elem) != typ:
						raise ValueError('Arrays must be of the same type')
				enc = bytearray([utfOut(val)])
				code = 0
				if isinstance(val[0], (int, long)):
					code = 3
					len = 0
					for elem in val:
						mylen = len(self.int2binary(elem))
						if mylen > len:
							len = mylen
					for elem in val:
						enc.extend(self.int2binary(elem, len))
				elif isinstance(val[0], float):
					code = 5
					for elem in val:
						enc.extend(bytearray(pack('d', elem)))
				elif isinstance(val[0], bytearray):
					len = len(val[0])
					for elem in val:
						if len(elem) != len:
							raise ValueError('Array elements cannot differ in length')
						enc.extend(elem)
				else:
					raise NotImplementedError('This type is not supported for arrays')
				self.createImpl(id, code, enc, 2)
			
		else:
			raise ValueError('unexpected type %s' % typ)
	
	def int2binary(self, val, minLen = 1):
		remain = val
		enc = bytearray()
		while len(enc)<minLen and ((remain != 0 and remain != -1) or ((enc[-1]&0x80!=0) != (remain < 0))):
			enc.append(remain & 0xff)
			remain >>= 8
		enc.reverse()
		return enc
	
	def from_dict(self, dict, id = -1):
		if id != -1:
			self.enterChunk(id)
		for key in dict:
			val = dict[key]
			key = long(key)
			if isinstance(val, dict):
				self.from_dict(val, key)
			else:
				self.create(key, val)
		if id != -1:
			self.leaveChunk()
	
	def enterChunk(self, id):
		if id < 0:
			raise ValueError('negative values not permitted here: %d', id)
		newChunk = Chunk(id)
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
		self.send([(typ << 5) | flags])
		self.send(utfOut(len(val)))
		self.send(val)
	
	def send(self, data):
		self.currnt.content.extend(data)

if __name__ == '__main__':
	from pprint import pprint
	test = utfOut(0xfff)
	pprint(len(test))
	pprint(list(test))
	pprint(utfIn(test))
