==========
UFC 2.3.0+
==========

Introduction
============

UFC (Unified Form-assembly Code) is a unified framework for finite
element assembly. More precisely, it defines a fixed interface for
communicating low level routines (functions) for evaluating and
assembling finite element variational forms. The UFC interface
consists of a single header file ufc.h that specifies a C++ interface
that must be implemented by code that complies with the UFC
specification. Examples of form compilers that support the UFC
interface are FFC and SyFi. For more information, visit the FEniCS web
page at

    http://www.fenicsproject.org

or refer to the UFC Specification and User Manual in

    doc/manual/ufc-user-manual.pdf

in this source tree.


Installation
============

To install UFC, run::

  cmake .
  make
  make install

This installs the header file ufc.h and a small set of Python
utilities (templates) for generating UFC code. Files will be installed
under the default prefix. The installation prefix may be optionally
specified, for example::

  cmake -DCMAKE_INSTALL_PREFIX=$HOME/local .
  make install

Alternatively, just copy the single header file src/ufc/ufc.h into a
suitable include directory. If you do not want to build and install
the python extenstion module of UFC, needed by, e.g., PyDOLFIN, you
can write::

  cmake -DCMAKE_INSTALL_PREFIX=~/local -D UFC_ENABLE_PYTHON:BOOL=OFF .
  make
  make install

For more options, it is convenient to use a CMake GUI. To use a GUI (if
installed) for an out-of-source build, simply type::

  mkdir build
  cd build
  cmake-gui ../
  make
  make install


AUTHORS
=======

A list of authors can be found in the file AUTHORS.


License
=======

Details about the license can be found the file LICENSE.


Feedback
========

Feedback, comments and suggestions should be sent to

  fenics-ufc@lists.launchpad.net

For questions and bug reports, visit the UFC Launchpad page:

  http://www.launchpad.net/ufc
