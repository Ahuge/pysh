#!/usr/bin/python

import os
import argparse
import tempfile
import sys

try:
    from contextlib import redirect_stdout
except ImportError:
    class redirect_stdout(object):
        _stream = "stdout"

        def __init__(self, new_target):
            super(redirect_stdout, self).__init__()
            self._new_target = new_target
            self._old_targets = []

        def __enter__(self):
            self._old_targets.append(getattr(sys, self._stream))
            setattr(sys, self._stream, self._new_target)
            return self._new_target

        def __exit__(self, exctype, excinst, exctb):
            setattr(sys, self._stream, self._old_targets.pop())

parser = argparse.ArgumentParser(description="Run python-enhanced bash scripts")
parser.add_argument("script", action="store",
                    help="filename of python-enhanced bash script")
parser.add_argument("-d", "--debug", action="store_true",
                    help="Only show the generated bash script, without execution")

args = parser.parse_args()

script = args.script
shell = "/bin/bash"

# Divide the input script into 'bash' and 'python' blocks.
blocks = []
block = []
lastType = "bash"

with open(script) as fIn:
    for line in fIn.readlines():
        if line.strip().startswith("#> "):
            lineType = "python"
        else:
            lineType = "bash"

        if lineType == lastType:
            block.append(line)
        else:
            # block ends here
            blocks.append((lastType, block))

            # start new block
            block = [line]

        lastType = lineType

    # append last block
    blocks.append((lineType, block))

# Create a temporary file for exchanging variable from python back to bash
envFile = tempfile.NamedTemporaryFile("wt", delete=False)
envFile.close()

with tempfile.NamedTemporaryFile("wt", delete=False) as outFile:
    with redirect_stdout(outFile):
        print("#!{shell}".format(shell=shell))
        print("set -o allexport")
        print("")
        for bType, lines in blocks:
            if bType == "python":
                print("python <<EOF")
                print("import os")
                print("import sys")
                print("for k, v in os.environ.items():")
                print("    locals()[k] = v")
                print("")
                lines = [line.strip()[3:].replace("$", "\\$") for line in lines]
                print("\n".join(lines))
                print("pyEnv = {k: v for k, v in locals().items()}")
                print("")
                print('with open("{envFile}", "w") as f:'.format(envFile=envFile.name))
                print("    for k, v in pyEnv.items():")
                print("        if 'BASH_FUNC' in k:")
                print("            continue")
                print("        if type(v) in [str, int, float, bool]:")
                print("            val = str(v).replace('\"', '\\\\\\\"')")
                print("            val = val.replace('$', '\\\\$')")
                print("            f.write('{k}=\"{val}\"\\n'.format(k=k, val=val))")
                print("EOF")
                print("source '{envFile}'".format(envFile=envFile.name))
            else:
                print("".join(lines))

if args.debug:
    os.system("cat '{script}'".format(script=outFile.name))
else:
    os.system("{shell} '{script}'".format(shell=shell, script=outFile.name))
os.remove(outFile.name)
os.remove(envFile.name)
