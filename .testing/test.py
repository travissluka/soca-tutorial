#!/usr/bin/env python3
import argparse
from pathlib import Path
import os
import re
import subprocess
import textwrap
from dataclasses import dataclass, field
from typing import List
import sys


TEST_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TUTORIAL_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))

"""
This script generates a test script from a tutorial markdown file. The script is
used to run the tutorial commands in a CI/CD pipeline.

Commands:
- @test_run  - run a single command, or run the commands in an entire code block
"""
# -------------------------------------------------------------------------------------------------


@dataclass
class Command:
  index: int

class RunCommand(Command):
  RE_MARKDOWN_ARGS = re.compile(r"(cmd|timeout)=(\".*\"|'.*'|\S+)")
  RE_MARKDOWN_RUN = re.compile(r"<!--\s+@test_run\s+(.*)\s*-->")
  RE_MARKDOWN_RUN_BLOCK = re.compile(r"```bash\s+@test_run\s*(.*?)$")

  def __init__(self, cmd, args=None):
    self.cmd = cmd
    self.args = args

  def __str__(self) -> str:
    timeout = ""
    if "timeout" in self.args:
      timeout = f"timeout {self.args['timeout']} "
    return f"(bash) {timeout}{self.cmd}"

  def bash(self) -> str:
    retCode = 0
    timeout = ""
    if "timeout" in self.args:
      retCode = 124
      timeout = f"timeout {self.args['timeout']} "
    return f"cmd=({timeout}{self.cmd}); run_cmd {self.index} {retCode}"

# -------------------------------------------------------------------------------------------------

@dataclass
class SectionInfo:
  level: int
  title: str
  parent: 'SectionInfo' = None
  children: List['SectionInfo'] = field(default_factory=list)
  commands: List[Command] = field(default_factory=list)

  RE_MARKDOWN_HEADER = re.compile(r"^(#{1,6})\s+(.*)\s*")

  def add(self, newSection: 'SectionInfo') -> 'SectionInfo':
    """ Add a new section to the tree"""
    if newSection.level > self.level:
      newSection.parent = self
      self.children.append(newSection)
    elif newSection.level == self.level:
      newSection.parent = self.parent
      self.parent.children.append(newSection)
    elif newSection.level < self.level:
      while newSection.level <= self.level:
        self = self.parent
      newSection.parent = self
      self.children.append(newSection)

    return newSection

  def __str__(self) -> str:
    return f"{'#' * self.level} {self.title}"

  def bash(self) -> str:
    return str(self)

  def flatten(self) -> List['SectionInfo']:
    """ Flatten the tree into a list of sections"""
    sections = [self]
    for c in self.children:
      sections.extend(c.flatten())
    return sections

# -------------------------------------------------------------------------------------------------

def get_physical_cores():
  """ Get the number of physical cores on the system
  note this only works on linux systems
  """
  cores_per_socket = int(os.popen("lscpu | awk '/^Core\\(s\\) per socket:/ {print $4}'").read().strip())
  sockets = int(os.popen("lscpu | awk '/^Socket\\(s\\):/ {print $2}'").read().strip())
  return cores_per_socket * sockets

def consoleBold(msg):
  return f"\033[1m{msg}\033[0m"

def consoleGreen(msg):
  return f"\033[92m{msg}\033[0m"

def consoleYellow(msg):
  return f"\033[93m{msg}\033[0m"

def consoleRed(msg):
  return f"\033[91m{msg}\033[0m"

# -------------------------------------------------------------------------------------------------

def parseMarkdown(markdownFile: str) -> SectionInfo:
  """ Parse a markdown file and return a tree of sections and test commands
  """
  rootSection = None

  # check if the file exists
  markdownFile = Path(markdownFile)
  if not markdownFile.exists():
    raise FileNotFoundError(f"Markdown file {markdownFile} does not exist.")

  # read the input file line by line
  with markdownFile.open('r') as f:
    content = f.read()
    currentSection = None
    in_code_block = False
    codeBlockArgs = []
    for line in content.splitlines():
      # remove block quotes
      line = line.strip().lstrip('>').strip()

      # check for markdown headers
      match = SectionInfo.RE_MARKDOWN_HEADER.match(line)
      if match:
        newSection = SectionInfo(level=len(match.group(1)), title=match.group(2))
        if rootSection is None:
          rootSection = newSection
          currentSection = newSection
        else:
          currentSection = currentSection.add(newSection)
        continue

      # run a single command?
      match = RunCommand.RE_MARKDOWN_RUN.search(line)
      if match:
        runArgs = RunCommand.RE_MARKDOWN_ARGS.findall(match.group(1))
        runArgs = {k: v.strip('"').strip("'") for k, v in runArgs}
        currentSection.commands.append(RunCommand(runArgs["cmd"], runArgs))
        continue

      # start of a code block?
      match = RunCommand.RE_MARKDOWN_RUN_BLOCK.match(line)
      if match:
        codeBlockArgs = RunCommand.RE_MARKDOWN_ARGS.findall(match.group(1))
        codeBlockArgs = {k: v.strip('"').strip("'") for k, v in codeBlockArgs}
        in_code_block = True
        continue

      if in_code_block:
        # end of a code block?
        if line.startswith("```"):
          in_code_block = False
          continue

        # add command
        currentSection.commands.append(RunCommand(line, codeBlockArgs))

  # give all the commands an increasing unique index
  headers = rootSection.flatten()
  cmdCount = 0
  for h in headers:
    for c in h.commands:
      cmdCount += 1
      c.index = cmdCount

  return rootSection

