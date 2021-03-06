import argparse
from os import uname
from os.path import relpath, dirname, splitext, basename, join
import subprocess as sp
import sys

def isLinux():
    return 'Linux' in uname()

def isMac():
    return 'Darwin' in uname()

assert isLinux() or isMac()

LOG_FILE = "/tmp/ycm-extra-conf-log.txt"
LIB_DIR  = '.lib-linux64' if isLinux() else '.lib-osx'

# cmd is a string with a shell command.
def _run_cmd( cmd ):
    p = sp.Popen( cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True )
    (stdout, stderr) = p.communicate()
    assert p.returncode == 0, \
          'error running: %s\nerror: %s' % (cmd,stderr)
    return stdout

# Normally when calling a compiler it has a set of built-in
# header search paths where it looks for its standard headers
# that will be used automatically without having to explicitly
# specify them with -I on the compile commandline. However, when
# calling libclang.so it will not autmatically use those. This is
# bad because YCM will try to deduce what they are and then ap-
# pend them (with -isystem ...) to the commandline which can mess
# things up when it gets it wrong. So in this function we invoke
# the compiler binary and get it to tell us what the search paths
# are so we can later append them manually to the commandline
# with -isystem.
def find_system_include_paths( compiler_binary ):
  cmd = 'echo | %s -v -E -x c++ - 2>&1' % compiler_binary
  output = _run_cmd( cmd )
  is_header = False
  search_paths = []
  # Print lines between the two marker patterns.
  for line in output.split( '\n' ):
    if 'End of search' in line:
      is_header = False
    if is_header:
      search_paths.append( line.strip() )
    if 'include <..' in line:
      is_header = True
  return search_paths

def _make( path ):

    # Convert file to object file, put it inside the lib folder,
    # and then make it relative to current directory, e.g.:
    #
    #    /A/B/C/file.cpp ==> ../../C/.lib-linux64/file.o

    rel_file = relpath( path )
    rel_dir  = dirname( rel_file )
    stem     = basename( splitext( rel_file )[0] )
    target   = join( rel_dir, LIB_DIR, stem) + '.o'

    # -n : don't run the target, just print commands,
    # -B : act as if the target were out of date
    # V= : tells nr-make to not suppress command echoing
    cmd = ['/usr/bin/make', 'USE_CLANG=', '-nB', 'V=', target]

    stdout = _run_cmd( ' '.join( cmd ) )

    (line,) = [l for l in stdout.split( '\n' ) if target in l]
    words = line.split()

    # words[0] or [1] is assumed to contain the compiler binary.
    compiler_binary = words[0] if 'ccache' not in words[0] else words[1]
    isystems = find_system_include_paths( compiler_binary )
    if isystems:
        # There MUST NOT be a space between -isystem and the
        # path, otherwise it will be silently ignored!
        words.extend( ['-isystem%s' % f for f in isystems] )

    return words

def FlagsForFile( filename, **kwargs ):
    return { 'flags': _make( filename ) }

def generate_compile_flags_txt( cpp_src, output ):
    with file( output, 'w' ) as f:
      flags = FlagsForFile( cpp_src )['flags']
      for f1,f2 in zip( flags, flags[1:] ):
        if '-c' in (f1,f2) or '-o' in (f1,f2):
          continue
        print >>f, f2
    # print 'Wrote output to', output

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Generate Compile Flags' )

    parser.add_argument( '--compile-flags-txt',
                         dest='compile_flags_txt',
                         default=None,
                         type=str,
                         help='Emit compile_flags.txt at specified location' )
    parser.add_argument( '--src-file',
                         dest='src',
                         required=True,
                         type=str,
                         help='The source file to use when running make' )
    args = parser.parse_args()

    if args.compile_flags_txt:
      generate_compile_flags_txt( args.src, args.compile_flags_txt )
      exit( 0 )

    print _run_cmd( '/usr/bin/make diag' )
    flags = FlagsForFile( args.src )['flags']
    print flags[0]
    for flag in flags[1:]:
        print ' ', flag
