import ctypes

lib = ctypes.CDLL(r".\ase_lib.dll")
lib.encrypt.restype = ctypes.c_char_p
lib.encrypt.argtypes = [ctypes.c_char_p]
lib.decrypt.restype = ctypes.c_char_p
lib.decrypt.argtypes = [ctypes.c_char_p]
lib.setKey.restype = ctypes.c_voidp
lib.setIV.restype = ctypes.c_voidp
lib.setKey.argtypes = [ctypes.c_char_p]
lib.setIV.argtypes = [ctypes.c_char_p]

encrypt = lib.encrypt
decrypt = lib.decrypt
setKey = lib.setKey
setIV = lib.setIV