# -------------------------------------------------------------------------------------------------
RUN_HEADER=textwrap.dedent(f"""\
  set -eu

  TEST_SCRIPT_DIR={TEST_SCRIPT_DIR}
  SOCA_TUTORIAL_ROOT={TUTORIAL_ROOT}
  NP={get_physical_cores()}
  LOG_FILE=${{TEST_SCRIPT_DIR}}/tmp/output.log

  mkdir -p $(dirname $LOG_FILE)

  run_cmd() {{
    # wrapper to run a command, log the output, and check the return code
    # note that we pull cmd from a global array, to get around issues with
    # quotes getting messed up when passing the command as a string
    local line_number=$1
    local err_code=$2
    shift 2
    # echo "RUN_CMD line=$line_number cmd=$cmd" >> $LOG_FILE
    echo "RUN_CMD_START line=$line_number"
    "${{cmd[@]}}" >> $LOG_FILE 2>&1 \\
      || (exit_code=$?; [ $exit_code -eq $err_code ] \\
        || (echo "RUN_CMD_ERR line=$line_number exit=$exit_code" && exit 1))
    echo "RUN_CMD_END line=$line_number"
  }}

  #---------------------------------------------
  """)

# -------------------------------------------------------------------------------------------------

def main():
  parser = argparse.ArgumentParser(description="")
  parser.add_argument(
    "tutorial_source_dir",
    type=str,
    help="Path to the tutorial source directory", )
  parser.add_argument(
    "--gen-only",
    action="store_true",
    help="Write the test script to the screen instead of running it",)
  parser.add_argument(
    "--section",
    type=str,
    help="Specify a section to run", )
  args = parser.parse_args()

  # determine which tutorial sections to run
  sections = []
  if args.section:
    sections = [Path(os.path.abspath(args.section)) / "README.md"]
  else:
    raise NotImplementedError("Running all sections is not yet implemented")

  # for each section
  for section in sections:
    tutorialSection = parseMarkdown(section).flatten()

    # output script to screen, and quit
    if args.gen_only:
      print(RUN_HEADER)
      for s in tutorialSection:
        print(s)
        for c in s.commands:
          print(c.bash())
      continue

    # count the number of commands, and print the section header
    cmdCount = sum(len(h.commands) for h in tutorialSection)
    print(consoleBold(consoleYellow(f"Running tutorial: {section} ({cmdCount} commands)")))

    # start running the script
    process = subprocess.Popen(
      ["bash"], stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    process.stdin.write(RUN_HEADER)
    process.stdin.write("echo RUN_SECTION_START\n")

    # helper function to read from the process
    # and print any errors that occur
    def waitRead():
      output = process.stdout.readline()
      if output == "" and process.poll() is not None:
        # we usually get here if there has been an error in the script
        # (possibly an unbound variable?)
        # print everything there is in the stderr and exit
        print(consoleRed("[ERROR]"))
        print("Error in script execution")
        while True:
          err = process.stderr.readline()
          if err == "":
            break
          print(err)
        sys.exit(1)
      return output

    # start printing information about the section, and wait for commands to finish
    RE_CMD_RET = re.compile(r"RUN_CMD_(?P<status>END|ERR|START) line=(?P<line>\d+)(?: exit=(?P<exit>\d+))?")
    for h in tutorialSection:
      print(consoleBold(h))
      for c in h.commands:
        # issue the bash command
        print(f"  [{c.index:>2}]  {c}  ", end="")
        sys.stdout.flush()
        process.stdin.write(f"{c.bash()}\n")
        process.stdin.flush()

        # wait for the command to finish
        while True:
          output = waitRead()

          # match end of command
          match = RE_CMD_RET.match(output)
          if match:
            retIndex = int(match.group("line"))
            retType = match.group("status")
            if retIndex != c.index:
              raise Exception(f"Error in command index {c.index}")
            elif retType == "ERR":
              print(consoleRed("[ERROR]"))
              print(f"command exited with error code: {match.group('exit')}")
              print("see output.log for details")
              sys.exit(1)
            elif retType == "END":
              print(consoleGreen("[OK]"))
              break
            elif retType == "START":
              # do something with this info??
              pass

    # wait for the final "section end" message
    process.stdin.write("echo RUN_SECTION_END\n")
    process.stdin.close()
    while True:
      output = waitRead()
      if output.startswith("RUN_SECTION_END"):
        print(consoleGreen("Section complete!"))
        break
      else:
        raise Exception("Error in section completion")

    # check for program termination and errors
    process.wait()
    return_code = process.poll()
    if return_code:
      raise subprocess.CalledProcessError(return_code, "bash")

if __name__ == "__main__":
  main()