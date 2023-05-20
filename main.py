#!/usr/bin/env python3
import threading
import os
import time
import signal
import subprocess

proc: subprocess.Popen = None
prompt = ""
terminated = False
prompts = (
    "To grant access to the server",
    "Open this link in your browser"
)


class ThreadRunner:
    def __init__(self) -> None:
        self.threading = None
        self.running = False

    def start(self):
        if self.threading != None:
            return
        self.running = True
        self.threading = threading.Thread(target=self.runnable)
        self.threading.setDaemon(True)
        self.threading.start()

    def stop(self):
        if self.threading == None:
            return
        self.running = False
        self.threading.join()
        self.threading = None

    def runnable(self):
        raise NotImplementedError


class MessageRepeater(ThreadRunner):
    def __init__(self, interval) -> None:
        super().__init__()
        self.prompt = ""
        self.interval = interval

    def set_prompt(self, prompt):
        self.prompt = prompt

    def runnable(self):
        while self.running:
            if self.prompt != "":
                print(self.prompt)
            time.sleep(self.interval)


class FileExistanceListener(ThreadRunner):
    def __init__(self, filename, interval, callback) -> None:
        super().__init__()
        self.filename = filename
        self.interval = interval
        self.callback = callback

    def runnable(self):
        while self.running and not os.path.exists(self.filename):
            time.sleep(self.interval)
        if os.path.exists(self.filename):
            self.callback()
        while self.running:
            time.sleep(self.interval)


def main():
    global proc
    global prompt
    global terminated

    repreater = MessageRepeater(2)
    repreater.start()

    name = os.environ.get("GITHUB_RUN_ID", "") + "-" + \
        os.environ.get("GITHUB_RUN_NUMBER", "")
    proc = subprocess.Popen(
        ["code-server", "--accept-server-license-terms",
         "rename", "--name", name],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while True:
        data = proc.stdout.readline()
        if data == b"" and proc.poll() is not None:
            break
        line = data.decode('ascii').rstrip()
        print(line)
        if line.startswith(prompts):
            repreater.set_prompt(line)

    proc.wait()
    repreater.stop()
    repreater.start()

    proc = subprocess.Popen(
        ["code-server", "--accept-server-license-terms"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    listener = FileExistanceListener("/tmp/exit_marker", 10,
                                     lambda: proc.send_signal(signal.SIGINT))
    listener.start()

    while True:
        data = proc.stdout.readline()
        if data == b"" and proc.poll() is not None:
            break
        line = data.decode('ascii').rstrip()
        print(line)
        if line.startswith(prompts):
            repreater.set_prompt(line)

    proc.wait()
    listener.stop()
    repreater.stop()


if __name__ == "__main__":
    main()
