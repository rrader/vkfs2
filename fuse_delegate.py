from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from stat import S_IFDIR, S_IFLNK, S_IFREG
from errno import ENOENT, EPERM
from time import time
import urllib


## FILESYSTEM CORE
def recursive(m):
    def _recursive(self, parts, *args, **kwargs):
        if len(parts) == 1:
            if parts[0] == self.name:
                return m(self, parts, *args, **kwargs)
            else:
                raise FuseOSError(ENOENT)
        else:
            if parts[1] in self.struct:
                sub_method = getattr(self.struct[parts[1]], m.__name__)
                return sub_method(parts[1:], *args, **kwargs)
            else:
                raise FuseOSError(ENOENT)
    return _recursive


class PathResolver(object):
    def __init__(self, name, vk):
        self.vk = vk
        self.name = name
        self.struct = {
        }

    @recursive
    def getattr(self, parts):
        raise FuseOSError(EPERM)

    @recursive
    def ls(self, parts):
        return list(filter(None, self.struct.keys()))

    @recursive
    def read(self, parts, size, offset, fh):
        raise FuseOSError(EPERM)

    @recursive
    def release(self, parts, fh):
        pass

    @recursive
    def open(self, parts, fh):
        pass

    @recursive
    def getattr(self, parts):
        return dict(st_mode=(S_IFDIR | 0o755), st_ctime=time(),
                    st_mtime=time(), st_atime=time(), st_nlink=1)


class FileResolver(PathResolver):
    def __init__(self, name, vk):
        super().__init__(name, vk)
        self._content = ''

    def read(self, parts, size, offset, fh):
        return self.content()[offset:offset + size]

    def content(self):
        return self._content

    def getattr(self, parts):
        return dict(st_mode=(S_IFREG | 0o755), st_ctime=time(),
                         st_mtime=time(), st_atime=time(), st_nlink=1,
                         st_size=len(self.content()))


class RootPathResolver(PathResolver):
    def __init__(self, vk):
        super().__init__('', vk)
        self.struct.update({
            '': self,
            'profile': ProfileFileResolver('profile', vk),
            'MyAudio': MyAudioResolver('MyAudio', vk)
        })

    @recursive
    def getattr(self, parts):
        return dict(st_mode=(S_IFDIR | 0o755), st_ctime=time(),
                    st_mtime=time(), st_atime=time(), st_nlink=2)


class FuseDelegate(LoggingMixIn, Operations):
    def __init__(self, vkdelegate):
        self.vk = vkdelegate
        self.resolver = RootPathResolver(vkdelegate)
        self.fd = 0

    def getattr(self, path, fh=None):
        parts = path.split('/')
        return self.resolver.getattr(parts)

    def readdir(self, path, fh):
        parts = path.split('/')
        return ['.', '..'] + self.resolver.ls(parts)

    def open(self, path, flags):
        self.fd += 1
        parts = path.split('/')
        self.resolver.open(parts, self.fd)
        return self.fd

    def release(self, path, fh):
        print("RELEASE ",fh)
        parts = path.split('/')
        self.resolver.release(parts, fh)

    def read(self, path, size, offset, fh):
        parts = path.split('/')
        return self.resolver.read(parts, size, offset, fh) # self.data[path][offset:offset + size]

## / FILESYSTEM CORE /

class ProfileFileResolver(FileResolver):
    def __init__(self, name, vk):
        super().__init__(name, vk)
        self._content = None

    def read(self, parts, size, offset, fh):
        return self.content()[offset:offset + size]

    def content(self):
        if not self._content:
            profile = self.vk.profile()
            self._content = bytes('\n'.join('%s: %s' % (key,value) for key,value in profile.items()) + '\n', 'UTF-8')

        return self._content


class MyAudioResolver(PathResolver):
    def __init__(self, name, vk):
        super().__init__(name, vk)
        self._audios = None
        self._files = {}

    @recursive
    def ls(self, parts):
        return list(self.audios().keys())

    def audios(self):
        if not self._audios:
            self._audios = {"{}-{}-{}.mp3".format(audio['artist'], audio['title'], audio['id']):audio
                            for audio in self.vk.my_audio_files()}
        return self._audios

    def getattr(self, parts):
        if len(parts) == 1:
            if parts[0] == self.name:
                return dict(st_mode=(S_IFDIR | 0o755), st_ctime=time(),
                            st_mtime=time(), st_atime=time(), st_nlink=1)
            else:
                raise FuseOSError(ENOENT)
        else:
            if parts[1] in self.audios():
                size = self.get_size(parts[1])
                return dict(st_mode=(S_IFREG | 0o755), st_ctime=time(),
                            st_mtime=time(), st_atime=time(), st_nlink=1,
                            st_size=size)
            else:
                raise FuseOSError(ENOENT)

    def get_size(self, name):
        audio = self.audios()[name]
        if 'size' not in audio:
            print('retrieving size of %s' % name)
            audio["size"] = 1000*1024*1024
            # with urllib.request.urlopen(audio['url']) as request:
            #     audio['size'] = int(request.info()['Content-Length'])
        return audio['size']

    def read(self, parts, size, offset, fh):
        print("READ",size,offset)
        audio = self.audios()[parts[1]]
        request = self._files[fh]["request"]
        while len(self._files[fh]["content"]) < offset + size:
            read_ = request.read(1000*1024)
            if not read_:
                break
            print("chunk loaded")
            self._files[fh]["content"] += read_

        data = self._files[fh]["content"]
        return data[offset:offset + size]

    def open(self, parts, fh):
        print("OPEN",parts[1])
        audio = self.audios()[parts[1]]
        if fh not in self._files:
            request = urllib.request.urlopen(audio['url'])
            self._audios[parts[1]]['size'] = int(request.info()['Content-Length'])
            self._files[fh] = {"content": b'', "request": request}

    def release(self, parts, fh):
        if fh in self._files:
            del self._files[fh]


class FuseController(object):
    def __init__(self, mountpoint, vkdelegate=None):
        self.mountpoint = mountpoint
        self.vkdelegate = vkdelegate
    
    def mount(self):
        self.fuse = FUSE(FuseDelegate(self.vkdelegate), self.mountpoint, foreground=True)
