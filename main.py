#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

import tinify

from MD5Mgr import MD5Mgr


TinyKeys = [
    'lJcr96FHq74Dt4KY7K0SnSsLwzzZg0Z9',
    'FmnXgPcNy8CYvjYpwJDXCBS9bykcsGzW',
    'Q8Pzzrwtlpptlc3hthyXTmTjyK4txQZc',
    'Q8Pzzrwtlpptlc3hthyXTmTjyK4txQZc'
]

needRemoveList = []
needRefreshList = []
refreshSucceedList = []
refreshFailList = []
avaImageSetList = []

# 多线程终止符
exitFlag = 0

canExecution = False
finishCount = 0

threadLock = threading.Lock()
queueLock = threading.Lock()
workQueue = queue.Queue()
threads = []


class WorkThread(threading.Thread):
    def __init__(self, threadId, name, q):
        threading.Thread.__init__(self)
        self.threadId = threadId
        self.name = name
        self.q = q

    def run(self) -> None:
        process_data(self.name, self.q)


def process_data(threadName, q):
    global exitFlag
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            path = q.get()
            queueLock.release()
            tinySlimImage(path)
            threadLock.acquire()
            printProcess(threadName)
            threadLock.release()
        else:
            queueLock.release()
        time.sleep(0.1)


def printProcess(threadName):
    global finishCount
    finishCount += 1
    count = len(needRefreshList)
    process = '%0.2f' % (finishCount / count * 100)
    print(f'总共{count},当前{finishCount},进度{process}%,完成线程:{threadName}')


def checkImageset(path):
    if 'imageset' == path[-8:]:
        with open(os.path.join(path, 'Contents.json'), 'r') as f:
            avaImageSetList.append(path)
            config = json.loads(f.read())
            dirs = os.listdir(path)
            images = config['images']
            image1x = None
            canDelete = False
            for im in images:
                filename = im.get('filename')
                if filename:
                    if im['scale'] == '1x':
                        image1x = im
                    else:
                        canDelete = True
                        dirs.remove(filename)
                        needRefreshList.append(os.path.join(path, filename))

            # 当仅有1x图时候 忽略
            if image1x and image1x.get('filename'):
                if canDelete:
                    del image1x['filename']
                else:
                    dirs.remove(image1x['filename'])
                    needRefreshList.append(os.path.join(path, image1x['filename']))

            # 关闭文件
            f.close()

            # 将文件回写回去
            if canExecution:
                with open(os.path.join(path, 'Contents.json'), 'w', encoding='UTF-8') as wf:
                    text = json.dumps(config)
                    wf.write(text)
                    wf.close()

            # 移除json 检索需要删除的文件
            dirs.remove('Contents.json')
            for file in dirs:
                needRemoveList.append(os.path.join(path, file))
            # print(config['images'])
    else:
        ergodicDirs(path, checkImageset)


def ergodicDirs(path, func):
    dirs = os.listdir(path)
    for file in dirs:
        currentPath = os.path.join(path, file)
        currentPathObj = Path(currentPath)
        if currentPathObj.is_dir():
            if func:
                func(currentPath)
        elif currentPathObj.is_file():
            if file != 'Contents.json':
                print(f'ignore file : {currentPath}')


def removeList():
    with open('logs/'+time.strftime("%m-%d_%H:%M:%S", time.localtime()) + '_del.txt', 'w', encoding='UTF-8') as f:
        f.write('\n'.join(needRemoveList))

    if canExecution:
        for file in needRemoveList:
            filePath = Path(file)
            if filePath.is_file():
                os.remove(file)
            else:
                print(f'未删除的目录:{file}')


def slimImageList():
    print(needRefreshList)


def clear1XImage(path):
    global canExecution
    canExecution = True
    ergodicDirs(path, checkImageset)
    removeList()


def slimImage(path):
    ergodicDirs(path, checkImageset)

    count = len(needRefreshList)

    for i in range(0, 10):
        thread = WorkThread(i + 1, f'Thread-{i}', workQueue)
        thread.start()
        threads.append(thread)

    # 填充队列
    queueLock.acquire()
    for i in range(0, count):
        print(f'载入数据{i + 1},进度{(i + 1) / count}')
        file = needRefreshList[i]
        # tinySlimImage(file)
        workQueue.put(file)
    queueLock.release()

    while not workQueue.empty():
        pass

    # 通知线程是时候退出
    global exitFlag
    exitFlag = 1

    for t in threads:
        t.join()

    print('任务完成')


def tinySlimImage(path):
    fileMD5 = hashlib.md5(open(path, 'rb').read()).hexdigest()
    if md5Manager.findMD5(fileMD5):
        return
    if len(TinyKeys) == 0:
        global exitFlag
        exitFlag = 1
        raise Exception('无有效的TinyKey')

    key = TinyKeys[0]

    try:
        tinify.key = key
        # tinify.proxy = "http://127.0.0.1:1087"

        source = tinify.from_file(path)
        source.to_file(path)
        refreshSucceedList.append(path)
        md5Manager.writeFile(hashlib.md5(open(path, 'rb').read()).hexdigest())

    except tinify.errors.AccountError:
        print(f'{key} 已超额')
        TinyKeys.remove(key)
        tinySlimImage(path)
    except BaseException as e:
        print('some error' + e)
        refreshFailList.append(path)


if __name__ == '__main__':

    # print(len(sys.argv),sys.argv)
    if len(sys.argv) != 4:
        print(
            '''
            请传入正确参数.
            python3 main.py 工程目录 xcassets名称 模式(1 清除1x图 2 压缩图片)
            
            ex: python3 main.py "~/Desktop/workCode/iOSCode" "Images" 1
            
            ''')
    else:
        workspacePath = sys.argv[1]
        imageXcassetsName = sys.argv[2] + '.xcassets'
        imageXcassetsPath = f'{workspacePath}/{imageXcassetsName}'
        md5Manager = MD5Mgr()
        mode = int(sys.argv[3])
        if mode == 1:
            print('启动清除1x模式')
            time.sleep(2)
            clear1XImage(imageXcassetsPath)
        elif mode == 2:
            print('启动压缩模式')
            time.sleep(2)
            if len(TinyKeys) == 0:
                print('无有效的TinyKey')
            else:
                slimImage(imageXcassetsPath)

# TinyKey
# lJcr96FHq74Dt4KY7K0SnSsLwzzZg0Z9
# FmnXgPcNy8CYvjYpwJDXCBS9bykcsGzW test
# Q8Pzzrwtlpptlc3hthyXTmTjyK4txQZc test2
# 7ngVLwtXvhtbk0j2hhGbLChWJyVYLVVw test3
#
