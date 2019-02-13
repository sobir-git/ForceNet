from my_subprocess import subprocess_args  # For safety in freeze mode
import subprocess  # For executing a shell command


class Pinger:
    '''A class for periodically pinging host and counting the number
    of failures.
    '''
    def __init__(self, host, max_failures, timeout=3, count=1):
        self._failures = 0
        self.max_failures = max_failures
        self.host = host
        self.timeout = timeout
        self.count = count

    def get_freeze(self):
        '''Ping the host and return True(freeze) or False(unfreeze) according
        to number of failures.
        '''
        result = ping(self.host, count=self.count, timeout=self.timeout)
        print(f"pinging {self.host}: {result}")

        if result:
            self._failures = 0
        else:
            self._failures += 1

        return self._get_freeze()

    def _get_freeze(self):
        '''Decide the block'''
        return self._failures > self.max_failures


def ping(host, count, timeout):
    '''Ping a host and return True if sucess else False
    '''
    command = ['ping', '-n', str(count), host]
    try:
        output = subprocess.check_output(
                command, **subprocess_args(include_stdout=False))
    except Exception as e:
        return False

    zero_loss = "(0% loss)" in output.decode()
    unreachable = "unreachable" in output.decode()
    result = zero_loss and not unreachable
    return result

