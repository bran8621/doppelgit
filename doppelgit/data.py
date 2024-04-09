import os
import hashlib

GIT_DIR = '.doppelgit'

def init():

    os.makedirs(GIT_DIR)
    os.makedirs(f'{GIT_DIR}/objects')

def hash_object(data, type = 'blob'):
    object = type.encode() + b'\x00' + data
    oid = hashlib.sha1(object).hexdigest()
    with open(f'{GIT_DIR}/objects/{oid}', 'wb') as f:
        f.write(object)
    return oid

def get_object(oid, expected = 'blob'):
    with open(f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        object = f.read()
    
    type_, _, content = object.partition(b'\x00')
    type_ = type_.decode()

    if expected is not None:
        assert type_ == expected, f'Expected {expected} but got {type_}'
    return content


