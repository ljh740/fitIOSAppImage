import os
from pathlib import Path

__all__ = [
    "MD5Mgr",
    ]

class MD5Mgr():
    def __init__(self):
        self.path = os.path.abspath(os.path.dirname(__file__))+'/finishMd5.txt'
        self.localList = []
        self.initFile()

    def initFile(self):
        if not Path(self.path).is_file():
            with open(self.path, 'w+') as f:
                f.write('#MD5 file\n')
                f.close()

        self.readFile()

    def readFile(self):
        with open(self.path,'r') as f:
            strValue = f.read()
            self.localList = strValue.split('\n')
            f.close()

    def writeFile(self,md5Str):
        with open(self.path,'a') as f:
            f.write(md5Str+'\n')
            self.localList.append(md5Str)

    def findMD5(self,md5Str):
        return md5Str in self.localList
